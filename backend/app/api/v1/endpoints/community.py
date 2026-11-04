from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.community import CommentCreate, CommentResponse, PostCreate, PostResponse
from app.services import community

router = APIRouter(prefix="/community", tags=["Community"])


@router.post("/posts", response_model=PostResponse)
async def create_community_post(
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await community.create_post(db, user.id, data)


@router.get("/posts", response_model=list[PostResponse])
async def list_community_posts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await community.get_posts(db)


@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def comment_on_post(
    post_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = await community.add_comment(db, post_id, user.id, data)
    if not comment:
        raise HTTPException(404, "Post not found")
    return comment


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def list_post_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await community.get_comments(db, post_id)


@router.post("/posts/{post_id}/vote")
async def vote_for_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await community.vote_post(db, post_id, user.id)
    if result is None:
        raise HTTPException(404, "Post not found")
    return {"message": result}
