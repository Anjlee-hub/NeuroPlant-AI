"""Assistant conversation providers (M3.1).

The assistant is a provider-backed conversational layer. Two implementations
share one :class:`ConversationProvider` protocol so the service never cares
which one answered:

- :class:`LocalConversationProvider` — the deterministic engine (M3 Task 6
  routing + M3.1 conversational upgrades). No network, no key, fully offline.
  It is the default and the only provider exercised by tests.
- :class:`LLMConversationProvider` — the LLM seam. Selected automatically when
  ``llm_api_key`` is configured; guarded so native dev (no key) keeps running
  the local engine. The system-prompt + message-turn builders are pure
  functions so the project-data → prompt wiring is unit-tested with no API
  call. Anthropic Messages is the only wired transport today.

Both providers reuse the **existing** engine services (scans, recommendations,
soil, recovery, calendar) for every fact — the assistant never re-implements
policy, it composes it.
"""

from __future__ import annotations

import re
from contextlib import suppress
from datetime import UTC, datetime
from typing import Protocol

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.catalog import Crop
from app.models.scan import Scan
from app.models.user import User
from app.schemas.assistant import AssistantReplyOut, AssistantSection
from app.services.assistant_context import (
    ASSISTANT_LANGS,  # noqa: F401  (re-exported for the facade's convenience)
    AssistantContext,
    CatalogEntityExtractor,
    ConversationMemory,
    greeting_for,
    load_disease,
    pick,
)
from app.services.calendar import CalendarService
from app.services.recommendations import (
    CatalogUnavailableError,
    RecommendationNotFoundError,
    RecommendationService,
)
from app.services.recovery import RecoveryTrackerService
from app.services.scans import ScanService
from app.services.soil import (
    SoilCatalogUnavailableError,
    SoilNotFoundError,
    SoilRecommendationService,
)

logger = get_logger(__name__)

# ── Bilingual label maps (computed statuses → localized display) ──────────

_SEVERITY_HI = {"low": "हल्का", "moderate": "मध्यम", "severe": "गंभीर"}
_RISK_HI = {"low": "कम", "medium": "मध्यम", "high": "उच्च"}
_RECOVERY_STATUS_HI = {
    "at_risk": "जोखिम में",
    "on_track": "सही राह पर",
    "improving": "सुधर रहा है",
    "recovered": "ठीक हो चुका है",
}
_SOIL_HEALTH_HI = {
    "poor": "खराब",
    "fair": "औसत",
    "good": "अच्छा",
    "excellent": "उत्तम",
}

# ── Intent routing ─────────────────────────────────────────────────────────
# (English + Hindi keyword lists matched with word boundaries against the
# lowercased query). ORDER MATTERS: earlier intents win, so "How do I treat
# this disease?" lands on treatment (not disease), "good morning" on greeting
# (not smalltalk), and "What does this disease mean?" on disease_explain.
# ``None`` → no keyword intent: the provider then falls back to entity/agri
# checks (report / help / non_agriculture).

_INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "greeting",
        (
            "hello",
            "hi",
            "hey",
            "namaste",
            "namaskar",
            "good morning",
            "good afternoon",
            "good evening",
            "good night",
            "greetings",
            "hola",
        ),
        ("नमस्ते", "नमस्कार", "हैलो", "नमो"),
    ),
    (
        "identity",
        (
            "who are you",
            "what are you",
            "your name",
            "who is neuroplant",
            "who is this",
            "about you",
        ),
        ("तुम कौन", "आप कौन", "कौन हो", "कौन हैं", "तुम्हारा नाम", "आपका नाम"),
    ),
    (
        "thanks",
        ("thank you", "thanks", "thank", "thx", "dhanyavaad", "shukriya"),
        ("धन्यवाद", "शुक्रिया", "थैंक्यू"),
    ),
    (
        "help",
        (
            "help",
            "what can you",
            "what do you do",
            "how do you work",
            "assistant",
            "capabilities",
            "features",
            "what can i ask",
            "how can you help",
            "explain your features",
        ),
        ("मदद", "क्या कर", "सहायक", "विशेषताएँ"),
    ),
    (
        "smalltalk",
        (
            "ok",
            "okay",
            "great",
            "nice",
            "cool",
            "awesome",
            "good",
            "fine",
            "sure",
            "yes",
            "no",
            "hmm",
            "haha",
            "lol",
            "wow",
            "right",
        ),
        ("ठीक है", "अच्छा", "हाँ", "नहीं"),
    ),
    (
        "recovery_timeline",
        (
            "how long",
            "when will",
            "recover",
            "recovery time",
            "how many days",
            "take to heal",
            "when it get better",
        ),
        ("कितने दिन", "कब ठीक", "कितना समय", "कब तक"),
    ),
    (
        "watering",
        ("water", "watering", "irrigat", "how often", "moisture", "sprinkle", "drip"),
        ("सिंचाई", "पानी", "कितनी बार"),
    ),
    (
        "neem",
        ("neem", "neem oil", "नीम"),
        ("नीम",),
    ),
    (
        "recovery",
        (
            "recovery",
            "recovering",
            "progress",
            "healed",
            "improved",
            "getting better",
            "how is my crop",
        ),
        ("सुधार", "ठीक", "पुनर्प्राप्ति", "बेहतर"),
    ),
    (
        "treatment",
        (
            "treat",
            "treatment",
            "cure",
            "how do i fix",
            "what should i spray",
            "remedy",
            "medicine",
            "get rid of",
            "fix it",
            "spray",
        ),
        ("इलाज", "दवा", "उपचार", "छिड़काव", "स्प्रे"),
    ),
    (
        "fertilizer",
        (
            "fertilizer",
            "fertilise",
            "fertilize",
            "manure",
            "nutrient",
            "feed",
            "npk",
            "compost",
            "urea",
            "dap",
        ),
        ("खाद", "उर्वरक", "पोषक"),
    ),
    (
        "soil",
        ("soil", "ph", "earth", "land"),
        ("मिट्टी", "भूमि", "मृदा"),
    ),
    (
        "calendar",
        (
            "calendar",
            "today",
            "task",
            "tasks",
            "reminder",
            "todo",
            "to-do",
            "schedule",
            "what's due",
            "whats due",
            "due today",
        ),
        ("आज", "कार्य", "काम", "रिमाइंडर"),
    ),
    (
        "symptoms",
        (
            "yellow",
            "yellowing",
            "leaves are",
            "leaf is",
            "wilting",
            "dying",
            "dead",
            "brown",
            "spots on",
            "curling",
            "drooping",
            "powder",
            "mildew",
            "fungus",
            "mold",
            "symptom",
        ),
        ("पीले", "पीलापन", "मुरझा", "सूख", "भूरे", "लक्षण"),
    ),
    (
        "disease_explain",
        (
            "what does",
            "what do you mean",
            "means",
            "meaning",
            "explain",
            "simple words",
            "dangerous",
            "danger",
            "serious",
            "is it bad",
            "what is this",
            "what is it",
            "in simple",
        ),
        ("क्या मतलब", "क्या होता", "खतरनाक", "गंभीर", "समझाओ", "सरल शब्द"),
    ),
    (
        "disease",
        (
            "disease",
            "diagnos",
            "infected",
            "what's wrong",
            "what is wrong",
            "problem with my crop",
            "why is my crop",
            "sick",
            "blight",
            "mosaic",
            "curl",
            "wilt",
            "what's the problem",
        ),
        ("रोग", "बीमारी", "समस्या", "क्या हुआ"),
    ),
)

