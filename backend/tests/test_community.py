from io import BytesIO

from app.models.user import User
from PIL import Image
from sqlalchemy import select


async def _register(client, phone: str, name: str = "Tester") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"phone": phone, "name": name, "role": "farmer", "password": "secret123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _image_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), color="green")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


async def _create_post(client, headers, **values):
    payload = {
        "title": "Farm question",
        "content": "How can I improve my soil?",
        **values,
    }
    response = await client.post("/api/v1/community/posts", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_community_post_and_comment_include_farmer_profile(client, db):
    headers = await _register(client, "919000000101", name="Asha Farmer")
    farmer = await db.scalar(select(User).where(User.phone == "919000000101"))
    assert farmer is not None
    farmer.avatar_url = "/media/asha.png"
    await db.commit()

    post = await _create_post(client, headers)

    assert post["farmer"] == {"name": "Asha Farmer", "avatar_url": "/media/asha.png"}
    assert post["like_count"] == 0
    assert post["is_liked"] is False

    comment_response = await client.post(
        f"/api/v1/community/posts/{post['id']}/comments",
        json={"content": "Try compost."},
        headers=headers,
    )
    assert comment_response.status_code == 200, comment_response.text
    assert comment_response.json()["farmer"]["name"] == "Asha Farmer"

    reply_response = await client.post(
        f"/api/v1/community/posts/{post['id']}/comments",
        json={"content": "Thank you!", "parent_id": comment_response.json()["id"]},
        headers=headers,
    )
    assert reply_response.status_code == 200, reply_response.text
    assert reply_response.json()["parent_id"] == comment_response.json()["id"]

    comments = await client.get(f"/api/v1/community/posts/{post['id']}/comments", headers=headers)
    assert comments.status_code == 200
    assert comments.json()[0]["farmer"]["name"] == "Asha Farmer"


async def test_community_image_upload_and_post_persistence(client):
    headers = await _register(client, "919000000102")
    response = await client.post(
        "/api/v1/community/posts/image",
        files={"file": ("crop.png", _image_bytes(), "image/png")},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    image_url = response.json()["image_url"]
    assert image_url.startswith("/media/")

    post = await _create_post(client, headers, image_url=image_url)
    assert post["image_url"] == image_url

    fetched = await client.get(image_url)
    assert fetched.status_code == 200
    assert fetched.content == _image_bytes()


async def test_community_image_upload_rejects_bad_type_and_oversize(client):
    headers = await _register(client, "919000000103")
    invalid_type = await client.post(
        "/api/v1/community/posts/image",
        files={"file": ("text.png", b"not an image", "text/plain")},
        headers=headers,
    )
    assert invalid_type.status_code == 422
    invalid_image = await client.post(
        "/api/v1/community/posts/image",
        files={"file": ("fake.png", b"not an image", "image/png")},
        headers=headers,
    )
    assert invalid_image.status_code == 422

    oversized = await client.post(
        "/api/v1/community/posts/image",
        files={"file": ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
        headers=headers,
    )
    assert oversized.status_code == 422


async def test_community_post_and_comment_owner_only_mutations(client):
    owner = await _register(client, "919000000104")
    other = await _register(client, "919000000105")
    post = await _create_post(client, owner)
    comment = await client.post(
        f"/api/v1/community/posts/{post['id']}/comments",
        json={"content": "Original comment"},
        headers=owner,
    )
    assert comment.status_code == 200, comment.text
    comment_id = comment.json()["id"]

    post_url = f"/api/v1/community/posts/{post['id']}"
    comment_url = f"{post_url}/comments/{comment_id}"
    unauthorized_post_edit = await client.patch(post_url, json={"title": "Hijacked"}, headers=other)
    assert unauthorized_post_edit.status_code == 404
    assert (await client.delete(post_url, headers=other)).status_code == 404
    assert (
        await client.patch(comment_url, json={"content": "Hijacked"}, headers=other)
    ).status_code == 404
    assert (await client.delete(comment_url, headers=other)).status_code == 404

    updated_post = await client.patch(post_url, json={"title": "Updated title"}, headers=owner)
    assert updated_post.status_code == 200
    assert updated_post.json()["title"] == "Updated title"
    assert updated_post.json()["content"] == post["content"]

    updated_comment = await client.patch(
        comment_url, json={"content": "Updated comment"}, headers=owner
    )
    assert updated_comment.status_code == 200
    assert updated_comment.json()["content"] == "Updated comment"
    preserved_comment = await client.post(
        f"/api/v1/community/posts/{post['id']}/comments",
        json={"content": "Keep with the post"},
        headers=owner,
    )
    assert preserved_comment.status_code == 200
    assert (await client.delete(comment_url, headers=owner)).status_code == 204
    assert (await client.delete(post_url, headers=owner)).status_code == 204

    feed = await client.get("/api/v1/community/posts", headers=owner)
    assert feed.status_code == 200
    assert all(item["id"] != post["id"] for item in feed.json())
    comments = await client.get(
        f"/api/v1/community/posts/{post['id']}/comments", headers=owner
    )
    assert [item["content"] for item in comments.json()] == ["Keep with the post"]


async def test_community_like_toggle_returns_counts_and_user_state(client):
    owner = await _register(client, "919000000106")
    liker = await _register(client, "919000000107")
    post = await _create_post(client, owner)
    vote_url = f"/api/v1/community/posts/{post['id']}/vote"

    liked = await client.post(vote_url, headers=liker)
    assert liked.status_code == 200
    assert liked.json()["like_count"] == 1
    assert liked.json()["is_liked"] is True

    feed = await client.get("/api/v1/community/posts", headers=liker)
    assert feed.json()[0]["like_count"] == 1
    assert feed.json()[0]["is_liked"] is True
    owner_feed = await client.get("/api/v1/community/posts", headers=owner)
    assert owner_feed.json()[0]["is_liked"] is False

    unliked = await client.post(vote_url, headers=liker)
    assert unliked.status_code == 200
    assert unliked.json()["like_count"] == 0
    assert unliked.json()["is_liked"] is False
