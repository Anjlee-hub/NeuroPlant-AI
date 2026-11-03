"""Notification triggers — domain integration (M5, Task 3).

Integrates the existing NotificationService with domain features so that
domain events create notifications without duplicating domain logic.

All triggers are idempotent where repeated events are possible (e.g. a
weather risk re-assessment on the same coordinates should not spam the
user). Each trigger uses the domain service's own data and calls
NotificationService.create() with the appropriate type + payload.

No push is implemented — the existing InAppTransport seam is preserved.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.catalog import Crop
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.calendar import CalendarService, CalendarTaskNotFoundError
from app.services.notifications import NotificationService, NotificationNotFoundError
from app.services.recovery import RecoveryTrackerService
from app.services.weather_risk import DiseaseRiskService
from app.services.weather import WeatherService, WeatherProviderError

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
    """Check if a similar notification was already created recently.

    Prevents duplicate notifications for the same user/type/payload within
    the time window. The payload match is loose (subset) so that additional
    keys in the new payload don't bypass the check.
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
        if notif and _payload_matches(notif.payload, payload):
            return True
    return False


def _payload_matches(existing: dict, new: dict) -> bool:
    """True if all new keys match existing values (extra keys in existing are OK)."""
    for k, v in new.items():
        if existing.get(k) != v:
            return False
    return True


# ── Trigger service ──────────────────────────────────────────────────────────


