from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1)
    image_url: str | None = Field(default=None, max_length=500)
    category: str = Field(default="general", max_length=80)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    image_url: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=80)


class CommunityFarmer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    avatar_url: str | None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    content: str
    image_url: str | None
    category: str
    is_active: bool
    farmer: CommunityFarmer
    like_count: int = 0
    is_liked: bool = False


class CommentCreate(BaseModel):
    content: str = Field(min_length=1)
    parent_id: int | None = None


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    content: str
    parent_id: int | None
    farmer: CommunityFarmer


class VoteResponse(BaseModel):
    message: str
    like_count: int
    is_liked: bool
