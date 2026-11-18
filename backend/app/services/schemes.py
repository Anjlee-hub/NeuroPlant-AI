"""Verified-source government scheme catalog and eligibility checks."""

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheme import (
    GovernmentScheme,
    SavedGovernmentScheme,
    SchemeUsageEvent,
)
from app.models.user import FarmerProfile
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
        existing = await self.db.scalar(
            select(GovernmentScheme).where(
                or_(
                    GovernmentScheme.name.ilike(data["name"]),
                    GovernmentScheme.source_url == str(data["source_url"]),
                )
            )
        )
        if existing is not None:
            raise ValueError("A scheme with the same name or source URL already exists.")
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
        district_code: str | None = None,
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[GovernmentScheme], int]:
        statement = select(GovernmentScheme)
        if category:
            statement = statement.where(GovernmentScheme.category.ilike(category))
        if status:
            statement = statement.where(GovernmentScheme.status == status)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    GovernmentScheme.name.ilike(term),
                    GovernmentScheme.description.ilike(term),
                    GovernmentScheme.department.ilike(term),
                    GovernmentScheme.source_name.ilike(term),
                )
            )
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
                and (
                    not district_code
                    or not scheme.district_codes
                    or district_code.casefold()
                    in {item.casefold() for item in scheme.district_codes}
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
            select(GovernmentScheme).where(GovernmentScheme.id == scheme_id)
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
            select(GovernmentScheme).where(GovernmentScheme.id == scheme_id)
        )
        if scheme is None:
            return None

        profile = await self.db.scalar(
            select(FarmerProfile).where(FarmerProfile.user_id == user_id)
        )
        profile_crops = (
            [str(item) for item in profile.crops_grown]
            if profile is not None and profile.crops_grown
            else []
        )
        supplied = {
            "state_code": payload.state_code.upper() if payload.state_code else None,
            "district_code": payload.district_code,
            "crop_name": payload.crop_name
            or (profile_crops[0] if len(profile_crops) == 1 else None),
            "farmer_category": payload.farmer_category,
            "landholding_acres": payload.landholding_acres
            if payload.landholding_acres is not None
            else (profile.farm_size if profile is not None else None),
        }
        matches: list[str] = []
        unmet: list[str] = []
        unknown: list[str] = []
        constraints = (
            ("state_code", scheme.state_codes),
            ("district_code", scheme.district_codes),
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
            elif field == "landholding_acres" and isinstance(value, (int, float)):
                matched_numeric = False
                for rule in allowed:
                    rule_text = rule.strip().lower()
                    if (
                        rule_text.startswith("<=")
                        and float(value) <= float(rule_text[2:].strip())
                    ) or (
                        rule_text.startswith(">=")
                        and float(value) >= float(rule_text[2:].strip())
                    ) or (
                        rule_text.startswith("<")
                        and float(value) < float(rule_text[1:].strip())
                    ) or (
                        rule_text.startswith(">")
                        and float(value) > float(rule_text[1:].strip())
                    ):
                        matched_numeric = True
                if matched_numeric:
                    matches.append(f"{field} matches the published rule")
                else:
                    unmet.append(f"{field} does not match the published rule")
            elif (
                isinstance(value, str)
                and value.casefold() in {item.casefold() for item in allowed}
            ):
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

    async def list_saved(self, user_id: int) -> list[GovernmentScheme]:
        rows = list(
            await self.db.scalars(
                select(GovernmentScheme)
                .join(
                    SavedGovernmentScheme,
                    SavedGovernmentScheme.scheme_id == GovernmentScheme.id,
                )
                .where(SavedGovernmentScheme.user_id == user_id)
                .order_by(GovernmentScheme.name)
            )
        )
        return rows

    async def is_saved(self, user_id: int, scheme_id: int) -> bool:
        row = await self.db.scalar(
            select(SavedGovernmentScheme).where(
                SavedGovernmentScheme.user_id == user_id,
                SavedGovernmentScheme.scheme_id == scheme_id,
            )
        )
        return row is not None

    async def save(self, user_id: int, scheme_id: int) -> bool:
        scheme = await self.db.scalar(
            select(GovernmentScheme).where(GovernmentScheme.id == scheme_id)
        )
        if scheme is None:
            return False
        existing = await self.db.scalar(
            select(SavedGovernmentScheme).where(
                SavedGovernmentScheme.user_id == user_id,
                SavedGovernmentScheme.scheme_id == scheme_id,
            )
        )
        if existing is None:
            self.db.add(
                SavedGovernmentScheme(user_id=user_id, scheme_id=scheme_id)
            )
            await self.db.commit()
        return True

    async def remove_saved(self, user_id: int, scheme_id: int) -> bool:
        row = await self.db.scalar(
            select(SavedGovernmentScheme).where(
                SavedGovernmentScheme.user_id == user_id,
                SavedGovernmentScheme.scheme_id == scheme_id,
            )
        )
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.commit()
        return True