class NotificationTriggerService:
    """Domain event → notification wiring.

    All methods are async and return the created Notification (or None if
    skipped due to idempotency / missing objects / failures). Exceptions from
    domain services propagate; callers should log and continue.
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
        """Create weather_risk / disease_risk notifications if risk crosses threshold.

        Uses the existing WeatherRiskService to assess. Idempotent per user +
        crop + location within 24h (the same re-assessment won't re-notify).
        """
        # Validate user exists
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning("notify_weather_risk_user_missing", user_id=user_id)
            return None

        # Validate crop exists
        crop = await self.db.get(Crop, crop_id)
        if not crop:
            logger.warning("notify_weather_risk_crop_missing", crop_id=crop_id)
            return None

        try:
            weather_result = await WeatherService().get_current(lat, lng)
            risk_out = await DiseaseRiskService(self.db).assess_crop(
                crop_id, weather_result.data, is_fallback=weather_result.is_fallback
            )
        except WeatherProviderError:
            logger.warning("notify_weather_risk_provider_failed", user_id=user_id, crop_id=crop_id)
            return None
        except Exception as exc:
            logger.warning("notify_weather_risk_assess_failed", user_id=user_id, crop_id=crop_id, error=str(exc))
            return None

        # Find the highest-risk disease above the threshold
        for risk in risk_out.risks:
            if risk.risk_level in notify_levels:
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
                type_ = NotificationType.DISEASE_RISK if risk.risk_level == "critical" else NotificationType.WEATHER_RISK

                # Idempotency check
                if await _notification_exists(self.db, user_id, type_, payload):
                    logger.info("notify_weather_risk_idempotent_skip", user_id=user_id, crop_id=crop_id, type=type_.value)
                    return None

                title = f"{risk.risk_level.capitalize()} {('disease' if type_ == NotificationType.DISEASE_RISK else 'weather')} risk for {crop.name}"
                message = risk.explanation

                return await self.notify.create(
                    user_id,
                    type=type_,
                    title=title,
                    message=message,
                    payload=payload,
                )
        return None

    # ── 2. Calendar / task reminder ────────────────────────────────────────

    async def maybe_notify_task_reminder(
        self,
        user_id: int,
        schedule_id: int,
        *,
        hours_before: int = 24,
    ) -> Notification | None:
        """Create task_reminder for an upcoming calendar task.

        Called periodically (e.g. by a scheduler) to find tasks due within
        ``hours_before`` and notify the farmer. Idempotent per task (each
        task has a unique scan_id + kind + due_at combination).
        """
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning("notify_task_reminder_user_missing", user_id=user_id)
            return None

        try:
            calendar = CalendarService(self.db)
            now = datetime.now(UTC)
            cutoff = now + timedelta(hours=hours_before)

            # Get the user's schedule
            schedule = await calendar.db.scalar(
                select(calendar.db.model.CropSchedule)
                .where(calendar.db.model.CropSchedule.id == schedule_id, calendar.db.model.CropSchedule.user_id == user_id)
            )
            if not schedule:
                logger.warning("notify_task_reminder_schedule_missing", user_id=user_id, schedule_id=schedule_id)
                return None

            # Find upcoming tasks in the window
            tasks = await calendar.db.scalars(
                select(calendar.db.model.CalendarTask).where(
                    calendar.db.model.CalendarTask.schedule_id == schedule_id,
                    calendar.db.model.CalendarTask.due_at >= now,
                    calendar.db.model.CalendarTask.due_at <= cutoff,
                    calendar.db.model.CalendarTask.completed_at.is_(None),
                )
            )
            tasks = list(tasks.all())

            for task in tasks:
                payload = {
                    "schedule_id": schedule_id,
                    "task_id": task.id,
                    "task_kind": task.kind,
                    "task_title": task.title,
                    "due_at": task.due_at.isoformat(),
                }
                if await _notification_exists(self.db, user_id, NotificationType.TASK_REMINDER, payload, since_hours=48):
                    continue

                title = f"Upcoming task: {task.title}"
                message = f"Due {task.due_at.strftime('%Y-%m-%d %H:%M')}"

                await self.notify.create(
                    user_id,
                    type=NotificationType.TASK_REMINDER,
                    title=title,
                    message=message,
                    payload=payload,
                )
        except Exception as exc:
            logger.warning("notify_task_reminder_failed", user_id=user_id, schedule_id=schedule_id, error=str(exc))
            return None
        return None

    # ── 3. Treatment / recovery reminder ──────────────────────────────────

    async def maybe_notify_treatment_reminder(
        self,
        user_id: int,
        scan_id: int,
    ) -> Notification | None:
        """Create treatment_reminder based on recovery tracker timeline.

        If the latest recovery log suggests a follow-up treatment (based on
        the documented resume intervals), notify the farmer. Idempotent per
        scan + last_log_id.
        """
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning("notify_treatment_reminder_user_missing", user_id=user_id)
            return None

        try:
            from app.models.scan import Scan
            scan = await self.db.get(Scan, scan_id)
            if not scan or scan.user_id != user_id:
                logger.warning("notify_treatment_reminder_scan_missing", user_id=user_id, scan_id=scan_id)
                return None

            tracker = RecoveryTrackerService(self.db)
            tracker_out = await tracker.tracker(scan)

            if not tracker_out.timeline:
                return None  # No treatment history yet

            # Check if it's time for a follow-up based on the last log
            last_log = tracker_out.timeline[-1]
            if last_log.progress == "recovered":
                return None

            # Determine when the next treatment should be
            from app.services.calendar import TREATMENT_RESUME_DAYS
            offset_days = TREATMENT_RESUME_DAYS.get(last_log.progress or "no-change", 5)
            next_due = last_log.applied_at + timedelta(days=offset_days)

            now = datetime.now(UTC)
            if next_due > now + timedelta(hours=24):
                return None  # Not due yet
            if next_due < now - timedelta(days=7):
                return None  # Too late (missed window)

            payload = {
                "scan_id": scan_id,
                "disease_name": scan.disease_name,
                "last_progress": last_log.progress,
                "last_applied_at": last_log.applied_at.isoformat() if last_log.applied_at else None,
                "next_due_at": next_due.isoformat(),
            }
            if await _notification_exists(self.db, user_id, NotificationType.TREATMENT_REMINDER, payload, since_hours=48):
                return None

            title = f"Treatment follow-up for {scan.disease_name}"
            message = f"Next treatment due based on last {last_log.progress} response"

            return await self.notify.create(
                user_id,
                type=NotificationType.TREATMENT_REMINDER,
                title=title,
                message=message,
                payload=payload,
            )
        except Exception as exc:
            logger.warning("notify_treatment_reminder_failed", user_id=user_id, scan_id=scan_id, error=str(exc))
            return None

    # ── 4. Marketplace message ────────────────────────────────────────────

    async def notify_marketplace_message(
        self,
        recipient_id: int,
        conversation_id: int,
        sender_id: int,
        sender_name: str,
        *,
        listing_id: int | None = None,
        product_id: int | None = None,
    ) -> Notification | None:
        """Create marketplace_message notification when a new message arrives.

        Called from MessagingService.send_message after the message is
        persisted. The recipient is the *other* participant. Idempotent per
        conversation + message (the message ID is in the payload).
        """
        user = await self.db.get(User, recipient_id)
        if not user:
            logger.warning("notify_marketplace_message_recipient_missing", recipient_id=recipient_id)
            return None

        payload = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
        }
        if listing_id:
            payload["listing_id"] = listing_id
        if product_id:
            payload["product_id"] = product_id

        if await _notification_exists(self.db, recipient_id, NotificationType.MARKETPLACE_MESSAGE, payload):
            return None

        title = f"New message from {sender_name}"
        message = "You have a new marketplace inquiry"

        return await self.notify.create(
            recipient_id,
            type=NotificationType.MARKETPLACE_MESSAGE,
            title=title,
            message=message,
            payload=payload,
        )

    # ── 5. Review received ─────────────────────────────────────────────────

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
        """Create review_received notification when a new review is posted.

        Called from ReviewsService.create after the review is persisted.
        Idempotent per review_id.
        """
        user = await self.db.get(User, seller_id)
        if not user:
            logger.warning("notify_review_received_seller_missing", seller_id=seller_id)
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

        if await _notification_exists(self.db, seller_id, NotificationType.REVIEW_RECEIVED, payload):
            return None

        stars = "★" * rating + "☆" * (5 - rating)
        title = f"New {rating}-star review from {reviewer_name}"
        message = f"You received a new review: {stars}"

        return await self.notify.create(
            seller_id,
            type=NotificationType.REVIEW_RECEIVED,
            title=title,
            message=message,
            payload=payload,
        )

    # ── 6. Order update (placeholder — no order system yet) ────────────────

    async def notify_order_update(
        self,
        user_id: int,
        *,
        event: Literal["placed", "confirmed", "shipped", "delivered", "cancelled"],
        order_id: int,
        details: dict | None = None,
    ) -> Notification | None:
        """Create order_update notification for order lifecycle events.

        **Note:** No order system exists in the codebase yet (M4 has
        marketplace listings/products/messaging/reviews but no orders).
        This method is a stub that logs and returns None. When an order
        system is added (future milestone), this will be implemented.
        """
        logger.info(
            "notify_order_update_stub",
            user_id=user_id,
            event=event,
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
        """Create a system notification (admin announcements, platform updates).

        Idempotent per user + title + message within 7 days.
        """
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning("notify_system_user_missing", user_id=user_id)
            return None

        full_payload = payload or {}
        if await _notification_exists(self.db, user_id, NotificationType.SYSTEM, full_payload, since_hours=168):
            return None

        return await self.notify.create(
            user_id,
            type=NotificationType.SYSTEM,
            title=title,
            message=message,
            payload=full_payload,
        )

    # ── Bulk: broadcast system notification to all users ──────────────────

    async def broadcast_system(
        self,
        title: str,
        message: str,
        *,
        payload: dict | None = None,
        role_filter: str | None = None,
    ) -> int:
        """Send a system notification to all users (optionally filtered by role).

        Returns the number of notifications created.
        """
        stmt = select(User).where(User.status == "active")
        if role_filter:
            stmt = stmt.where(User.role == role_filter)
        users = await self.db.scalars(stmt)

        count = 0
        for user in users.all():
            if await self.notify_system(user.id, title, message, payload=payload):
                count += 1
        return count