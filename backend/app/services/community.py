import io

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import case, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import (
    CommunityBookmark,
    CommunityComment,
    CommunityPost,
    CommunityVote,
)
from app.models.user import User
from app.schemas.community import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    PostCreate,
    PostResponse,
    PostUpdate,
)
from app.services.storage import get_storage_service

MAX_COMMUNITY_IMAGE_BYTES = 10 * 1024 * 1024
BOOKMARKS_UNAVAILABLE_MESSAGE = (
    "Community bookmarks are unavailable until the community-bookmarks migration is applied."
)
COMMUNITY_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/gif",
    "image/tiff",
}


class CommunityBookmarksUnavailableError(Exception):
    """The database has not yet been migrated to persist post bookmarks."""


async def _bookmarks_table_exists(db: AsyncSession) -> bool:
    connection = await db.connection()
    return await connection.run_sync(
        lambda sync_connection: inspect(sync_connection).has_table("community_bookmarks")
    )


async def upload_post_image(user_id: int, file: UploadFile) -> str:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in COMMUNITY_IMAGE_CONTENT_TYPES:
        raise ValueError(f"unsupported image type: {content_type or 'unknown'}")

    data = await file.read(MAX_COMMUNITY_IMAGE_BYTES + 1)
    if not data:
        raise ValueError("image file is empty")
    if len(data) > MAX_COMMUNITY_IMAGE_BYTES:
        raise ValueError("image exceeds the 10 MB limit")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = image.format
            image.verify()
    except (
        OSError,
        UnidentifiedImageError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValueError("file is not a valid image") from exc

    if Image.MIME.get(image_format or "") != content_type:
        raise ValueError("image content does not match its declared type")

    storage = get_storage_service()
    key = storage.save(data, content_type, user_id, subdir="community")
    return storage.url(key)


async def create_post(db: AsyncSession, user_id: int, data: PostCreate) -> PostResponse:
    post = CommunityPost(user_id=user_id, **data.model_dump())
    post.farmer = await db.get(User, user_id)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return await _post_response(db, post, user_id)


async def get_posts(
    db: AsyncSession, user_id: int, *, saved_only: bool = False
) -> list[PostResponse]:
    bookmarks_available = await _bookmarks_table_exists(db)
    if saved_only and not bookmarks_available:
        raise CommunityBookmarksUnavailableError(BOOKMARKS_UNAVAILABLE_MESSAGE)

    statement = select(CommunityPost).where(CommunityPost.is_active)
    if saved_only:
        statement = statement.join(
            CommunityBookmark,
            CommunityBookmark.post_id == CommunityPost.id,
        ).where(CommunityBookmark.user_id == user_id)
    posts = (await db.scalars(statement.order_by(CommunityPost.id.desc()))).all()
    if not posts:
        return []

    votes = await db.execute(
        select(
            CommunityVote.post_id,
            func.count(CommunityVote.id),
            func.max(case((CommunityVote.user_id == user_id, 1), else_=0)),
        )
        .where(CommunityVote.post_id.in_([post.id for post in posts]))
        .group_by(CommunityVote.post_id)
    )
    counts = {
        post_id: (like_count, bool(is_liked)) for post_id, like_count, is_liked in votes.all()
    }
    saved_ids: set[int] = set()
    if bookmarks_available:
        saved_ids = set(
            (
                await db.scalars(
                    select(CommunityBookmark.post_id).where(
                        CommunityBookmark.user_id == user_id,
                        CommunityBookmark.post_id.in_([post.id for post in posts]),
                    )
                )
            ).all()
        )
    return [
        PostResponse.model_validate(post).model_copy(
            update={
                "like_count": counts.get(post.id, (0, False))[0],
                "is_liked": counts.get(post.id, (0, False))[1],
                "is_saved": post.id in saved_ids,
            }
        )
        for post in posts
    ]


async def _post_response(db: AsyncSession, post: CommunityPost, user_id: int) -> PostResponse:
    like_count = await db.scalar(
        select(func.count(CommunityVote.id)).where(CommunityVote.post_id == post.id)
    )
    is_liked = await db.scalar(
        select(CommunityVote.id).where(
            CommunityVote.post_id == post.id,
            CommunityVote.user_id == user_id,
        )
    )
    is_saved = False
    if await _bookmarks_table_exists(db):
        is_saved = (await db.scalar(
            select(CommunityBookmark.id).where(
                CommunityBookmark.post_id == post.id,
                CommunityBookmark.user_id == user_id,
            )
        )) is not None
    return PostResponse.model_validate(post).model_copy(
        update={
            "like_count": like_count or 0,
            "is_liked": is_liked is not None,
            "is_saved": is_saved,
        }
    )


async def set_post_saved(
    db: AsyncSession, post_id: int, user_id: int, saved: bool
) -> bool | None:
    if not await _bookmarks_table_exists(db):
        raise CommunityBookmarksUnavailableError(BOOKMARKS_UNAVAILABLE_MESSAGE)

    post = await db.scalar(
        select(CommunityPost).where(
            CommunityPost.id == post_id,
            CommunityPost.is_active,
        )
    )
    if post is None:
        return None

    bookmark = await db.scalar(
        select(CommunityBookmark).where(
            CommunityBookmark.post_id == post_id,
            CommunityBookmark.user_id == user_id,
        )
    )
    if saved and bookmark is None:
        db.add(CommunityBookmark(post_id=post_id, user_id=user_id))
        await db.commit()
    elif not saved and bookmark is not None:
        await db.delete(bookmark)
        await db.commit()
    return saved


async def update_post(
    db: AsyncSession, post_id: int, user_id: int, data: PostUpdate
) -> PostResponse | None:
    post = await db.scalar(
        select(CommunityPost).where(
            CommunityPost.id == post_id,
            CommunityPost.user_id == user_id,
            CommunityPost.is_active,
        )
    )
    if post is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    await db.commit()
    await db.refresh(post)
    return await _post_response(db, post, user_id)


async def delete_post(db: AsyncSession, post_id: int, user_id: int) -> bool:
    post = await db.scalar(
        select(CommunityPost).where(
            CommunityPost.id == post_id,
            CommunityPost.user_id == user_id,
            CommunityPost.is_active,
        )
    )
    if post is None:
        return False

    post.is_active = False
    await db.commit()
    return True


async def add_comment(
    db: AsyncSession, post_id: int, user_id: int, data: CommentCreate
) -> CommentResponse | None:
    post = await db.get(CommunityPost, post_id)

    if not post or not post.is_active:
        return None

    if data.parent_id is not None:
        parent = await db.get(CommunityComment, data.parent_id)

        if not parent or parent.post_id != post_id:
            raise ValueError("Parent comment does not belong to this post")

    comment = CommunityComment(
        post_id=post_id,
        user_id=user_id,
        **data.model_dump(),
    )
    comment.farmer = await db.get(User, user_id)

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentResponse.model_validate(comment)


async def update_comment(
    db: AsyncSession,
    post_id: int,
    comment_id: int,
    user_id: int,
    data: CommentUpdate,
) -> CommentResponse | None:
    comment = await db.scalar(
        select(CommunityComment).where(
            CommunityComment.id == comment_id,
            CommunityComment.post_id == post_id,
            CommunityComment.user_id == user_id,
        )
    )
    if comment is None:
        return None

    comment.content = data.content
    await db.commit()
    await db.refresh(comment)
    return CommentResponse.model_validate(comment)


async def delete_comment(db: AsyncSession, post_id: int, comment_id: int, user_id: int) -> bool:
    comment = await db.scalar(
        select(CommunityComment).where(
            CommunityComment.id == comment_id,
            CommunityComment.post_id == post_id,
            CommunityComment.user_id == user_id,
        )
    )
    if comment is None:
        return False

    await db.delete(comment)
    await db.commit()
    return True


async def get_comments(db: AsyncSession, post_id: int) -> list[CommentResponse]:
    result = await db.execute(
        select(CommunityComment)
        .where(CommunityComment.post_id == post_id)
        .order_by(CommunityComment.id.asc())
    )
    return [CommentResponse.model_validate(comment) for comment in result.scalars().all()]


async def vote_post(db: AsyncSession, post_id: int, user_id: int) -> dict | None:
    post = await db.scalar(
        select(CommunityPost).where(CommunityPost.id == post_id).with_for_update()
    )

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
        message = "Vote removed"
    else:
        db.add(CommunityVote(post_id=post_id, user_id=user_id))
        await db.commit()
        message = "Vote added"

    like_count = await db.scalar(
        select(func.count(CommunityVote.id)).where(CommunityVote.post_id == post_id)
    )
    is_liked = await db.scalar(
        select(CommunityVote.id).where(
            CommunityVote.post_id == post_id,
            CommunityVote.user_id == user_id,
        )
    )
    return {
        "message": message,
        "like_count": like_count or 0,
        "is_liked": is_liked is not None,
    }
