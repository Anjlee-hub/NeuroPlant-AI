"""M3.1 tests — conversation memory service.

Covers the rolling per-user transcript: append stores both turns (with
assistant intent/lang metadata), ``list`` returns oldest-first history,
``clear`` empties it, and ``_trim`` caps the stored transcript at
``MAX_MESSAGES`` so a chat that runs forever stays bounded.
"""

from app.models.user import User
from app.services.conversation import CONTEXT_WINDOW, MAX_MESSAGES, ConversationService
from sqlalchemy import select


async def _register(client, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": "Tester", "role": "farmer", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _user_id(db, phone: str) -> int:
    user = await db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user.id


async def test_append_stores_turns_with_metadata(db, client):
    await _register(client, "+919310000031")
    user_id = await _user_id(db, "+919310000031")
    svc = ConversationService(db)

    await svc.append(user_id, "user", "My tomato has early blight")
    await svc.append(user_id, "assistant", "Got it — Early Blight.", intent="report", lang="en")
    await db.commit()

    rows = await svc.list(user_id)
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[0].content == "My tomato has early blight"
    assert rows[1].intent == "report"
    assert rows[1].lang == "en"


async def test_list_is_oldest_first_and_windowed(db, client):
    await _register(client, "+919310000032")
    user_id = await _user_id(db, "+919310000032")
    svc = ConversationService(db)

    for i in range(CONTEXT_WINDOW + 5):
        await svc.append(user_id, "user", f"q{i}")
        await svc.append(user_id, "assistant", f"a{i}")
    await db.commit()

    rows = await svc.list(user_id)
    assert len(rows) == CONTEXT_WINDOW
    assert rows[0].content == "q15"
    assert rows[-1].content == f"a{CONTEXT_WINDOW + 4}"


async def test_clear_empties_transcript(db, client):
    await _register(client, "+919310000033")
    user_id = await _user_id(db, "+919310000033")
    svc = ConversationService(db)

    await svc.append(user_id, "user", "hello")
    await svc.append(user_id, "assistant", "hi there")
    await svc.clear(user_id)
    await db.commit()

    assert await svc.list(user_id) == []


async def test_trim_caps_transcript_at_max_messages(db, client):
    await _register(client, "+919310000034")
    user_id = await _user_id(db, "+919310000034")
    svc = ConversationService(db)

    for i in range(70):  # 140 turns — well past MAX_MESSAGES (60)
        await svc.append(user_id, "user", f"q{i}")
        await svc.append(user_id, "assistant", f"a{i}")
    await db.commit()

    rows = await svc.list(user_id, limit=MAX_MESSAGES + 10)
    assert len(rows) == MAX_MESSAGES
    # Only the newest turns survive; the oldest pair was q40/a40.
    assert rows[0].content == "q40"
    assert rows[-1].content == "a69"
