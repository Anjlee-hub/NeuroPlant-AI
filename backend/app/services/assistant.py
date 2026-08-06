"""Voice AI assistant service (M3, Task 6).

A rule-based conversational layer — deliberately *no LLM*, consistent with the
project's offline / policy-as-constants philosophy. It routes a free-text query
(English or Hindi) to the **existing** engines and stitches their output into a
localized, speakable reply:

    greeting / help  → static bilingual copy
    disease          → latest scan                  → ScanService
    treatment        → care plan for that disease   → RecommendationService
    fertilizer       → fertilizer guidance          → RecommendationService
    soil             → disease-aware soil plan      → SoilRecommendationService
    recovery         → recovery tracker             → RecoveryTrackerService
    calendar         → today's farming tasks        → CalendarService.dashboard

Intent routing is bilingual keyword matching (documented tables below); reply
templates are bilingual (``en``/``hi``). Catalog *content* (disease names,
remedies, crops) stays English — exactly like every other UI surface. New
languages extend the keyword + template tables only; the routing structure and
this module's contract do not change. No logic is duplicated: every fact comes
from the engine services this module composes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.catalog import Crop
from app.models.scan import Scan
from app.models.user import User
from app.schemas.assistant import AssistantReplyOut, AssistantSection
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

ASSISTANT_LANGS = ("en", "hi")

# ── Bilingual intent keywords ─────────────────────────────────────────────
# (English phrases, Hindi substrings) matched against the lowercased query.
# ORDER MATTERS: earlier intents win, so "How do I treat this disease?" lands
# on treatment (not disease) and "What fertilizer should I use?" on fertilizer.

_INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
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
        ),
        ("इलाज", "दवा", "उपचार", "छिड़काव", "स्प्रे"),
    ),
    (
        "fertilizer",
        ("fertilizer", "fertilise", "fertilize", "manure", "nutrient", "feed"),
        ("खाद", "उर्वरक", "पोषक"),
    ),
    ("soil", ("soil", "ph", "earth", "land"), ("मिट्टी", "भूमि", "मृदा")),
    (
        "calendar",
        (
            "calendar",
            "today",
            "task",
            "reminder",
            "todo",
            "to-do",
            "schedule",
            "watering",
            "irrigat",
        ),
        ("आज", "कार्य", "काम", "रिमाइंडर", "सिंचाई"),
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
        ),
        ("सुधार", "ठीक", "पुनर्प्राप्ति", "बेहतर"),
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
        ),
        ("रोग", "बीमारी", "समस्या", "क्या हुआ"),
    ),
    (
        "greeting",
        (
            "hello",
            "hi ",
            "hi,",
            "hey",
            "namaste",
            "namaskar",
            "good morning",
            "good evening",
            "good afternoon",
            "greetings",
        ),
        ("नमस्ते", "नमस्कार", "हैलो", "नमो"),
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
            "what can i ask",
        ),
        ("मदद", "क्या कर", "सहायक"),
    ),
)

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


def _pick(lang: str, en: str, hi: str) -> str:
    """Localized string: Hindi template when ``lang`` is hi, else English."""
    return hi if lang == "hi" else en


def _detect_lang(query: str) -> str:
    """Detect the reply language from the query's script (Devanagari → hi)."""
    if any(0x0900 <= ord(ch) <= 0x097F for ch in query):
        return "hi"
    return "en"


def _detect_intent(query: str) -> str:
    """First intent whose English or Hindi keyword appears in the query."""
    lowered = query.lower()
    for intent, en_kw, hi_kw in _INTENT_KEYWORDS:
        if any(kw in lowered for kw in en_kw) or any(kw in lowered for kw in hi_kw):
            return intent
    return "fallback"


