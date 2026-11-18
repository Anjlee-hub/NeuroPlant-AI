from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.community import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    PostCreate,
    PostResponse,
    PostUpdate,
    VoteResponse,
)
from app.services import community

router = APIRouter(prefix="/community", tags=["Community"])


@router.post("/posts", response_model=PostResponse)
async def create_community_post(
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await community.create_post(db, user.id, data)


@router.post("/posts/image")
async def upload_community_post_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    try:
        image_url = await community.upload_post_image(user.id, file)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"image_url": image_url}


@router.get("/posts", response_model=list[PostResponse])
async def list_community_posts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await community.get_posts(db, user.id)


@router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_community_post(
    post_id: int,
    data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = await community.update_post(db, post_id, user.id, data)
    if post is None:
        raise HTTPException(404, "Post not found")
    return post


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_community_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deleted = await community.delete_post(db, post_id, user.id)
    if not deleted:
        raise HTTPException(404, "Post not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
)
async def comment_on_post(
    post_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        comment = await community.add_comment(db, post_id, user.id, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not comment:
        raise HTTPException(404, "Post not found")

    return comment


@router.get(
    "/posts/{post_id}/comments",
    response_model=list[CommentResponse],
)
async def list_post_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await community.get_comments(db, post_id)


@router.patch(
    "/posts/{post_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_post_comment(
    post_id: int,
    comment_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = await community.update_comment(db, post_id, comment_id, user.id, data)
    if comment is None:
        raise HTTPException(404, "Comment not found")
    return comment


@router.delete(
    "/posts/{post_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_post_comment(
    post_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deleted = await community.delete_comment(db, post_id, comment_id, user.id)
    if not deleted:
        raise HTTPException(404, "Comment not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/posts/{post_id}/vote", response_model=VoteResponse)
async def vote_for_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await community.vote_post(db, post_id, user.id)

    if result is None:
        raise HTTPException(404, "Post not found")

    return result
