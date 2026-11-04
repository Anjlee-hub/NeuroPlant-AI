from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import (
    CommunityComment,
    CommunityPost,
    CommunityVote,
)


async def create_post(db: AsyncSession, user_id: int, data):
    post = CommunityPost(user_id=user_id, **data.model_dump())
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def get_posts(db: AsyncSession):
    result = await db.execute(
        select(CommunityPost).where(CommunityPost.is_active).order_by(CommunityPost.id.desc())
    )
    return result.scalars().all()


async def add_comment(db: AsyncSession, post_id: int, user_id: int, data):
    post = await db.get(CommunityPost, post_id)
    if not post or not post.is_active:
        return None

    comment = CommunityComment(
        post_id=post_id,
        user_id=user_id,
        **data.model_dump(),
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_comments(db: AsyncSession, post_id: int):
    result = await db.execute(
        select(CommunityComment)
        .where(CommunityComment.post_id == post_id)
        .order_by(CommunityComment.id.asc())
    )
    return result.scalars().all()


async def vote_post(db: AsyncSession, post_id: int, user_id: int):
    post = await db.get(CommunityPost, post_id)
    if not post or not post.is_active:
        return None

    result = await db.execute(
        select(CommunityVote).where(
            CommunityVote.post_id == post_id,
            CommunityVote.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return "Vote removed"

    db.add(CommunityVote(post_id=post_id, user_id=user_id))
    await db.commit()
    return "Vote added"