# Words that mark a query as farm-related even when no intent keyword matches.
_AGRI_HINTS = (
    "crop",
    "plant",
    "leaf",
    "leaves",
    "field",
    "farm",
    "farmer",
    "grow",
    "growing",
    "seed",
    "seedling",
    "harvest",
    "fruit",
    "vegetable",
    "garden",
    "soil",
    "water",
    "pesticide",
    "fertilizer",
    "fungus",
    "mildew",
    "blight",
    "disease",
    "yield",
    "खेत",
    "फसल",
    "पौधा",
    "पत्ती",
    "मिट्टी",
    "बीज",
)

_QUESTION_WORDS = (
    "what",
    "how",
    "why",
    "which",
    "when",
    "who",
    "where",
    "is",
    "are",
    "can",
    "do",
    "should",
    "does",
    "will",
    "क्या",
    "कैसे",
    "क्यों",
    "कौन",
)


def _kw_match(lowered: str, keywords: tuple[str, ...]) -> bool:
    """Match English keywords on word boundaries, Hindi as substrings.

    Python's ``\\b`` is ASCII-defined, and Devanagari words contain combining
    marks (virama, vowel signs) that ``\\w`` skips — so ``\\bनमस्ते\\b`` never
    matches. Hindi keywords are non-ASCII and can't collide with English text,
    so plain substring matching is correct (and matches the old router).
    """
    return any(
        (kw in lowered)
        if kw and ord(kw[0]) > 0x7F
        else bool(re.search(rf"\b{re.escape(kw)}\b", lowered))
        for kw in keywords
    )


def _detect_intent(query: str) -> str | None:
    """First intent whose English or Hindi keyword appears in the query."""
    lowered = query.lower()
    for intent, en_kw, hi_kw in _INTENT_KEYWORDS:
        if _kw_match(lowered, en_kw) or _kw_match(lowered, hi_kw):
            return intent
    return None


def _has_agri_hint(query: str) -> bool:
    lowered = query.lower()
    return any(hint in lowered for hint in _AGRI_HINTS)


def _is_statement(query: str) -> bool:
    """True when the query is a bare statement, not a question."""
    lowered = query.lower().strip("?.! ")
    if re.search(
        r"\b(what|how|why|which|when|who|where|is|are|can|do|should|does|will)\b", lowered
    ):
        return False
    return not any(q in lowered for q in ("क्या", "कैसे", "क्यों", "कौन"))


def _danger_text(lang: str, severity: str | None) -> str:
    """Friendly, scan-aware answer to "is it dangerous?"."""
    if severity == "severe":
        return pick(
            lang,
            "Yes — it can spread quickly and seriously harm your crop, so treat it right away.",
            "हाँ — यह तेज़ी से फैल सकता है और फसल को गंभीर नुकसान पहुँचा सकता है, इसलिए तुरंत उपचार करें।",
        )
    if severity == "moderate":
        return pick(
            lang,
            "It's serious but manageable with prompt, consistent care.",
            "यह गंभीर है पर नियमित देखभाल से संभाला जा सकता है।",
        )
    if severity == "low":
        return pick(
            lang,
            "It's mild right now — keep monitoring and treat it early before it spreads.",
            "अभी हल्का है — नज़र रखें और फैलने से पहले शुरुआत में ही उपचार करें।",
        )
    return pick(
        lang,
        "How dangerous it is depends on how early you catch it — a crop scan tells us "
        "the severity and stage.",
        "खतरा इस बात पर निर्भर करता है कि आप इसे कितनी जल्दी पकड़ते हैं — क्रॉप स्कैन से "
        "गंभीरता और अवस्था पता चलती है।",
    )


# ── Provider protocol ──────────────────────────────────────────────────────


class ConversationProvider(Protocol):
    """Anything that turns an :class:`AssistantContext` into a reply."""

    async def answer(self, ctx: AssistantContext) -> AssistantReplyOut: ...


# ── Local (deterministic) provider ─────────────────────────────────────────


