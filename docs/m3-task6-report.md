# M3 Task 6 Completion Report — Voice AI Assistant & Multilingual Voice Support

**Milestone:** M3 · **Task:** 6 · **Status:** Implemented — awaiting approval
**Branch:** `main` · **Date:** 2026-08-06

---

## 1. Overview

Task 6 delivers a **Voice AI Assistant and Multilingual Voice Support** layer
over the rule-based backend: a conversational **AI Assistant page** (text or
voice in, voice out) and a **"read it aloud" button on every major
recommendation section** — treatment, soil, recovery, Crop Doctor summary, AI
diagnosis, and the crop calendar. All engine logic lives on the backend,
**reusing the existing treatment / soil / recovery / calendar services**; the
frontend adds three **framework-free speech services**
(`SpeechRecognitionService`, `SpeechSynthesisService`, `VoiceAssistantService`)
that the UI reuses everywhere, so recognition/synthesis wiring is never
duplicated.

Voice is **multilingual from day one** — English and हिन्दी ship now, and the
architecture is ready for all 12 Indian languages without fake translations:
language → BCP-47 voice locale mapping (`en-IN` / `hi-IN`) is one row per
code, the backend intent router auto-detects Hindi (Devanagari) and the
assistant replies in the language you asked in.

## 2. Features Implemented

### 2.1 Backend — rule-based assistant (no LLM)

**`app/schemas/assistant.py`** — `AssistantIn(query, lang)`,
`AssistantReplyOut(intent, message, sections, lang)` with
`ASSISTANT_LANGS = ("en", "hi")` and the intent vocabulary.

**`app/services/assistant.py`** — `AssistantService.answer(user, query, lang)`:
bilingual **keyword intent routing** (treatment → fertilizer → soil →
calendar → recovery → disease → greeting → help), **language detection**
(Devanagari → हिन्दी; otherwise the sent `lang`), and **best-effort
composition** that reuses the existing engines rather than duplicating policy:

| Intent | Sources (existing services) |
|---|---|
| `disease` | `ScanService.list_scans` — healthy / diseased / no-scans answers |
| `treatment` | `RecommendationService.for_scan` — homemade / organic / chemical sections |
| `soil` | `SoilRecommendationService.for_scan` — health score + care + suitability |
| `recovery` | `RecoveryTrackerService.tracker` — status, %, risk, recent treatments |
| `calendar` | `CalendarService.dashboard` — today + overdue open tasks |
| greeting / help / fallback | static bilingual copy + capability listing |

Every engine call is `try/except` best-effort, so a missing scan or catalog
degrades to a helpful fallback instead of an error. Sections are titled in the
reply language (English or Hindi).

**`app/api/v1/endpoints/assistant.py`** — `POST /api/v1/assistant` (auth
required). Registered in `app/api/v1/router.py`.

**`tests/test_assistant.py` (15)** — auth 401, empty-query 422, unrecognized
lang auto-detect, greeting (en), Hindi auto-detect, fallback, disease
no-scans / diseased / healthy, treatment sections, fertilizer, soil, recovery,
calendar before/after scheduling tomato, Hindi treatment localization.

### 2.2 Frontend — three reusable speech services

- **`src/services/speech-recognition.ts`** — thin wrapper over the Web Speech
  recognition API (absent from TS lib.dom → structural interfaces). Resolves
  `SpeechRecognition` / `webkitSpeechRecognition`, wires `start/stop/abort`
  lifecycle, accumulates **committed + interim** transcripts, and normalizes
  vendor errors (`not-allowed`, `no-speech`, `audio-capture`, `network`,
  `aborted`, `unknown`) so the UI localizes *codes*, not vendor sentences.
- **`src/services/speech-synthesis.ts`** — wrapper over `window.speechSynthesis`:
  caches voices, `pickVoice(lang)` (exact BCP-47 match, then prefix), and
  `speak(text, lang, handlers)` with cancel/pause/resume/isSpeaking.
- **`src/services/voice-assistant.ts`** — the one seam the UI talks to:
  `speechLocale(lang)` maps app codes → voice locales (`en → en-IN`,
  `hi → hi-IN`, one row per language — the M4 growth point),
  `replyText(reply)` flattens a reply to speakable text, `ask()` → backend,
  `readReply()` reads it aloud **in the reply's own language**,
  `isVoiceSupported()`.

### 2.3 Reusable UI

- **`src/components/assistant/speak-button.tsx`** — "Read aloud" play/stop
  toggle with `aria-pressed` + sr-only label. Renders **nothing** when the
  browser has no synthesis, so unsupported browsers never see a dead control.
- **`src/components/assistant/speech-input.tsx`** — text field + mic: live
  transcript streams into the field while listening, red pulsing dot, mic →
  stop toggle, localized mic-permission / no-speech / unsupported alerts, Enter
  submits, session aborted on unmount.
