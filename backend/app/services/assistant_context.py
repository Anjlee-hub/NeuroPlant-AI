"""Assistant conversation context + memory (M3.1).

M3.1 turns the assistant from a keyword router into a *conversational* layer.
Everything that describes *what is being talked about* lives here, decoupled
from the engine that decides the words:

- :class:`CatalogEntityExtractor` — resolves free-text mentions of catalog
  crops/diseases ("my tomato has early blight") against the knowledge catalog.
- :class:`ConversationMemory` — tracks the current subject across turns and
  resolves anaphora ("it", "this disease") to the last-mentioned entity. It is
  seeded from recent history, so a page reload keeps the context alive.
- :class:`AssistantContext` — the immutable per-query bundle handed to a
  conversation provider (user, query, chosen language, history, clock).

Language helpers (:func:`pick`, :func:`detect_lang`, :func:`greeting_for`) are
kept here so both providers (local + LLM) share one localization source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Crop, Disease
from app.models.user import User
from app.schemas.assistant import ConversationMessageOut

# Reply languages. ``lang`` is optional on the request: when omitted the
# service auto-detects it from the query's script (Devanagari → Hindi).
ASSISTANT_LANGS = ("en", "hi")


def pick(lang: str, en: str, hi: str) -> str:
    """Localized string: Hindi template when ``lang`` is hi, else English."""
    return hi if lang == "hi" else en


def detect_lang(query: str) -> str:
    """Detect the reply language from the query's script (Devanagari → hi)."""
    if any(0x0900 <= ord(ch) <= 0x097F for ch in query):
        return "hi"
    return "en"


def greeting_for(lang: str, hour: int) -> str:
    """Time-of-day greeting ("Good morning" / "शुभ संध्या") in the reply language."""
    if 5 <= hour < 12:
        en, hi = "Good morning", "सुप्रभात"
    elif 12 <= hour < 17:
        en, hi = "Good afternoon", "शुभ दोपहर"
    elif 17 <= hour < 21:
        en, hi = "Good evening", "शुभ संध्या"
    else:
        en, hi = "Good night", "शुभ रात्रि"
    return pick(lang, en, hi)


class CatalogEntityExtractor:
    """Resolve crop/disease names from free text against the catalog.

    Names are matched longest-first with an optional plural suffix and English
    word boundaries, so "my tomato plants have early blight" yields
    ``crop="tomato"`` / ``disease="Early Blight"`` while the *hi* in *this*
    never matches the greeting keyword.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._crops: list[str] | None = None
        self._diseases: list[str] | None = None

    async def _load(self) -> None:
        if self._crops is not None:
            return
        crop_names: set[str] = set()
        for crop in (await self._db.scalars(select(Crop))).all():
            crop_names.add(crop.name)
            if crop.common_name:
                crop_names.add(crop.common_name)
        disease_names: set[str] = set((await self._db.scalars(select(Disease.name))).all())
        self._crops = sorted(crop_names, key=len, reverse=True)
        self._diseases = sorted(disease_names, key=len, reverse=True)

    @staticmethod
    def _find(text: str, names: list[str]) -> str | None:
        lowered = text.lower()
        for name in names:
            base = name.lower()
            if re.search(rf"\b{re.escape(base)}(?:es|s)?\b", lowered):
                return name
        return None

    async def crop_in(self, text: str) -> str | None:
        await self._load()
        return self._find(text, self._crops or [])

    async def disease_in(self, text: str) -> str | None:
        await self._load()
        return self._find(text, self._diseases or [])


class ConversationMemory:
    """Tracks the current subject (crop/disease) across turns.

    Seeded from recent history so a page reload keeps context; updated from each
    user query and assistant reply; :meth:`resolve` prefers an explicit mention
    in the query and otherwise carries the remembered subject — the anaphora
    rule that makes "How do I treat it?" refer to the last-mentioned disease.
    """

    def __init__(
        self, extractor: CatalogEntityExtractor, history: list[ConversationMessageOut]
    ) -> None:
        self._extractor = extractor
        self._history = history
        self.crop: str | None = None
        self.disease: str | None = None

    async def seed(self) -> None:
        """Prime the subject from recent history (newest mention wins)."""
        for message in reversed(self._history):
            if self.crop is None:
                self.crop = await self._extractor.crop_in(message.content)
            if self.disease is None:
                self.disease = await self._extractor.disease_in(message.content)
            if self.crop is not None and self.disease is not None:
                break

    async def remember(self, text: str) -> None:
        """Fold a new turn into the tracked subject."""
        crop = await self._extractor.crop_in(text)
        disease = await self._extractor.disease_in(text)
        if crop is not None:
            self.crop = crop
        if disease is not None:
            self.disease = disease

    async def resolve(self, query: str) -> tuple[str | None, str | None]:
        """Explicit mention wins; otherwise carry the remembered subject."""
        crop = await self._extractor.crop_in(query)
        disease = await self._extractor.disease_in(query)
        return crop or self.crop, disease or self.disease


@dataclass
class AssistantContext:
    """Everything a conversation provider needs to answer one query."""

    user: User
    query: str
    lang: str
    history: list[ConversationMessageOut]
    now: datetime


async def load_disease(db: AsyncSession, name: str, crop: str | None = None) -> Disease | None:
    """Look up a catalog disease by name, optionally disambiguated by crop.

    Tomato and potato both carry a Late Blight catalog entry; when the farmer
    names the crop, match against it (by common *or* catalog name).
    """
    query = (
        select(Disease)
        .join(Crop, Disease.crop_id == Crop.id)
        .options(selectinload(Disease.crop))
        .where(Disease.name == name)
    )
    if crop:
        query = query.where(or_(Crop.name == crop, Crop.common_name == crop))
    return await db.scalar(query)