class LocalConversationProvider:
    """Conversational engine — bilingual, offline, reuses the engine services.

    Follow-ups work because the provider carries :class:`ConversationMemory`
    seeded from the request's transcript: "How do I treat *it*?" resolves to
    the disease named earlier. Statements ("My tomato has early blight") are
    acknowledged and remembered; off-topic questions get a friendly boundary,
    never "I couldn't find an answer."
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def answer(self, ctx: AssistantContext) -> AssistantReplyOut:
        memory = ConversationMemory(CatalogEntityExtractor(self.db), ctx.history)
        await memory.seed()

        intent = _detect_intent(ctx.query)
        if intent is None:
            crop, disease = await memory.resolve(ctx.query)
            if crop is not None or disease is not None:
                intent = "report"
            elif _has_agri_hint(ctx.query):
                intent = "help"
            else:
                intent = "non_agriculture"

        crop, disease = await memory.resolve(ctx.query)
        builder = getattr(self, f"_reply_{intent}", self._reply_non_agriculture)
        try:
            reply = await builder(ctx, crop, disease)
        except Exception:
            logger.warning("assistant_reply_failed", intent=intent, exc_info=True)
            reply = await self._reply_non_agriculture(ctx, None, None)

        # Keep the subject current for the next turn.
        await memory.remember(reply.message)
        return reply

    # ── Social / static intents ───────────────────────────────────────────

    async def _reply_greeting(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        greeting = greeting_for(ctx.lang, ctx.now.hour)
        return AssistantReplyOut(
            intent="greeting",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"{greeting}! 🌱 I'm your NeuroPlant AI farming assistant. How can I help "
                "you with your crops today?",
                f"{greeting}! 🌱 मैं आपका न्यूरोप्लांट AI खेती सहायक हूँ। आज मैं आपकी फसलों में कैसे मदद करूँ?",
            ),
            sections=self._capability_sections(ctx.lang),
        )

    async def _reply_identity(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        return AssistantReplyOut(
            intent="identity",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                "I'm the NeuroPlant AI farming assistant — your personal crop doctor. I "
                "analyze your crop scans, recommend treatments and soil care, track "
                "recovery, and remind you of farming tasks. Ask me anything about your "
                "crops! 🌱",
                "मैं न्यूरोप्लांट AI खेती सहायक हूँ — आपका निजी फसल डॉक्टर। मैं आपकी "
                "फसल के स्कैन का विश्लेषण करता हूँ, उपचार और मिट्टी की देखभाल सुझाता "
                "हूँ, सुधार ट्रैक करता हूँ और खेती के कार्य याद दिलाता हूँ। अपनी "
                "फसलों के बारे में कुछ भी पूछिए! 🌱",
            ),
            sections=self._capability_sections(ctx.lang),
        )

    async def _reply_help(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        return AssistantReplyOut(
            intent="help",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                "I answer from your own farm data. Try one of these:",
                "मैं आपके अपने फार्म डेटा से उत्तर देता हूँ। इनमें से कुछ पूछिए:",
            ),
            sections=self._capability_sections(ctx.lang),
        )

    async def _reply_thanks(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        return AssistantReplyOut(
            intent="thanks",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                "You're welcome! 🌱 Happy farming — ask me anything about your crops.",
                "आपका स्वागत है! 🌱 खेती मंगलमय हो — अपनी फसलों के बारे में कुछ भी पूछिए।",
            ),
            sections=[],
        )

    async def _reply_smalltalk(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        return AssistantReplyOut(
            intent="smalltalk",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                "Glad to help! 🌱 I know your crops best once you've scanned them and "
                "scheduled them on the calendar. What would you like to know?",
                "खुशी की बात है! 🌱 जब आप अपनी फसलें स्कैन करते हैं और कैलेंडर पर शेड्यूल "
                "करते हैं तो मैं उन्हें सबसे अच्छी तरह जानता हूँ। क्या जानना चाहेंगे?",
            ),
            sections=self._capability_sections(ctx.lang),
        )

    async def _reply_non_agriculture(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        """Friendly boundary for off-topic questions — never a dead-end."""
        return self._fallback(
            "non_agriculture",
            ctx.lang,
            pick(
                ctx.lang,
                "I'm your farming assistant, so I focus on crops, plant disease, "
                "treatment, soil care, recovery and farming tasks. Ask me something "
                "about your farm — I'm happy to help! 🌱",
                "मैं आपका खेती सहायक हूँ, इसलिए मैं फसलों, पौधों के रोग, उपचार, मिट्टी "
                "की देखभाल, सुधार और खेती के कार्यों पर ध्यान देता हूँ। अपने खेत के "
                "बारे में कुछ पूछिए — मैं मदद के लिए तैयार हूँ! 🌱",
            ),
        )

    # ── Data-backed intents ───────────────────────────────────────────────

    async def _reply_disease(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        drow = None
        if disease:
            drow = await load_disease(self.db, disease, crop)

        # A named disease (this turn or from memory) → describe it from the catalog.
        if drow is not None:
            crop_label = crop
            if crop_label is None and drow.crop is not None:
                crop_label = drow.crop.common_name or drow.crop.name
            opening = "Got it — " if _is_statement(ctx.query) else ""
            cause_line = drow.causes or pick(
                ctx.lang,
                f"It's a plant disease that can affect {crop_label or 'your crop'}.",
                f"यह एक पौधा रोग है जो {crop_label or 'आपकी फसल'} को प्रभावित कर सकता है।",
            )
            sections: list[AssistantSection] = []
            if drow.symptoms:
                sections.append(
                    AssistantSection(
                        title=pick(ctx.lang, "Symptoms", "लक्षण"),
                        body="\n".join(f"• {s}" for s in drow.symptoms),
                    )
                )
            if drow.causes:
                sections.append(
                    AssistantSection(
                        title=pick(ctx.lang, "What causes it", "इसका कारण"), body=drow.causes
                    )
                )
            if scan is not None and scan.disease_name == drow.name:
                sections.append(self._scan_summary_section(scan, ctx.lang, crop))
            return AssistantReplyOut(
                intent="disease",
                lang=ctx.lang,
                message=pick(
                    ctx.lang,
                    f"{opening}**{drow.name}** on {crop_label or 'your crop'}. {cause_line} "
                    "I can help you treat it, explain it in simple words, improve the soil, "
                    "or track recovery — just ask.",
                    f"{opening}**{drow.name}** {crop_label or 'आपकी फसल'} पर। {cause_line} "
                    "मैं इसका उपचार, सरल शब्दों में स्पष्टीकरण, मिट्टी सुधार या सुधार "
                    "ट्रैकिंग में मदद कर सकता हूँ — बस पूछिए।",
                ),
                sections=sections,
            )

        # No named disease → fall back to the latest scan (existing behavior).
        if scan is None:
            return self._fallback("disease", ctx.lang, _no_scan_text(ctx.lang))
        if scan.disease_id is None:
            crop = await self._crop_name(scan)
            return AssistantReplyOut(
                intent="disease",
                lang=ctx.lang,
                message=pick(
                    ctx.lang,
                    f"Your latest scan of {crop or 'your crop'} didn't find a disease "
                    "— it looks healthy. Keep an eye on it and re-scan if symptoms appear.",
                    f"{crop or 'आपकी फसल'} के सबसे हालिया स्कैन में कोई रोग नहीं मिला — "
                    "यह स्वस्थ दिखती है। नज़र रखें और लक्षण दिखने पर दोबारा स्कैन करें।",
                ),
                sections=[self._scan_summary_section(scan, ctx.lang, crop)],
            )

        crop = await self._crop_name(scan)
        conf = f"{scan.confidence:.0%}"
        sev = scan.severity or "unknown"
        sev_hi = _SEVERITY_HI.get(sev, sev)
        return AssistantReplyOut(
            intent="disease",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"Your latest scan of {crop or 'your crop'} shows {scan.disease_name} "
                f"with {conf} confidence ({sev} severity).",
                f"{crop or 'आपकी फसल'} के सबसे हालिया स्कैन में {scan.disease_name} "
                f"दिखा — {conf} विश्वास ({sev_hi} गंभीरता)।",
            ),
            sections=[
                self._scan_summary_section(scan, ctx.lang, crop),
                AssistantSection(
                    title=pick(ctx.lang, "Next step", "अगला कदम"),
                    body=pick(
                        ctx.lang,
                        "Open the Crop Doctor for the full care plan and recovery "
                        "tracking, or ask: How do I treat this disease?",
                        "पूरी देखभाल योजना और सुधार ट्रैकिंग के लिए क्रॉप डॉक्टर खोलें, "
                        "या पूछें: इस रोग का इलाज कैसे करूँ?",
                    ),
                ),
            ],
        )

    async def _reply_disease_explain(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        drow = None
        if disease:
            drow = await load_disease(self.db, disease, crop)
        if drow is None and scan is not None and scan.disease_id is not None:
            drow = await load_disease(self.db, scan.disease_name, await self._crop_name(scan))
        if drow is None:
            return self._fallback("disease_explain", ctx.lang, _explain_no_disease_text(ctx.lang))

        name = drow.name
        severity = None
        if scan is not None and scan.disease_name == name:
            severity = scan.severity
        elif drow.severity_range:
            severity = (
                drow.severity_range[0]
                if isinstance(drow.severity_range, list)
                else drow.severity_range
            )
        pathogen = drow.pathogen_type or "disease"
        cause_line = f" {drow.causes}" if drow.causes else ""

        sections: list[AssistantSection] = []
        if drow.symptoms:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Symptoms", "लक्षण"),
                    body="\n".join(f"• {s}" for s in drow.symptoms),
                )
            )
        if drow.causes:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "What causes it", "इसका कारण"), body=drow.causes
                )
            )
        if drow.recovery_time:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Typical recovery time", "सामान्य सुधार समय"),
                    body=drow.recovery_time,
                )
            )

        return AssistantReplyOut(
            intent="disease_explain",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"In simple words, **{name}** is a {pathogen}{cause_line}. "
                f"{_danger_text(ctx.lang, severity)}",
                f"सरल शब्दों में, **{name}** एक {_pathogen_hi(pathogen)} है{cause_line}। "
                f"{_danger_text(ctx.lang, severity)}",
            ),
            sections=sections,
        )

    async def _reply_symptoms(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        lowered = ctx.query.lower()
        if any(k in lowered for k in ("yellow", "yellowing", "पीले", "पीलापन")):
            message = pick(
                ctx.lang,
                "Yellowing leaves usually point to water stress (too much or too little), "
                "a nitrogen shortage, or too little sunlight — and sometimes it's the "
                "first sign of a disease. A quick scan of the leaf tells us which one.",
                "पीली पत्तियाँ आमतौर पर पानी की कमी/अधिकता, नाइट्रोजन की कमी या धूप की "
                "कमी — और कभी-कभी किसी रोग की शुरुआत दिखाती हैं। पत्ती का त्वरित स्कैन "
                "बता सकता है कि वास्तव में क्या है।",
            )
        elif any(
            k in lowered for k in ("dying", "dead", "wilting", "drooping", "मुरझा", "सूख", "मर ")
        ):
            message = pick(
                ctx.lang,
                "A crop that's wilting or dying is usually stressed by water (under or over "
                "watering), root damage, or a fast-spreading disease. Catch it early: "
                "check the roots and soil moisture, then scan the affected leaf for a "
                "precise diagnosis and treatment.",
                "मुरझाई या सूखती फसल आमतौर पर पानी (कमी या अधिकता), जड़ों की क्षति या "
                "तेज़ी से फैलने वाले रोग से दबाव में होती है। इसे जल्दी पकड़ें: जड़ों और "
                "मिट्टी की नमी जाँचें, फिर सटीक निदान और उपचार के लिए प्रभावित पत्ती "
                "स्कैन करें।",
            )
        else:
            message = pick(
                ctx.lang,
                "Leaf spots, powder or curling can be a fungal disease, a pest, or a "
                "nutrition issue. The most reliable step is a crop scan of the affected "
                "part — it tells us exactly what's wrong and what to do.",
                "पत्ती के धब्बे, पाउडर या मुड़ाव फफूँदी रोग, कीट या पोषण की समस्या हो "
                "सकती है। सबसे भरोसेमंद कदम प्रभावित भाग का क्रॉप स्कैन है — यह बताता "
                "है कि वास्तव में क्या गलत है और क्या करना है।",
            )

        if disease:
            message += pick(
                ctx.lang,
                f" This could be related to {disease} — a scan will confirm it.",
                f" यह {disease} से संबंधित हो सकता है — स्कैन इसकी पुष्टि करेगा।",
            )

        return AssistantReplyOut(
            intent="symptoms",
            lang=ctx.lang,
            message=message,
            sections=[
                AssistantSection(
                    title=pick(ctx.lang, "Quick checks", "त्वरित जाँच"),
                    body=pick(
                        ctx.lang,
                        "• Is the soil too wet or bone dry?\n"
                        "• Any pests or webs on the underside of leaves?\n"
                        "• Is the plant getting enough sunlight?\n"
                        "• Scan the leaf for a precise diagnosis.",
                        "• क्या मिट्टी बहुत गीली या पूरी सूखी है?\n"
                        "• पत्तियों के नीचे कोई कीट या जाला तो नहीं?\n"
                        "• क्या पौधे को पर्याप्त धूप मिल रही है?\n"
                        "• सटीक निदान के लिए पत्ती स्कैन करें।",
                    ),
                )
            ],
        )

    async def _reply_treatment(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        drow = None
        if disease:
            drow = await load_disease(self.db, disease, crop)
        if drow is not None:
            try:
                rec = await RecommendationService(self.db).for_disease(drow.id)
            except (RecommendationNotFoundError, CatalogUnavailableError):
                return self._fallback("treatment", ctx.lang, _no_plan_text(ctx.lang, drow.name))
        elif scan is not None and scan.disease_id is not None:
            try:
                rec = await RecommendationService(self.db).for_scan(scan)
            except (RecommendationNotFoundError, CatalogUnavailableError):
                return self._fallback(
                    "treatment", ctx.lang, _no_plan_text(ctx.lang, scan.disease_name)
                )
        elif scan is None:
            return self._fallback("treatment", ctx.lang, _no_scan_text(ctx.lang))
        else:
            return self._fallback("treatment", ctx.lang, _no_disease_text(ctx.lang))

        crop_label = rec.disease.crop_name or crop or "your crop"
        sections = self._plan_sections(ctx.lang, rec)
        return AssistantReplyOut(
            intent="treatment",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"For {rec.disease.name} on {crop_label}, here is a treatment plan:",
                f"{rec.disease.name} के लिए {crop_label} पर एक उपचार योजना यह है:",
            ),
            sections=sections,
        )

    async def _reply_fertilizer(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        drow = None
        if disease:
            drow = await load_disease(self.db, disease, crop)
        if drow is not None:
            try:
                rec = await RecommendationService(self.db).for_disease(drow.id)
            except (RecommendationNotFoundError, CatalogUnavailableError):
                return self._fallback(
                    "fertilizer",
                    ctx.lang,
                    pick(
                        ctx.lang,
                        f"I don't have fertilizer guidance for {drow.name} yet.",
                        f"अभी {drow.name} के लिए खाद संबंधी मार्गदर्शन उपलब्ध नहीं है।",
                    ),
                )
        elif scan is not None and scan.disease_id is not None:
            try:
                rec = await RecommendationService(self.db).for_scan(scan)
            except (RecommendationNotFoundError, CatalogUnavailableError):
                return self._fallback(
                    "fertilizer",
                    ctx.lang,
                    pick(
                        ctx.lang,
                        f"I don't have fertilizer guidance for {scan.disease_name} yet.",
                        f"अभी {scan.disease_name} के लिए खाद संबंधी मार्गदर्शन उपलब्ध नहीं है।",
                    ),
                )
        elif scan is None:
            return self._fallback("fertilizer", ctx.lang, _no_scan_text(ctx.lang))
        else:
            return self._fallback("fertilizer", ctx.lang, _no_disease_text(ctx.lang))

        if not rec.fertilizer:
            return self._fallback(
                "fertilizer",
                ctx.lang,
                pick(
                    ctx.lang,
                    f"I don't have specific fertilizer guidance for {rec.disease.name}.",
                    f"{rec.disease.name} के लिए विशेष खाद मार्गदर्शन मेरे पास नहीं है।",
                ),
            )

        crop_label = rec.disease.crop_name or crop or "your crop"
        return AssistantReplyOut(
            intent="fertilizer",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"For {rec.disease.name} on {crop_label}, keep the feeding balanced: "
                f"{rec.fertilizer}",
                f"{rec.disease.name} के लिए {crop_label} पर खाद संतुलित रखें: {rec.fertilizer}",
            ),
            sections=[
                AssistantSection(
                    title=pick(ctx.lang, "Fertilizer guidance", "खाद मार्गदर्शन"),
                    body=rec.fertilizer,
                )
            ],
        )

    async def _reply_watering(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        rec = await self._plan_for_subject(crop, disease, scan)
        sections: list[AssistantSection] = []
        if rec is not None and rec.watering:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Watering guidance", "सिंचाई मार्गदर्शन"),
                    body=rec.watering,
                )
            )
        sections.append(
            AssistantSection(
                title=pick(ctx.lang, "General tip", "सामान्य सलाह"),
                body=pick(
                    ctx.lang,
                    "Check the top 2–3 cm of soil before watering — crops prefer deep, "
                    "less-frequent watering over shallow daily sprinkles.",
                    "पानी देने से पहले ऊपर की 2–3 सेंटीमीटर मिट्टी जाँचें — फसलें हल्के "
                    "रोज़ाना छिड़काव की बजाय गहरा, कम-बार पानी पसंद करती हैं।",
                ),
            )
        )
        if rec is not None and rec.watering:
            message = pick(
                ctx.lang,
                f"For {rec.disease.name} on {crop or 'your crop'}, here's watering guidance:",
                f"{rec.disease.name} के लिए {crop or 'आपकी फसल'} पर सिंचाई मार्गदर्शन यह है:",
            )
        else:
            message = pick(
                ctx.lang,
                f"For {crop or 'your crop'}, water deeply and less often — let the top "
                "2–3 cm of soil dry between waterings. Overwatering causes more problems "
                "than underwatering.",
                f"{crop or 'आपकी फसल'} के लिए गहरा और कम-बार पानी दें — दो पानियों के "
                "बीच ऊपर की 2–3 सेंटीमीटर मिट्टी सूखने दें। ज़्यादा पानी कम पानी से "
                "ज़्यादा नुकसान करता है।",
            )
        return AssistantReplyOut(
            intent="watering", lang=ctx.lang, message=message, sections=sections
        )

    async def _reply_neem(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        rec = await self._plan_for_subject(crop, disease, scan)
        neem_line = None
        disease_name = None
        if rec is not None:
            disease_name = rec.disease.name
            for rem in [*rec.homemade_remedies, *rec.organic_remedies]:
                if "neem" in (rem.title or "").lower():
                    neem_line = (
                        f"{rem.title}: {rem.instructions or rem.application} ({rem.frequency})"
                    )
                    break
        if neem_line is not None:
            return AssistantReplyOut(
                intent="neem",
                lang=ctx.lang,
                message=pick(
                    ctx.lang,
                    f"Yes — for {disease_name or 'that'}, neem oil is a good organic option:",
                    f"हाँ — {disease_name or 'इसके'} लिए नीम का तेल एक अच्छा जैविक विकल्प है:",
                ),
                sections=[
                    AssistantSection(
                        title=pick(ctx.lang, "Neem remedy", "नीम उपाय"), body=neem_line
                    )
                ],
            )
        return AssistantReplyOut(
            intent="neem",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                "Yes — neem oil is a safe, broad-spectrum organic option for many fungal "
                "diseases and pests. Dilute it (about 2–3 ml per litre of water with a "
                "few drops of soap), spray in the evening, and test on a single leaf "
                "first. Apply every 7–14 days.",
                "हाँ — नीम का तेल कई फफूँदी रोगों और कीटों के लिए सुरक्षित, प्राकृतिक "
                "विकल्प है। इसे पतला करें (लगभग 2–3 मिली प्रति लीटर पानी में साबुन की "
                "कुछ बूँदें मिलाकर), शाम को छिड़काव करें, और पहले एक पत्ती पर परीक्षण "
                "करें। हर 7–14 दिन में लगाएँ।",
            ),
            sections=[
                AssistantSection(
                    title=pick(ctx.lang, "How to apply", "कैसे लगाएँ"),
                    body=pick(
                        ctx.lang,
                        "Dilute 2–3 ml neem oil per litre of water, add a few drops of "
                        "soap, shake well, spray in the evening.",
                        "2–3 मिली नीम तेल प्रति लीटर पानी में मिलाएँ, साबुन की कुछ बूँदें "
                        "डालें, अच्छी तरह हिलाएँ, शाम को छिड़काव करें।",
                    ),
                )
            ],
        )

    async def _reply_soil(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        drow = None
        if disease:
            drow = await load_disease(self.db, disease, crop)
        soil = None
        if drow is not None:
            with suppress(SoilNotFoundError, SoilCatalogUnavailableError):
                soil = await SoilRecommendationService(self.db).for_disease(
                    drow.id,
                    severity=scan.severity if scan is not None else None,
                    confidence=scan.confidence if scan is not None else None,
                )
        elif scan is not None and scan.disease_id is not None:
            with suppress(SoilNotFoundError, SoilCatalogUnavailableError):
                soil = await SoilRecommendationService(self.db).for_scan(scan)
        elif scan is None:
            return self._fallback("soil", ctx.lang, _no_scan_text(ctx.lang))
        else:
            return self._fallback("soil", ctx.lang, _no_disease_text(ctx.lang))

        if soil is None:
            return self._fallback(
                "soil",
                ctx.lang,
                pick(
                    ctx.lang,
                    "I couldn't find a soil care plan for that yet. Ask me about treatment "
                    "or today's tasks in the meantime.",
                    "अभी उसके लिए मिट्टी देखभाल योजना नहीं मिली। तब तक उपचार या आज के "
                    "कार्यों के बारे में पूछिए।",
                ),
            )

        health = soil.soil_health
        crop_label = soil.disease.crop_name or crop or "your crop"
        label = _SOIL_HEALTH_HI.get(health.label, health.label)
        care_lines: list[str] = []
        if soil.recommended_soil_type:
            care_lines.append(soil.recommended_soil_type)
        if soil.ph_range:
            care_lines.append(pick(ctx.lang, f"pH: {soil.ph_range}", f"पीएच: {soil.ph_range}"))
        if soil.moisture_level:
            care_lines.append(soil.moisture_level)
        care_lines += soil.improvement_suggestions[:3]

        sections = [
            AssistantSection(
                title=pick(ctx.lang, "Soil health", "मिट्टी की सेहत"),
                body=pick(
                    ctx.lang,
                    f"Score {health.score:.1f}/5 — {health.label}. {health.summary}",
                    f"स्कोर {health.score:.1f}/5 — {label}. {health.summary}",
                ),
            )
        ]
        if care_lines:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Recommended care", "अनुशंसित देखभाल"),
                    body="\n".join(f"• {line}" for line in care_lines),
                )
            )
        if soil.soil_suitability:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Suitability", "उपयुक्तता"),
                    body=soil.soil_suitability,
                )
            )

        return AssistantReplyOut(
            intent="soil",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"For {soil.disease.name} on {crop_label}, your soil health is "
                f"{health.label} ({health.score:.1f}/5). {health.summary}",
                f"{soil.disease.name} के लिए {crop_label} पर आपकी मिट्टी की सेहत "
                f"{label} ({health.score:.1f}/5) है। {health.summary}",
            ),
            sections=sections,
        )

    async def _reply_recovery(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        if scan is None or scan.disease_id is None:
            return self._fallback(
                "recovery",
                ctx.lang,
                _no_scan_text(ctx.lang) if scan is None else _no_disease_text(ctx.lang),
            )
        tracker = await RecoveryTrackerService(self.db).tracker(scan)
        status = tracker.status
        status_hi = _RECOVERY_STATUS_HI.get(status, status)
        risk = tracker.risk
        risk_hi = _RISK_HI.get(risk, risk)
        pct = round(tracker.recovery_percentage * 100)
        crop = tracker.scan.crop_name

        sections = [
            AssistantSection(
                title=pick(ctx.lang, "Recovery", "पुनर्प्राप्ति"),
                body=pick(
                    ctx.lang,
                    f"Status: {status} · {pct}% recovered · "
                    f"{tracker.total_treatments} treatments logged · {risk} risk.",
                    f"स्थिति: {status_hi} · {pct}% ठीक · "
                    f"{tracker.total_treatments} उपचार दर्ज · {risk_hi} जोखिम।",
                ),
            )
        ]
        if tracker.timeline:
            last = tracker.timeline[-1]
            note = f" — {last.notes}" if last.notes else ""
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Latest log", "नवीनतम उपचार"),
                    body=f"{last.treatment_applied}{note} ({last.applied_at:%d %b %Y})",
                )
            )

        return AssistantReplyOut(
            intent="recovery",
            lang=ctx.lang,
            message=pick(
                ctx.lang,
                f"Your {crop or 'crop'} is {status} — {pct}% recovered, with {risk} risk.",
                f"आपकी {crop or 'फसल'} {status_hi} है — {pct}% ठीक, {risk_hi} जोखिम के साथ।",
            ),
            sections=sections,
        )

    async def _reply_recovery_timeline(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        scan = await self._latest_scan(ctx.user)
        drow = None
        if disease:
            drow = await load_disease(self.db, disease, crop)
        if drow is None and scan is not None and scan.disease_id is not None:
            drow = await load_disease(self.db, scan.disease_name, await self._crop_name(scan))
        if drow is None:
            if scan is None:
                return self._fallback("recovery_timeline", ctx.lang, _no_scan_text(ctx.lang))
            return self._fallback("recovery_timeline", ctx.lang, _no_disease_text(ctx.lang))

        rec = None
        with suppress(RecommendationNotFoundError, CatalogUnavailableError):
            rec = await RecommendationService(self.db).for_disease(drow.id)
        timeline = (rec.recovery_timeline if rec is not None else None) or drow.recovery_time

        sections: list[AssistantSection] = []
        tracker_note = ""
        if scan is not None and scan.disease_id is not None:
            try:
                tracker = await RecoveryTrackerService(self.db).tracker(scan)
                pct = round(tracker.recovery_percentage * 100)
                tracker_note = pick(
                    ctx.lang,
                    f" You're {pct}% of the way there, with {tracker.total_treatments} "
                    f"treatment(s) logged ({tracker.risk} risk).",
                    f" आप {pct}% रास्ते पर हैं, {tracker.total_treatments} उपचार दर्ज "
                    f"हैं ({_risk_hi(tracker.risk, ctx.lang)} जोखिम)।",
                )
                sections.append(
                    AssistantSection(
                        title=pick(ctx.lang, "Recovery progress", "सुधार प्रगति"),
                        body=pick(
                            ctx.lang,
                            f"{pct}% recovered · {tracker.total_treatments} treatments · "
                            f"{tracker.risk} risk",
                            f"{pct}% ठीक · {tracker.total_treatments} उपचार · "
                            f"{_RISK_HI.get(tracker.risk, tracker.risk)} जोखिम",
                        ),
                    )
                )
            except Exception:
                logger.debug("recovery_timeline_tracker_failed", exc_info=True)

        if timeline:
            sections.insert(
                0,
                AssistantSection(
                    title=pick(ctx.lang, "Typical recovery time", "सामान्य सुधार समय"),
                    body=timeline,
                ),
            )

        en_fallback = "some time, depending on the stage and treatment"
        hi_fallback = "अवस्था और उपचार के अनुसार कुछ समय"
        message = pick(
            ctx.lang,
            f"Recovery for {drow.name} usually takes about {timeline or en_fallback}."
            f"{tracker_note}",
            f"{drow.name} को ठीक होने में आमतौर पर {timeline or hi_fallback} लगता है।{tracker_note}",
        )
        return AssistantReplyOut(
            intent="recovery_timeline", lang=ctx.lang, message=message, sections=sections
        )

    async def _reply_calendar(
        self, ctx: AssistantContext, _crop: str | None, _disease: str | None
    ) -> AssistantReplyOut:
        dashboard = await CalendarService(self.db).dashboard(ctx.user, now=ctx.now)
        today = ctx.now.replace(tzinfo=None).date()
        today_tasks: list[tuple[str, str]] = []
        overdue_tasks: list[tuple[str, str]] = []
        for schedule in dashboard.schedules:
            for task in schedule.tasks:
                if task.completed_at is not None:
                    continue
                due = task.due_at.date()
                if due == today:
                    today_tasks.append((schedule.crop_name, task.title))
                elif due < today:
                    overdue_tasks.append((schedule.crop_name, task.title))

        if not today_tasks and not overdue_tasks:
            return AssistantReplyOut(
                intent="calendar",
                lang=ctx.lang,
                message=pick(
                    ctx.lang,
                    "You're all caught up for today — no farming tasks are due. "
                    "Schedule a crop on the Calendar to start reminders.",
                    "आज के लिए सब कुछ साफ है — कोई कार्य देय नहीं है। रिमाइंडर शुरू "
                    "करने के लिए कैलेंडर में फसल शेड्यूल करें।",
                ),
                sections=[],
            )

        sections: list[AssistantSection] = []
        by_crop: dict[str, list[str]] = {}
        for crop, title in today_tasks:
            by_crop.setdefault(crop, []).append(title)
        for crop, titles in by_crop.items():
            sections.append(AssistantSection(title=crop, body="\n".join(f"• {t}" for t in titles)))
        if overdue_tasks:
            sections.append(
                AssistantSection(
                    title=pick(ctx.lang, "Overdue", "विलंबित"),
                    body="\n".join(f"• {t}" for _, t in overdue_tasks),
                )
            )

        message = pick(
            ctx.lang,
            f"Here are today's farming tasks ({len(today_tasks)} due today, "
            f"{len(overdue_tasks)} overdue).",
            f"आज के खेती के कार्य ये हैं ({len(today_tasks)} आज देय, {len(overdue_tasks)} विलंबित)।",
        )
        return AssistantReplyOut(
            intent="calendar", lang=ctx.lang, message=message, sections=sections
        )

    async def _reply_report(
        self, ctx: AssistantContext, crop: str | None, disease: str | None
    ) -> AssistantReplyOut:
        if disease and crop:
            message = pick(
                ctx.lang,
                f"Got it — **{disease}** on {crop}. I can help you treat it, understand "
                "what it means, improve the soil, or track its recovery. What would you "
                "like to do?",
                f"समझ गया — {crop} पर **{disease}**। मैं इसका उपचार करने, इसका मतलब "
                "समझने, मिट्टी सुधारने या सुधार ट्रैक करने में मदद कर सकता हूँ। आप क्या "
                "करना चाहेंगे?",
            )
        elif disease:
            message = pick(
                ctx.lang,
                f"Got it — **{disease}**. I can explain it in simple words, suggest a "
                "treatment, or share soil care — just ask.",
                f"समझ गया — **{disease}**। मैं इसे सरल शब्दों में समझा सकता हूँ, उपचार "
                "सुझा सकता हूँ, या मिट्टी की देखभाल बता सकता हूँ — बस पूछिए।",
            )
        elif crop:
            message = pick(
                ctx.lang,
                f"Nice — **{crop}**! Ask me about its treatment, watering, fertilizer, "
                "soil, or today's tasks.",
                f"बढ़िया — **{crop}**! इसके उपचार, सिंचाई, खाद, मिट्टी या आज के कार्यों के बारे में पूछिए।",
            )
        else:
            message = pick(
                ctx.lang,
                "I'm here to help with your crops — ask me anything about disease, "
                "treatment, soil, recovery, or today's tasks.",
                "मैं आपकी फसलों की मदद के लिए यहाँ हूँ — रोग, उपचार, मिट्टी, सुधार या "
                "आज के कार्यों के बारे में कुछ भी पूछिए।",
            )
        return AssistantReplyOut(
            intent="report",
            lang=ctx.lang,
            message=message,
            sections=self._capability_sections(ctx.lang),
        )

    # ── Shared builders ───────────────────────────────────────────────────

    def _fallback(self, intent: str, lang: str, message: str) -> AssistantReplyOut:
        """A polite, useful reply that keeps the caller's intent for UI affordances."""
        return AssistantReplyOut(
            intent=intent,
            lang=lang,
            message=message,
            sections=self._capability_sections(lang),
        )

    def _capability_sections(self, lang: str) -> list[AssistantSection]:
        return [
            AssistantSection(
                title=pick(lang, "Try asking", "ये प्रश्न पूछिए"),
                body=pick(
                    lang,
                    "• What disease does my crop have?\n"
                    "• How do I treat this disease?\n"
                    "• What does this disease mean?\n"
                    "• Can I use neem oil?\n"
                    "• Read today's farming tasks.",
                    "• मेरी फसल में कौन सा रोग है?\n"
                    "• इस रोग का इलाज कैसे करूँ?\n"
                    "• इस रोग का क्या मतलब है?\n"
                    "• क्या मैं नीम तेल का उपयोग कर सकता हूँ?\n"
                    "• आज के खेती के कार्य सुनाओ।",
                ),
            )
        ]

    def _plan_sections(self, lang: str, rec) -> list[AssistantSection]:
        """Treatment plan sub-blocks from a recommendation (reused by builders)."""
        sections: list[AssistantSection] = []
        if rec.overview:
            sections.append(
                AssistantSection(title=pick(lang, "Overview", "अवलोकन"), body=rec.overview)
            )
        if rec.homemade_remedies:
            remedy = rec.homemade_remedies[0]
            sections.append(
                AssistantSection(
                    title=pick(lang, "Homemade remedy", "घरेलू उपाय"),
                    body=f"{remedy.title}: {remedy.instructions} ({remedy.frequency})",
                )
            )
        if rec.organic_remedies:
            organic = rec.organic_remedies[0]
            sections.append(
                AssistantSection(
                    title=pick(lang, "Organic remedy", "जैविक उपाय"),
                    body=f"{organic.title}: {organic.application} ({organic.frequency})",
                )
            )
        if rec.chemical_recommendations:
            chemical = rec.chemical_recommendations[0]
            sections.append(
                AssistantSection(
                    title=pick(lang, "Chemical option", "रासायनिक विकल्प"),
                    body=f"{chemical.product} — {chemical.dosage}, {chemical.application_interval}",
                )
            )
        return sections

    async def _latest_scan(self, user: User) -> Scan | None:
        rows, _ = await ScanService(self.db).list_scans(user.id, page_size=1)
        return rows[0] if rows else None

    async def _crop_name(self, scan: Scan) -> str | None:
        if scan.crop_id is None:
            return None
        crop = await self.db.get(Crop, scan.crop_id)
        if crop is None:
            return None
        return crop.common_name or crop.name

    async def _plan_for_subject(self, crop: str | None, disease: str | None, scan: Scan | None):
        """Best-effort treatment plan: a named disease first, else the latest scan."""
        if disease:
            drow = await load_disease(self.db, disease, crop)
            if drow is not None:
                try:
                    return await RecommendationService(self.db).for_disease(drow.id)
                except (RecommendationNotFoundError, CatalogUnavailableError):
                    return None
        if scan is not None and scan.disease_id is not None:
            try:
                return await RecommendationService(self.db).for_scan(scan)
            except (RecommendationNotFoundError, CatalogUnavailableError):
                return None
        return None

    def _scan_summary_section(
        self, scan: Scan, lang: str, crop: str | None = None
    ) -> AssistantSection:
        crop = crop or "—"
        return AssistantSection(
            title=pick(lang, "What the scan shows", "स्कैन क्या दिखाता है"),
            body=pick(
                lang,
                f"Crop: {crop} · Part: {scan.part_type or '—'} · "
                f"Confidence: {scan.confidence:.0%} · Severity: {scan.severity or '—'} · "
                f"Stage: {scan.stage or '—'} · Scanned: {scan.created_at:%d %b %Y}",
                f"फसल: {crop} · भाग: {scan.part_type or '—'} · "
                f"विश्वास: {scan.confidence:.0%} · गंभीरता: {scan.severity or '—'} · "
                f"अवस्था: {scan.stage or '—'} · स्कैन: {scan.created_at:%d %b %Y}",
            ),
        )


