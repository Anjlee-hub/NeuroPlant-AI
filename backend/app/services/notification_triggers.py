
"""Notification triggers — domain integration (M5, Task 3).

Integrates the existing NotificationService with domain features so that
domain events create notifications without duplicating domain logic.

All triggers are idempotent where repeated events are possible. Each trigger
uses the domain service's own data and calls NotificationService.create()
with the appropriate type and payload.

No push is implemented — the existing InAppTransport seam is preserved.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import ensure_aware
from app.models.calendar import CalendarTask, CropSchedule
from app.models.catalog import Crop
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.notifications import NotificationService
from app.services.recovery import RecoveryTrackerService
from app.services.weather import WeatherProviderError, WeatherService
from app.services.weather_risk import DiseaseRiskService

logger = get_logger(__name__)


# ── Idempotency helpers ──────────────────────────────────────────────────────


async def _notification_exists(
    db: AsyncSession,
    user_id: int,
    type: NotificationType,
    payload: dict,
    *,
    since_hours: int = 24,
) -> bool:
    """Check whether a similar notification was created recently.

    Prevents duplicate notifications for the same user/type/payload within
    the configured time window. Payload matching is loose: all keys in the
    new payload must match, while extra keys in the existing payload are OK.
    """
    since = datetime.now(UTC) - timedelta(hours=since_hours)

    result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.created_at >= since,
        )
    )

    for (notif_id,) in result.all():
        notif = await db.get(Notification, notif_id)

        if notif and _payload_matches(notif.payload or {}, payload):
            return True

    return False


def _payload_matches(existing: dict, new: dict) -> bool:
    """Return True when all new payload keys match the existing payload."""
    return all(existing.get(key) == value for key, value in new.items())


# ── Trigger service ──────────────────────────────────────────────────────────


class NotificationTriggerService:
    """Domain event → notification wiring.

    All methods are async and return the created Notification (or None if
    skipped due to idempotency, missing objects, or handled failures).

    Unexpected domain errors are logged and handled so notification failures
    do not unnecessarily disrupt the primary application workflow.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notify = NotificationService(db)

    # ── 1. Weather / disease risk ──────────────────────────────────────────

    async def maybe_notify_weather_risk(
        self,
        user_id: int,
        crop_id: int,
        lat: float,
        lng: float,
        *,
        notify_levels: tuple[str, ...] = ("high", "critical"),
    ) -> Notification | None:
        """Create weather_risk / disease_risk notifications when risk is high.

        Uses WeatherService and DiseaseRiskService to assess crop risk.
        Duplicate assessments for the same user/crop/location are suppressed.
        """
        user = await self.db.get(User, user_id)

        if not user:
            logger.warning(
                "notify_weather_risk_user_missing",
                user_id=user_id,
            )
            return None

        crop = await self.db.get(Crop, crop_id)

        if not crop:
            logger.warning(
                "notify_weather_risk_crop_missing",
                crop_id=crop_id,
            )
            return None

        try:
            weather_result = await WeatherService().get_current(lat, lng)

            risk_out = await DiseaseRiskService(self.db).assess_crop(
                crop_id,
                weather_result.data,
                is_fallback=weather_result.is_fallback,
            )

        except WeatherProviderError:
            logger.warning(
                "notify_weather_risk_provider_failed",
                user_id=user_id,
                crop_id=crop_id,
            )
            return None

        except Exception as exc:
            logger.exception(
                "notify_weather_risk_assess_failed",
                user_id=user_id,
                crop_id=crop_id,
                error=str(exc),
            )
            return None

        for risk in risk_out.risks:
            if risk.risk_level not in notify_levels:
                continue

            payload = {
                "crop_id": crop_id,
                "crop_name": crop.name,
                "disease_id": risk.disease_id,
                "disease_name": risk.disease_name,
                "risk_level": risk.risk_level,
                "risk_score": risk.risk_score,
                "lat": lat,
                "lng": lng,
                "is_fallback": weather_result.is_fallback,
            }

            notification_type = (
                NotificationType.DISEASE_RISK
                if risk.risk_level == "critical"
                else NotificationType.WEATHER_RISK
            )

            if await _notification_exists(
                self.db,
                user_id,
                notification_type,
                payload,
            ):
                logger.info(
                    "notify_weather_risk_idempotent_skip",
                    user_id=user_id,
                    crop_id=crop_id,
                    type=notification_type.value,
                )
                return None

            risk_kind = (
                "disease"
                if notification_type == NotificationType.DISEASE_RISK
                else "weather"
            )

            title = (
                f"{risk.risk_level.capitalize()} "
                f"{risk_kind} risk for {crop.name}"
            )

            return await self.notify.create(
                user_id,
                type=notification_type,
                title=title,
                message=risk.explanation,
                payload=payload,
                idempotency_key=(
                    f"weather-risk:{user_id}:{crop_id}:{risk.disease_id}:"
                    f"{datetime.now(UTC).date().isoformat()}:"
                    f"{lat:.4f}:{lng:.4f}"
                ),
            )

        return None

    # ── 2. Calendar / task reminder ────────────────────────────────────────

    async def maybe_notify_task_reminder(
        self,
        user_id: int,
        schedule_id: int,
        *,
        hours_before: int = 24,
    ) -> list[Notification]:
        """Create notifications for upcoming incomplete tasks.

        Tasks due within ``hours_before`` are notified. Duplicate reminders
        for the same task and due date are prevented.
        """
        user = await self.db.get(User, user_id)

        if not user:
            logger.warning(
                "notify_task_reminder_user_missing",
                user_id=user_id,
            )
            return []

        try:
            now = datetime.now(UTC)
            cutoff = now + timedelta(hours=hours_before)

            schedule = await self.db.scalar(
                select(CropSchedule).where(
                    CropSchedule.id == schedule_id,
                    CropSchedule.user_id == user_id,
                )
            )

            if not schedule:
                logger.warning(
                    "notify_task_reminder_schedule_missing",
                    user_id=user_id,
                    schedule_id=schedule_id,
                )
                return []

            # SQLite commonly stores datetimes without timezone information.
            # Normalize query boundaries to match the database representation.
            is_sqlite = self.db.get_bind().dialect.name == "sqlite"

            db_now = now.replace(tzinfo=None) if is_sqlite else now
            db_cutoff = cutoff.replace(tzinfo=None) if is_sqlite else cutoff

            tasks = await self.db.scalars(
                select(CalendarTask)
                .where(
                    CalendarTask.schedule_id == schedule_id,
                    CalendarTask.due_at >= db_now,
                    CalendarTask.due_at <= db_cutoff,
                    CalendarTask.completed_at.is_(None),
                )
                .order_by(CalendarTask.due_at, CalendarTask.id)
            )

            created: list[Notification] = []

            for task in tasks:
                due_at = ensure_aware(task.due_at)

                payload = {
                    "schedule_id": schedule_id,
                    "task_id": task.id,
                    "task_kind": task.kind,
                    "task_title": task.title,
                    "due_at": due_at.isoformat(),
                }

                if await _notification_exists(
                    self.db,
                    user_id,
                    NotificationType.TASK_REMINDER,
                    payload,
                    since_hours=48,
                ):
                    continue

                notification = await self.notify.create(
                    user_id,
                    type=NotificationType.TASK_REMINDER,
                    title=f"Upcoming task: {task.title}",
                    message=f"Due {due_at.strftime('%Y-%m-%d %H:%M UTC')}",
                    payload=payload,
                    idempotency_key=(
                        f"calendar-task:{task.id}:{due_at.isoformat()}"
                    ),
                )

                if notification is not None:
                    created.append(notification)

            return created

        except Exception as exc:
            logger.exception(
                "notify_task_reminder_failed",
                user_id=user_id,
                schedule_id=schedule_id,
                error=str(exc),
            )
            return []

    # ── 3. Treatment / recovery reminder ──────────────────────────────────

    async def maybe_notify_treatment_reminder(
        self,
        user_id: int,
        scan_id: int,
    ) -> Notification | None:
        """Create a treatment reminder based on recovery tracker history.

        Uses the latest recovery log and documented treatment resume intervals
        to determine whether a follow-up treatment reminder is due.
        """
        user = await self.db.get(User, user_id)

        if not user:
            logger.warning(
                "notify_treatment_reminder_user_missing",
                user_id=user_id,
            )
            return None

        try:
            from app.models.scan import Scan

            scan = await self.db.get(Scan, scan_id)

            if not scan or scan.user_id != user_id:
                logger.warning(
                    "notify_treatment_reminder_scan_missing",
                    user_id=user_id,
                    scan_id=scan_id,
                )
                return None

            tracker_out = await RecoveryTrackerService(self.db).tracker(scan)

            if not tracker_out.timeline:
                return None

            last_log = tracker_out.timeline[-1]

            if last_log.progress == "recovered" or last_log.applied_at is None:
                return None

            from app.services.calendar import TREATMENT_RESUME_DAYS

            applied_at = ensure_aware(last_log.applied_at)

            offset_days = TREATMENT_RESUME_DAYS.get(
                last_log.progress or "no-change",
                5,
            )

            next_due = applied_at + timedelta(days=offset_days)
            now = datetime.now(UTC)

            # Remind within 24 hours of the due time, but do not send
            # reminders for treatments that are more than 7 days overdue.
            if next_due > now + timedelta(hours=24):
                return None

            if next_due < now - timedelta(days=7):
                return None

            payload = {
                "scan_id": scan_id,
                "recovery_log_id": last_log.id,
                "disease_name": scan.disease_name,
                "last_progress": last_log.progress,
                "last_applied_at": applied_at.isoformat(),
                "next_due_at": next_due.isoformat(),
            }

            if await _notification_exists(
                self.db,
                user_id,
                NotificationType.TREATMENT_REMINDER,
                payload,
                since_hours=48,
            ):
                return None

            return await self.notify.create(
                user_id,
                type=NotificationType.TREATMENT_REMINDER,
                title=f"Treatment follow-up for {scan.disease_name}",
                message=(
                    "Next treatment due based on last "
                    f"{last_log.progress} response"
                ),
                payload=payload,
                idempotency_key=(
                    f"treatment-follow-up:{scan_id}:"
                    f"{last_log.id}:{next_due.isoformat()}"
                ),
            )

        except Exception as exc:
            logger.exception(
                "notify_treatment_reminder_failed",
                user_id=user_id,
                scan_id=scan_id,
                error=str(exc),
            )
            return None

    # ── 4. Marketplace message ───────────────────────────────────────────────

    async def notify_marketplace_message(
        self,
        recipient_id: int,
        conversation_id: int,
        sender_id: int,
        sender_name: str,
        *,
        message_id: int | None = None,
        listing_id: int | None = None,
        product_id: int | None = None,
    ) -> Notification | None:
        """Create a marketplace message notification.

        Called after a message is persisted. The recipient is the other
        conversation participant. Notifications are idempotent per message.
        """
        user = await self.db.get(User, recipient_id)

        if not user:
            logger.warning(
                "notify_marketplace_message_recipient_missing",
                recipient_id=recipient_id,
            )
            return None

        payload = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
        }

        if message_id is not None:
            payload["message_id"] = message_id

        if listing_id:
            payload["listing_id"] = listing_id

        if product_id:
            payload["product_id"] = product_id

        if await _notification_exists(
            self.db,
            recipient_id,
            NotificationType.MARKETPLACE_MESSAGE,
            payload,
        ):
            return None

        return await self.notify.create(
            recipient_id,
            type=NotificationType.MARKETPLACE_MESSAGE,
            title=f"New message from {sender_name}",
            message="You have a new marketplace inquiry",
            payload=payload,
            idempotency_key=(
                f"marketplace-message:{recipient_id}:{message_id}"
                if message_id is not None
                else None
            ),
        )

    # ── 5. Review received ────────────────────────────────────────────────

    async def notify_review_received(
        self,
        seller_id: int,
        review_id: int,
        *,
        listing_id: int | None = None,
        product_id: int | None = None,
        rating: int,
        reviewer_name: str,
    ) -> Notification | None:
        """Create a review notification after a review is posted.

        Idempotent per review.
        """
        user = await self.db.get(User, seller_id)

        if not user:
            logger.warning(
                "notify_review_received_seller_missing",
                seller_id=seller_id,
            )
            return None

        payload = {
            "review_id": review_id,
            "rating": rating,
            "reviewer_name": reviewer_name,
        }

        if listing_id:
            payload["listing_id"] = listing_id

        if product_id:
            payload["product_id"] = product_id

        if await _notification_exists(
            self.db,
            seller_id,
            NotificationType.REVIEW_RECEIVED,
            payload,
        ):
            return None

        stars = "★" * rating + "☆" * (5 - rating)

        return await self.notify.create(
            seller_id,
            type=NotificationType.REVIEW_RECEIVED,
            title=f"New {rating}-star review from {reviewer_name}",
            message=f"You received a new review: {stars}",
            payload=payload,
            idempotency_key=f"review-received:{seller_id}:{review_id}",
        )

    # ── 6. Order update (placeholder — no order system yet) ────────────────

    async def notify_order_update(
        self,
        user_id: int,
        *,
        event: Literal[
            "placed",
            "confirmed",
            "shipped",
            "delivered",
            "cancelled",
        ],
        order_id: int,
        details: dict | None = None,
    ) -> Notification | None:
        """Create an order update notification.

        No order system exists in the codebase yet. This is a placeholder
        until order lifecycle functionality is implemented.
        """
        logger.info(
            "notify_order_update_stub",
            user_id=user_id,
            order_event=event,
            order_id=order_id,
            note="order system not implemented — returning None",
        )

        return None

    # ── 7. System notification ─────────────────────────────────────────────

    async def notify_system(
        self,
        user_id: int,
        title: str,
        message: str,
        *,
        payload: dict | None = None,
    ) -> Notification | None:
        """Create a system notification.

        Uses a stable hash for idempotency so identical announcements
        do not create duplicate notifications for the same user.
        """
        user = await self.db.get(User, user_id)

        if not user:
            logger.warning(
                "notify_system_user_missing",
                user_id=user_id,
            )
            return None

        full_payload = payload or {}

        stable_data = json.dumps(
            {
                "title": title.strip(),
                "message": message.strip(),
                "payload": full_payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        digest = hashlib.sha256(stable_data.encode("utf-8")).hexdigest()

        return await self.notify.create(
            user_id,
            type=NotificationType.SYSTEM,
            title=title,
            message=message,
            payload=full_payload,
            idempotency_key=f"system:{user_id}:{digest}",
        )

    # ── Bulk: broadcast system notification to all users ────────────────

    async def broadcast_system(
        self,
        title: str,
        message: str,
        *,
        payload: dict | None = None,
        role_filter: str | None = None,
    ) -> int:
        """Broadcast a system notification to active users.

        Optionally restrict recipients by role. Returns the number of
        notifications created.
        """
        stmt = select(User).where(User.status == "active")

        if role_filter:
            stmt = stmt.where(User.role == role_filter)

        users = await self.db.scalars(stmt)

        count = 0

        for user in users.all():
            notification = await self.notify_system(
                user.id,
                title,
                message,
                payload=payload,
            )

            if notification is not None:
                count += 1

        return count