class AssistantService:
    """Answer farmer questions by composing the existing engine services."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def answer(self, user: User, query: str, lang: str | None = None) -> AssistantReplyOut:
        """Route a query to the matching builder and return the localized reply.

        Every engine call is best-effort: a missing scan, an unseeded catalog,
        or any unexpected error degrades to a helpful reply rather than a 500.
        """
        lang = lang if lang in ASSISTANT_LANGS else _detect_lang(query)
        intent = _detect_intent(query)
        builder = getattr(self, f"_reply_{intent}", self._reply_fallback)
        try:
            return await builder(user, lang)
        except Exception:
            logger.warning("assistant_reply_failed", intent=intent, exc_info=True)
            return await self._reply_fallback(user, lang)

    # ── Static intents ────────────────────────────────────────────────────

    async def _reply_greeting(self, _: User, lang: str) -> AssistantReplyOut:
        return AssistantReplyOut(
            intent="greeting",
            lang=lang,
            message=_pick(
                lang,
                "Namaste! I'm your NeuroPlant assistant. Ask me about your crop's "
                "disease, how to treat it, fertilizer, soil care, recovery, or today's "
                "farming tasks.",
                "नमस्ते! मैं आपका न्यूरोप्लांट सहायक हूँ। अपनी फसल के रोग, उपचार, "
                "खाद, मिट्टी, सुधार या आज के कार्यों के बारे में पूछिए।",
            ),
            sections=self._capability_sections(lang),
        )

    async def _reply_help(self, _: User, lang: str) -> AssistantReplyOut:
        return AssistantReplyOut(
            intent="help",
            lang=lang,
            message=_pick(
                lang,
                "I answer from your own farm data. Try one of these:",
                "मैं आपके अपने फार्म डेटा से उत्तर देता हूँ। इनमें से कुछ पूछिए:",
            ),
            sections=self._capability_sections(lang),
        )

    # ── Data-backed intents ───────────────────────────────────────────────

    async def _reply_disease(self, user: User, lang: str) -> AssistantReplyOut:
        scan = await self._latest_scan(user)
        if scan is None:
            return self._fallback("disease", lang, _no_scan_text(lang))
        if scan.disease_id is None:
            crop = await self._crop_name(scan)
            return AssistantReplyOut(
                intent="disease",
                lang=lang,
                message=_pick(
                    lang,
                    f"Your latest scan of {crop or 'your crop'} didn't find a disease "
                    "— it looks healthy. Keep an eye on it and re-scan if symptoms appear.",
                    f"{crop or 'आपकी फसल'} के सबसे हालिया स्कैन में कोई रोग नहीं मिला — "
                    "यह स्वस्थ दिखती है। नज़र रखें और लक्षण दिखने पर दोबारा स्कैन करें।",
                ),
                sections=[self._scan_summary_section(scan, lang, crop)],
            )

        crop = await self._crop_name(scan)
        conf = f"{scan.confidence:.0%}"
        sev = scan.severity or "unknown"
        sev_hi = _SEVERITY_HI.get(sev, sev)
        return AssistantReplyOut(
            intent="disease",
            lang=lang,
            message=_pick(
                lang,
                f"Your latest scan of {crop or 'your crop'} shows {scan.disease_name} "
                f"with {conf} confidence ({sev} severity).",
                f"{crop or 'आपकी फसल'} के सबसे हालिया स्कैन में {scan.disease_name} "
                f"दिखा — {conf} विश्वास ({sev_hi} गंभीरता)।",
            ),
            sections=[
                self._scan_summary_section(scan, lang, crop),
                AssistantSection(
                    title=_pick(lang, "Next step", "अगला कदम"),
                    body=_pick(
                        lang,
                        "Open the Crop Doctor for the full care plan and recovery "
                        "tracking, or ask: How do I treat this disease?",
                        "पूरी देखभाल योजना और सुधार ट्रैकिंग के लिए क्रॉप डॉक्टर खोलें, "
                        "या पूछें: इस रोग का इलाज कैसे करूँ?",
                    ),
                ),
            ],
        )

    async def _reply_treatment(self, user: User, lang: str) -> AssistantReplyOut:
        scan = await self._latest_scan(user)
        if scan is None or scan.disease_id is None:
            return self._fallback(
                "treatment",
                lang,
                _no_scan_text(lang) if scan is None else _no_disease_text(lang),
            )
        try:
            rec = await RecommendationService(self.db).for_scan(scan)
        except (RecommendationNotFoundError, CatalogUnavailableError):
            return self._fallback(
                "treatment",
                lang,
                _pick(
                    lang,
                    f"I couldn't find a curated treatment plan for {scan.disease_name} "
                    "yet. Ask me about soil care or today's tasks in the meantime.",
                    f"अभी {scan.disease_name} के लिए कोई उपचार योजना नहीं मिली। "
                    "तब तक मिट्टी की देखभाल या आज के कार्यों के बारे में पूछिए।",
                ),
            )

        crop = rec.disease.crop_name or await self._crop_name(scan) or "your crop"
        sections: list[AssistantSection] = []
        if rec.overview:
            sections.append(
                AssistantSection(title=_pick(lang, "Overview", "अवलोकन"), body=rec.overview)
            )
        if rec.homemade_remedies:
            remedy = rec.homemade_remedies[0]
            sections.append(
                AssistantSection(
                    title=_pick(lang, "Homemade remedy", "घरेलू उपाय"),
                    body=f"{remedy.title}: {remedy.instructions} ({remedy.frequency})",
                )
            )
        if rec.organic_remedies:
            organic = rec.organic_remedies[0]
            sections.append(
                AssistantSection(
                    title=_pick(lang, "Organic remedy", "जैविक उपाय"),
                    body=f"{organic.title}: {organic.application} ({organic.frequency})",
                )
            )
        if rec.chemical_recommendations:
            chemical = rec.chemical_recommendations[0]
            sections.append(
                AssistantSection(
                    title=_pick(lang, "Chemical option", "रासायनिक विकल्प"),
                    body=f"{chemical.product} — {chemical.dosage}, {chemical.application_interval}",
                )
            )

        return AssistantReplyOut(
            intent="treatment",
            lang=lang,
            message=_pick(
                lang,
                f"For {rec.disease.name} on {crop}, here is a treatment plan:",
                f"{rec.disease.name} के लिए {crop} पर एक उपचार योजना यह है:",
            ),
            sections=sections,
        )

    async def _reply_fertilizer(self, user: User, lang: str) -> AssistantReplyOut:
        scan = await self._latest_scan(user)
        if scan is None or scan.disease_id is None:
            return self._fallback(
                "fertilizer",
                lang,
                _no_scan_text(lang) if scan is None else _no_disease_text(lang),
            )
        try:
            rec = await RecommendationService(self.db).for_scan(scan)
        except (RecommendationNotFoundError, CatalogUnavailableError):
            return self._fallback(
                "fertilizer",
                lang,
                _pick(
                    lang,
                    f"I don't have fertilizer guidance for {scan.disease_name} yet.",
                    f"अभी {scan.disease_name} के लिए खाद संबंधी मार्गदर्शन उपलब्ध नहीं है।",
                ),
            )
        if not rec.fertilizer:
            return self._fallback(
                "fertilizer",
                lang,
                _pick(
                    lang,
                    f"I don't have specific fertilizer guidance for {scan.disease_name}.",
                    f"{scan.disease_name} के लिए विशेष खाद मार्गदर्शन मेरे पास नहीं है।",
                ),
            )

        crop = rec.disease.crop_name or await self._crop_name(scan) or "your crop"
        return AssistantReplyOut(
            intent="fertilizer",
            lang=lang,
            message=_pick(
                lang,
                f"For {rec.disease.name} on {crop}, keep the feeding balanced: {rec.fertilizer}",
                f"{rec.disease.name} के लिए {crop} पर खाद संतुलित रखें: {rec.fertilizer}",
            ),
            sections=[
                AssistantSection(
                    title=_pick(lang, "Fertilizer guidance", "खाद मार्गदर्शन"),
                    body=rec.fertilizer,
                )
            ],
        )

    async def _reply_soil(self, user: User, lang: str) -> AssistantReplyOut:
        scan = await self._latest_scan(user)
        if scan is None or scan.disease_id is None:
            return self._fallback(
                "soil",
                lang,
                _no_scan_text(lang) if scan is None else _no_disease_text(lang),
            )
        try:
            soil = await SoilRecommendationService(self.db).for_scan(scan)
        except (SoilNotFoundError, SoilCatalogUnavailableError):
            return self._fallback(
                "soil",
                lang,
                _pick(
                    lang,
                    f"I couldn't find a soil care plan for {scan.disease_name} yet.",
                    f"अभी {scan.disease_name} के लिए मिट्टी देखभाल योजना नहीं मिली।",
                ),
            )

        health = soil.soil_health
        crop = soil.disease.crop_name or await self._crop_name(scan) or "your crop"
        label = _SOIL_HEALTH_HI.get(health.label, health.label)
        care_lines: list[str] = []
        if soil.recommended_soil_type:
            care_lines.append(soil.recommended_soil_type)
        if soil.ph_range:
            care_lines.append(_pick(lang, f"pH: {soil.ph_range}", f"पीएच: {soil.ph_range}"))
        if soil.moisture_level:
            care_lines.append(soil.moisture_level)
        care_lines += soil.improvement_suggestions[:3]

        sections = [
            AssistantSection(
                title=_pick(lang, "Soil health", "मिट्टी की सेहत"),
                body=_pick(
                    lang,
                    f"Score {health.score:.1f}/5 — {health.label}. {health.summary}",
                    f"स्कोर {health.score:.1f}/5 — {label}. {health.summary}",
                ),
            )
        ]
        if care_lines:
            sections.append(
                AssistantSection(
                    title=_pick(lang, "Recommended care", "अनुशंसित देखभाल"),
                    body="\n".join(f"• {line}" for line in care_lines),
                )
            )
        if soil.soil_suitability:
            sections.append(
                AssistantSection(
                    title=_pick(lang, "Suitability", "उपयुक्तता"),
                    body=soil.soil_suitability,
                )
            )

        return AssistantReplyOut(
            intent="soil",
            lang=lang,
            message=_pick(
                lang,
                f"For {soil.disease.name} on {crop}, your soil health is "
                f"{health.label} ({health.score:.1f}/5). {health.summary}",
                f"{soil.disease.name} के लिए {crop} पर आपकी मिट्टी की सेहत "
                f"{label} ({health.score:.1f}/5) है। {health.summary}",
            ),
            sections=sections,
        )

    async def _reply_recovery(self, user: User, lang: str) -> AssistantReplyOut:
        scan = await self._latest_scan(user)
        if scan is None or scan.disease_id is None:
            return self._fallback(
                "recovery",
                lang,
                _no_scan_text(lang) if scan is None else _no_disease_text(lang),
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
                title=_pick(lang, "Recovery", "पुनर्प्राप्ति"),
                body=_pick(
                    lang,
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
                    title=_pick(lang, "Latest log", "नवीनतम उपचार"),
                    body=f"{last.treatment_applied}{note} ({last.applied_at:%d %b %Y})",
                )
            )

        return AssistantReplyOut(
            intent="recovery",
            lang=lang,
            message=_pick(
                lang,
                f"Your {crop or 'crop'} is {status} — {pct}% recovered, with {risk} risk.",
                f"आपकी {crop or 'फसल'} {status_hi} है — {pct}% ठीक, {risk_hi} जोखिम के साथ।",
            ),
            sections=sections,
        )

    async def _reply_calendar(self, user: User, lang: str) -> AssistantReplyOut:
        dashboard = await CalendarService(self.db).dashboard(user)
        today = datetime.now(UTC).replace(tzinfo=None).date()
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
                lang=lang,
                message=_pick(
                    lang,
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
                    title=_pick(lang, "Overdue", "विलंबित"),
                    body="\n".join(f"• {t}" for _, t in overdue_tasks),
                )
            )

        message = _pick(
            lang,
            f"Here are today's farming tasks ({len(today_tasks)} due today, "
            f"{len(overdue_tasks)} overdue).",
            f"आज के खेती के कार्य ये हैं ({len(today_tasks)} आज देय, {len(overdue_tasks)} विलंबित)।",
        )
        return AssistantReplyOut(intent="calendar", lang=lang, message=message, sections=sections)

    # ── Fallback + shared builders ────────────────────────────────────────

    async def _reply_fallback(self, _: User, lang: str) -> AssistantReplyOut:
        return self._fallback(
            "fallback",
            lang,
            _pick(
                lang,
                "I couldn't find an answer for that. Ask me about your crop's disease, "
                "how to treat it, fertilizer, soil care, recovery, or today's tasks.",
                "मैं इसका उत्तर नहीं ढूँढ सका। अपनी फसल के रोग, उपचार, खाद, मिट्टी, "
                "सुधार या आज के कार्यों के बारे में पूछिए।",
            ),
        )

    def _fallback(self, intent: str, lang: str, message: str) -> AssistantReplyOut:
        """A polite dead-end that keeps the caller's intent for UI affordances."""
        return AssistantReplyOut(
            intent=intent,
            lang=lang,
            message=message,
            sections=self._capability_sections(lang),
        )

    def _capability_sections(self, lang: str) -> list[AssistantSection]:
        return [
            AssistantSection(
                title=_pick(lang, "Try asking", "ये प्रश्न पूछिए"),
                body=_pick(
                    lang,
                    "• What disease does my crop have?\n"
                    "• How do I treat this disease?\n"
                    "• What fertilizer should I use?\n"
                    "• Read today's farming tasks.",
                    "• मेरी फसल में कौन सा रोग है?\n"
                    "• इस रोग का इलाज कैसे करूँ?\n"
                    "• मुझे कौन सी खाद इस्तेमाल करनी चाहिए?\n"
                    "• आज के खेती के कार्य सुनाओ।",
                ),
            )
        ]

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

    def _scan_summary_section(
        self, scan: Scan, lang: str, crop: str | None = None
    ) -> AssistantSection:
        crop = crop or "—"
        return AssistantSection(
            title=_pick(lang, "What the scan shows", "स्कैन क्या दिखाता है"),
            body=_pick(
                lang,
                f"Crop: {crop} · Part: {scan.part_type or '—'} · "
                f"Confidence: {scan.confidence:.0%} · Severity: {scan.severity or '—'} · "
                f"Stage: {scan.stage or '—'} · Scanned: {scan.created_at:%d %b %Y}",
                f"फसल: {crop} · भाग: {scan.part_type or '—'} · "
                f"विश्वास: {scan.confidence:.0%} · गंभीरता: {scan.severity or '—'} · "
                f"अवस्था: {scan.stage or '—'} · स्कैन: {scan.created_at:%d %b %Y}",
            ),
        )


def _no_scan_text(lang: str) -> str:
    return _pick(
        lang,
        "I don't see any scans yet. Go to Scan Crop and photograph your crop's leaf — "
        "then I can tell you about its disease, treatment and soil.",
        "मैंने अभी तक कोई स्कैन नहीं देखा। अपनी फसल की पत्ती की फोटो स्कैन क्रॉप में "
        "लें — फिर मैं रोग, उपचार और मिट्टी के बारे में बता सकता हूँ।",
    )


def _no_disease_text(lang: str) -> str:
    return _pick(
        lang,
        "Your latest scan didn't find a disease, so there's nothing to treat yet. "
        "Re-scan if new symptoms appear.",
        "आपके सबसे हालिया स्कैन में कोई रोग नहीं मिला, इसलिए इलाज की आवश्यकता नहीं है। "
        "नए लक्षण दिखने पर दोबारा स्कैन करें।",
    )