# ── LLM provider (optional seam) ───────────────────────────────────────────


class LLMNotConfiguredError(RuntimeError):
    """Raised when the LLM provider is selected but can't actually run."""


def build_system_prompt(snapshot: str, lang: str) -> str:
    """Pure prompt builder — unit-testable without any API call."""
    guidance = (
        "Reply in Hindi (Devanagari script). Keep it warm, concise and practical."
        if lang == "hi"
        else "Reply in English. Keep it warm, concise and practical."
    )
    return (
        "You are the NeuroPlant AI farming assistant for Indian farmers. Answer ONLY "
        "about agriculture, crops, plant diseases, treatment, soil care, recovery and "
        "farming tasks.\n"
        "Ground every answer in the farmer's project data below when relevant. If the "
        "data has no answer, give practical general farming advice. If the question is "
        "not about farming, politely say you specialize in crop and farming guidance.\n\n"
        "=== THE FARMER'S PROJECT DATA ===\n"
        f"{snapshot}\n\n"
        f"{guidance}"
    )


def build_message_turns(history) -> list[dict[str, str]]:
    """Recent transcript as API message turns (assistant/user), in order."""
    return [
        {"role": "assistant" if item.role == "assistant" else "user", "content": item.content}
        for item in history
        if item.content
    ]