- **`src/components/assistant/describe.ts`** — a single source of truth that
  flattens each recommendation data model (treatment, soil, recovery, plant
  overview, AI diagnosis, schedule) into one speakable string, shared by every
  panel's SpeakButton.

### 2.4 Voice AI Assistant page (`src/pages/assistant.tsx`)

Replaces the placeholder: auth gate, chat bubbles (user right / assistant
left with intent badge + per-reply speak control), **voice-output toggle**,
typing / empty / error states, tappable **suggestion chips**, clear-conversation
(which also cancels speech), auto-scroll conversation, fully responsive with
dark mode. Routes + header nav added; the whole `assistant` namespace is in
`en.json` / `hi.json` (UI chrome localized; catalog content stays English).

### 2.5 SpeakButton integrated into every major section

Treatment recommendations, soil recommendations, recovery tracker, Crop
Doctor plant overview, AI diagnosis, and calendar schedule-card each render a
SpeakButton driven by `describe.ts` — the same data model, flattened once.

## 3. Test Results

### 3.1 Backend — full suite
`295 collected, 294 passed, 1 skipped` (was 279/1; +15 assistant tests) ·
exit 0. **Ruff check**: All checks passed. **Ruff format --check**: own M3 T6
files formatted (pre-existing soil/recovery files intentionally left per
project scoping rule). **MyPy**: Success, 73 source files.

### 3.2 Frontend — 6 new test files, 37 tests
- **`speech-recognition.test.ts` (7)** — support detection, create wiring,
  start/stop lifecycle, interim streaming + final commit, error normalization,
  abort. Exercises the service against a stubbed `window.SpeechRecognition`.
- **`speech-synthesis.test.ts` (7)** — support, locale read-aloud + handlers,
  empty/unsupported skips, exact-before-prefix voice pick, cancel/pause/resume.
- **`voice-assistant.test.ts` (7)** — locale mapping, `replyText` flattening,
  `ask()` payload, `readReply()` speaking in the reply's language, support flag.
- **`speak-button.test.tsx` (5)** — renders null when unsupported/empty, play →
  stop toggle, reset after finish, custom label + hi-IN locale.
- **`speech-input.test.tsx` (5)** — disabled mic when unsupported, session
  start/stop, live interim + commit, localized error alert, Enter submit.
- **`assistant.test.tsx` (6)** — auth gate, suggestion chip → reply rendered +
  read aloud, typed send, voice-output-off silence, error bubble, clear.

**Full frontend suite: `143 passed, 26 files`** (was 106/20) · **TypeScript**
`tsc -b --noEmit`: clean · **ESLint** `--max-warnings=0`: clean ·
**Production build**: OK (pre-existing CSS/chunk warnings only).

Robustness fixes surfaced by the tests: the conversation's auto-scroll now uses
an optional-call guard (`scrollTo` is missing in some webviews), and the
live-transcript composer collapses whitespace runs browsers inject between
interim fragments.

## 4. Files Changed / Added

- **Backend (new):** `app/schemas/assistant.py`, `app/services/assistant.py`,
  `app/api/v1/endpoints/assistant.py`, `tests/test_assistant.py`
- **Backend (modified):** `app/api/v1/router.py`
- **Frontend (new):** `src/types/assistant.ts`,
  `src/services/speech-recognition.ts`, `src/services/speech-synthesis.ts`,
  `src/services/voice-assistant.ts`, `src/components/assistant/describe.ts`,
  `src/components/assistant/speak-button.tsx`,
  `src/components/assistant/speech-input.tsx`, `src/pages/assistant.tsx`, and
  their 6 test files
- **Frontend (modified):** `src/lib/api.ts`, `src/app/router.tsx`,
  `src/components/layout/header.tsx`, `src/locales/en.json`,
  `src/locales/hi.json`, and the six SpeakButton integration panels
  (`recommendations`, `soil-recommendations`, `recovery-tracker`,
  `plant-overview`, `ai-diagnosis`, `schedule-card`) plus
  `src/pages/__tests__/scan-history.test.tsx` (waitFor timeout hardening).

## 5. Future-Ready Notes

- **All 12 Indian languages (M4)** — add a real `locales/<code>.json` pack and
  one `speechLocale` row; no fake translations are ever shipped. Voice adapts
  because the reply carries its own `lang`, and recognition uses
  `speechLocale(i18n.language)`.
- **Framework-free services** — all three speech services are plain classes
  (no React), so any future surface reuses them unchanged.
- **Push-notification seam** — the assistant's calendar answers read the same
  server-side buckets a future notifier will target.
- **Restart the dev backend** to pick up the new `/assistant` route (started
  without `--reload`).

**Next:** M3 Task 7 — awaiting user approval; do not begin unprompted.
