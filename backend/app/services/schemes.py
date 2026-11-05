"""Verified-source government scheme catalog and eligibility checks."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheme import GovernmentScheme, SchemeUsageEvent
from app.schemas.scheme import (
    EligibilityCheckIn,
    EligibilityCheckOut,
    GovernmentSchemeCreate,
)

SCHEME_SOURCE_UNAVAILABLE = (
    "No government scheme records are loaded. Scheme names, amounts, and links "
    "are not inferred or fabricated."
)


class GovernmentSchemeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payload: GovernmentSchemeCreate) -> GovernmentScheme:
        data = payload.model_dump()
        for field in ("official_application_url", "source_url"):
            if data[field] is not None:
                data[field] = str(data[field])
        scheme = GovernmentScheme(**data, is_active=True)
        self.db.add(scheme)
        await self.db.commit()
        await self.db.refresh(scheme)
        return scheme

    async def list(
        self,
        user_id: int,
        *,
        state_code: str | None = None,
        crop_name: str | None = None,
        farmer_category: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[GovernmentScheme], int]:
        statement = select(GovernmentScheme).where(GovernmentScheme.is_active.is_(True))
        if category:
            statement = statement.where(GovernmentScheme.category.ilike(category))
        records = list(await self.db.scalars(statement.order_by(GovernmentScheme.name)))

        def matches(scheme: GovernmentScheme) -> bool:
            return (
                (
                    not state_code
                    or not scheme.state_codes
                    or state_code.upper() in scheme.state_codes
                )
                and (
                    not crop_name
                    or not scheme.crops
                    or crop_name.casefold() in {crop.casefold() for crop in scheme.crops}
                )
                and (
                    not farmer_category
                    or not scheme.farmer_categories
                    or farmer_category.casefold()
                    in {item.casefold() for item in scheme.farmer_categories}
                )
            )

        matched = [scheme for scheme in records if matches(scheme)]
        items = matched[(page - 1) * page_size : page * page_size]
        self.db.add_all(
            [
                SchemeUsageEvent(
                    user_id=user_id,
                    scheme_id=scheme.id,
                    action="view",
                    state_code=state_code.upper() if state_code else None,
                    crop_name=crop_name,
                    created_at=datetime.now(UTC),
                )
                for scheme in items
            ]
        )
        if items:
            await self.db.commit()
        return items, len(matched)

    async def get(self, user_id: int, scheme_id: int) -> GovernmentScheme | None:
        scheme = await self.db.scalar(
            select(GovernmentScheme).where(
                GovernmentScheme.id == scheme_id,
                GovernmentScheme.is_active.is_(True),
            )
        )
        if scheme is not None:
            self.db.add(
                SchemeUsageEvent(
                    user_id=user_id,
                    scheme_id=scheme.id,
                    action="view",
                    created_at=datetime.now(UTC),
                )
            )
            await self.db.commit()
        return scheme

    async def check_eligibility(
        self,
        user_id: int,
        scheme_id: int,
        payload: EligibilityCheckIn,
    ) -> EligibilityCheckOut | None:
        scheme = await self.db.scalar(
            select(GovernmentScheme).where(
                GovernmentScheme.id == scheme_id,
                GovernmentScheme.is_active.is_(True),
            )
        )
        if scheme is None:
            return None

        supplied = {
            "state_code": payload.state_code.upper() if payload.state_code else None,
            "crop_name": payload.crop_name,
            "farmer_category": payload.farmer_category,
        }
        matches: list[str] = []
        unmet: list[str] = []
        unknown: list[str] = []
        constraints = (
            ("state_code", scheme.state_codes),
            ("crop_name", scheme.crops),
            ("farmer_category", scheme.farmer_categories),
        )
        for field, allowed in constraints:
            value = supplied[field]
            if not allowed:
                continue
            if value is None:
                unknown.append(f"{field} was not provided")
            elif value.casefold() in {item.casefold() for item in allowed}:
                matches.append(f"{field} matches the published scheme scope")
            else:
                unmet.append(f"{field} does not match the published scheme scope")

        for field, allowed in scheme.eligibility_rules.items():
            value = supplied.get(field)
            if value is None:
                unknown.append(f"{field} was not provided")
            elif value.casefold() in {item.casefold() for item in allowed}:
                matches.append(f"{field} matches the published rule")
            else:
                unmet.append(f"{field} does not match the published rule")

        if unmet:
            outcome = "not_eligible"
            explanation = "One or more provided details do not match the recorded scheme rules."
        elif unknown or not scheme.eligibility_rules:
            outcome = "unknown"
            explanation = (
                "The available structured rules are insufficient to determine eligibility."
            )
        else:
            outcome = "potentially_eligible"
            explanation = (
                "Provided details match the recorded rules; confirm with the official authority."
            )

        self.db.add(
            SchemeUsageEvent(
                user_id=user_id,
                scheme_id=scheme.id,
                action="eligibility_check",
                state_code=supplied["state_code"],
                crop_name=payload.crop_name,
                created_at=datetime.now(UTC),
            )
        )
        await self.db.commit()
        return EligibilityCheckOut(
            scheme_id=scheme.id,
            outcome=outcome,
            matched_rules=matches,
            unmet_rules=unmet + unknown,
            explanation=explanation,
        )