async def build_project_snapshot(user: User, db: AsyncSession) -> str:
    """Assemble the farmer's current project state for the LLM system prompt.

    Reuses the existing engine services — the LLM never re-implements policy; it
    reads the same summaries the rest of the UI shows. Best-effort: a missing
    scan or an unseeded catalog degrades to an explicit "not yet" line.
    """
    lines: list[str] = []
    scans, _ = await ScanService(db).list_scans(user.id, page_size=1)
    scan = scans[0] if scans else None
    if scan is None:
        lines.append("Scans: none yet (the farmer has not scanned any crop).")
    else:
        lines.append(
            f"Latest scan ({scan.created_at:%d %b %Y}): crop_id={scan.crop_id}, "
            f"part={scan.part_type or 'n/a'}, predicted_disease={scan.disease_name or 'healthy'}, "
            f"confidence={scan.confidence:.0%}, severity={scan.severity or 'n/a'}, "
            f"stage={scan.stage or 'n/a'}."
        )
        if scan.disease_id is not None:
            try:
                rec = await RecommendationService(db).for_scan(scan)
                lines.append(
                    f"Treatment plan: overview={rec.overview or 'n/a'} "
                    f"fertilizer={rec.fertilizer or 'n/a'} watering={rec.watering or 'n/a'}"
                )
                if rec.homemade_remedies:
                    r = rec.homemade_remedies[0]
                    lines.append(
                        f"First homemade remedy: {r.title} — {r.instructions} ({r.frequency})"
                    )
            except (RecommendationNotFoundError, CatalogUnavailableError):
                lines.append("Treatment plan: not curated yet.")
            try:
                soil = await SoilRecommendationService(db).for_scan(scan)
                lines.append(
                    f"Soil health: {soil.soil_health.label} ({soil.soil_health.score:.1f}/5) — "
                    f"{soil.soil_health.summary}"
                )
            except (SoilNotFoundError, SoilCatalogUnavailableError):
                lines.append("Soil plan: not curated yet.")
            try:
                tracker = await RecoveryTrackerService(db).tracker(scan)
                lines.append(
                    f"Recovery: {tracker.status}, {round(tracker.recovery_percentage * 100)}% "
                    f"recovered, {tracker.total_treatments} treatments, {tracker.risk} risk."
                )
            except Exception:  # noqa: BLE001 — recovery is best-effort context
                lines.append("Recovery: no data yet.")
    try:
        dashboard = await CalendarService(db).dashboard(user)
        today = datetime.now(UTC).replace(tzinfo=None).date()
        tasks: list[str] = []
        for schedule in dashboard.schedules:
            for task in schedule.tasks:
                if task.completed_at is not None:
                    continue
                due = task.due_at.date()
                if due == today:
                    tasks.append(f"{schedule.crop_name}: {task.title} (today)")
                elif due < today:
                    tasks.append(f"{schedule.crop_name}: {task.title} (overdue)")
        lines.append(f"Calendar: {'; '.join(tasks) if tasks else 'no tasks due today.'}")
    except Exception:  # noqa: BLE001 — calendar is best-effort context
        lines.append("Calendar: no schedules yet.")
    return "\n".join(lines)


class LLMConversationProvider:
    """Real-LLM provider behind the same :class:`ConversationProvider` protocol.

    Used only when ``llm_api_key`` is configured; native dev (no key) keeps the
    local engine. The current transport is Anthropic Messages; other vendors are
    a settings-only change once wired.
    """

    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self._settings = settings or get_settings()

    async def answer(self, ctx: AssistantContext) -> AssistantReplyOut:
        if not self._settings.llm_api_key:
            raise LLMNotConfiguredError("llm_api_key is not set")
        snapshot = await build_project_snapshot(ctx.user, self.db)
        system = build_system_prompt(snapshot, ctx.lang)
        turns = build_message_turns(ctx.history)
        text = await self._call_api(system, turns, ctx.query)
        return AssistantReplyOut(
            intent="conversation", lang=ctx.lang, message=text.strip(), sections=[]
        )

    async def _call_api(self, system: str, turns: list[dict[str, str]], query: str) -> str:
        api_key = self._settings.llm_api_key
        if not api_key:
            raise LLMNotConfiguredError("llm_api_key is not set")
        if self._settings.llm_provider != "anthropic":
            raise LLMNotConfiguredError(
                f"llm_provider '{self._settings.llm_provider}' is not wired yet; "
                "set llm_provider=anthropic"
            )
        payload = {
            "model": self._settings.llm_model,
            "max_tokens": 1024,
            "system": system,
            "messages": [*turns, {"role": "user", "content": query}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )


def select_conversation_provider(
    db: AsyncSession, settings: Settings | None = None
) -> ConversationProvider:
    """The provider for this request: LLM when a key is configured, else local."""
    settings = settings or get_settings()
    if settings.llm_api_key:
        return LLMConversationProvider(db, settings)
    return LocalConversationProvider(db)


# ── Module-level copy helpers ──────────────────────────────────────────────


def _no_scan_text(lang: str) -> str:
    return pick(
        lang,
        "I don't see any scans yet. Go to Scan Crop and photograph your crop's leaf — "
        "then I can tell you about its disease, treatment and soil.",
        "मैंने अभी तक कोई स्कैन नहीं देखा। अपनी फसल की पत्ती की फोटो स्कैन क्रॉप में "
        "लें — फिर मैं रोग, उपचार और मिट्टी के बारे में बता सकता हूँ।",
    )


def _no_disease_text(lang: str) -> str:
    return pick(
        lang,
        "Your latest scan didn't find a disease, so there's nothing to treat yet. "
        "Re-scan if new symptoms appear.",
        "आपके सबसे हालिया स्कैन में कोई रोग नहीं मिला, इसलिए इलाज की आवश्यकता नहीं है। "
        "नए लक्षण दिखने पर दोबारा स्कैन करें।",
    )


def _no_plan_text(lang: str, disease_name: str) -> str:
    return pick(
        lang,
        f"I couldn't find a curated treatment plan for {disease_name} yet. Ask me about "
        "soil care or today's tasks in the meantime.",
        f"अभी {disease_name} के लिए कोई उपचार योजना नहीं मिली। तब तक मिट्टी की देखभाल "
        "या आज के कार्यों के बारे में पूछिए।",
    )


def _explain_no_disease_text(lang: str) -> str:
    return pick(
        lang,
        "I don't know which disease you mean yet. Scan your crop's leaf or name the "
        "disease, and I'll explain it in simple words.",
        "अभी मुझे नहीं पता कि आप किस रोग की बात कर रहे हैं। अपनी फसल की पत्ती स्कैन "
        "करें या रोग का नाम बताएँ, मैं सरल शब्दों में समझाऊँगा।",
    )


def _pathogen_hi(pathogen: str) -> str:
    """Roughly localize a pathogen type label for the explain reply."""
    return {
        "fungal": "कवक रोग",
        "fungus": "कवक रोग",
        "bacterial": "जीवाणु रोग",
        "viral": "वायरल रोग",
        "virus": "वायरल रोग",
        "disease": "रोग",
    }.get(pathogen, "रोग")


def _risk_hi(risk: str, lang: str) -> str:
    return pick(lang, risk, _RISK_HI.get(risk, risk))
