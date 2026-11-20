import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bookmark,
  Leaf,
  MessageCircle,
  Pencil,
  Plus,
  ThumbsUp,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { CommunityPost, CreatePostInput } from "@/types/community";

const CATEGORIES = [
  ["all", "All categories"],
  ["disease", "Plant diseases"],
  ["pest", "Pest problems"],
  ["fertilizer", "Crop advice"],
  ["irrigation", "Farming techniques"],
  ["harvesting", "Harvesting"],
  ["general", "General discussions"],
] as const;

type CommunityTab = "explore" | "mine" | "saved";

function PostComments({ postId }: { postId: number }) {
  const [content, setContent] = useState("");
  const queryClient = useQueryClient();

  const commentsQuery = useQuery({
    queryKey: ["community-comments", postId],
    queryFn: () => api.listPostComments(postId),
  });

  const commentMutation = useMutation({
    mutationFn: () => api.addPostComment(postId, { content }),
    onSuccess: async () => {
      setContent("");
      await queryClient.invalidateQueries({
        queryKey: ["community-comments", postId],
      });
    },
  });

  return (
    <div className="mt-4 border-t pt-4">
      <div className="space-y-3">
        {commentsQuery.data?.map((comment) => (
          <div key={comment.id} className="rounded-lg bg-muted/50 p-3">
            <p className="text-sm">{comment.content}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {comment.farmer.name}
            </p>
          </div>
        ))}
        {commentsQuery.isLoading && (
          <p className="text-sm text-muted-foreground">Loading comments...</p>
        )}
        {commentsQuery.isError && (
          <p className="text-sm text-destructive">Could not load comments.</p>
        )}
        {commentsQuery.data?.length === 0 && (
          <p className="text-sm text-muted-foreground">No comments yet.</p>
        )}
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (content.trim()) commentMutation.mutate();
        }}
      >
        <input
          value={content}
          onChange={(event) => setContent(event.target.value)}
          aria-label="Write a comment"
          placeholder="Write a comment..."
          className="min-w-0 flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!content.trim() || commentMutation.isPending}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Comment
        </button>
      </form>

      {commentMutation.isError && (
        <p className="mt-2 text-sm text-destructive">
          Could not add your comment. Please try again.
        </p>
      )}
    </div>
  );
}

export function CommunityPage() {
  const user = useAuth((state) => state.user);
  const queryClient = useQueryClient();

  const [tab, setTab] = useState<CommunityTab>("explore");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editingPost, setEditingPost] = useState<CommunityPost | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [image, setImage] = useState<File | null>(null);
  const [statusNotice, setStatusNotice] = useState("");
  const imageInputRef = useRef<HTMLInputElement>(null);

  const postsQuery = useQuery({
    queryKey: ["community-posts"],
    queryFn: api.listCommunityPosts,
    enabled: !!user,
  });
  const savedQuery = useQuery({
    queryKey: ["community-saved-posts"],
    queryFn: api.listSavedCommunityPosts,
    enabled: !!user && tab === "saved",
  });

  const resetForm = () => {
    setTitle("");
    setContent("");
    setCategory("general");
    setImage(null);
    setEditingPost(null);
    if (imageInputRef.current) imageInputRef.current.value = "";
  };
  const closeComposer = () => {
    if (publishMutation.isPending) return;
    setCreateOpen(false);
    resetForm();
    publishMutation.reset();
  };

  const publishMutation = useMutation({
    mutationFn: async ({
      postId,
      payload,
    }: {
      postId: number | null;
      payload: CreatePostInput;
    }) => {
      const uploaded = image
        ? await api.uploadCommunityPostImage(image)
        : undefined;
      const postPayload = {
        ...payload,
        image_url: uploaded?.image_url ?? editingPost?.image_url ?? undefined,
      };
      return postId
        ? api.updateCommunityPost(postId, postPayload)
        : api.createCommunityPost(postPayload);
    },
    onSuccess: async () => {
      setCreateOpen(false);
      resetForm();
      setStatusNotice(editingPost ? "Your post was updated." : "Your post was published.");
      await queryClient.invalidateQueries({ queryKey: ["community-posts"] });
      await queryClient.invalidateQueries({ queryKey: ["community-saved-posts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (postId: number) => api.deleteCommunityPost(postId),
    onSuccess: async () => {
      setStatusNotice("Your post was deleted.");
      await queryClient.invalidateQueries({ queryKey: ["community-posts"] });
      await queryClient.invalidateQueries({ queryKey: ["community-saved-posts"] });
    },
  });

  const voteMutation = useMutation({
    mutationFn: (postId: number) => api.voteForPost(postId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["community-posts"] });
      await queryClient.invalidateQueries({ queryKey: ["community-saved-posts"] });
    },
  });

  const saveMutation = useMutation({
    mutationFn: ({ postId, saved }: { postId: number; saved: boolean }) =>
      saved ? api.saveCommunityPost(postId) : api.unsaveCommunityPost(postId),
    onSuccess: async (result) => {
      setStatusNotice(result.saved ? "Post saved." : "Post removed from saved posts.");
      await queryClient.invalidateQueries({ queryKey: ["community-posts"] });
      await queryClient.invalidateQueries({ queryKey: ["community-saved-posts"] });
    },
  });

  const openNewPost = () => {
    resetForm();
    publishMutation.reset();
    setStatusNotice("");
    setCreateOpen(true);
  };
  const openEditPost = (post: CommunityPost) => {
    setEditingPost(post);
    setTitle(post.title);
    setContent(post.content);
    setCategory(post.category);
    setImage(null);
    publishMutation.reset();
    setStatusNotice("");
    setCreateOpen(true);
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <Users className="mx-auto mb-4 h-12 w-12 text-primary" />
        <h1 className="text-2xl font-bold">Farmer Community</h1>
        <p className="mt-2 text-muted-foreground">
          Sign in to connect with farmers, share experiences and discuss crop
          diseases.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-block rounded-lg bg-primary px-6 py-3 text-primary-foreground"
        >
          Sign in
        </Link>
      </div>
    );
  }

  const activeQuery = tab === "saved" ? savedQuery : postsQuery;
  const sourcePosts = tab === "saved" ? savedQuery.data : postsQuery.data;
  const visiblePosts = (sourcePosts ?? [])
    .filter((post) => tab !== "mine" || post.user_id === user.id)
    .filter((post) => categoryFilter === "all" || post.category === categoryFilter);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-4 py-8 pb-24">
        <header className="mb-7">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-primary/10 p-3">
              <Leaf className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Farmer Community</h1>
              <p className="text-sm text-muted-foreground">
                Share knowledge. Discuss problems. Grow together.
              </p>
            </div>
          </div>
        </header>

        {statusNotice && (
          <p
            role="status"
            aria-live="polite"
            className="mb-4 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-primary"
          >
            {statusNotice}
          </p>
        )}

        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div role="tablist" aria-label="Community sections" className="flex gap-1 rounded-xl bg-muted p-1">
            {(
              [
                ["explore", "Community / Explore"],
                ["mine", "My Posts"],
                ["saved", "Saved Posts"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={tab === value}
                onClick={() => setTab(value)}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  tab === value
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="sr-only">Filter posts by category</span>
            <select
              aria-label="Filter posts by category"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
              className="rounded-lg border bg-background px-3 py-2 text-foreground"
            >
              {CATEGORIES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        <section role="tabpanel" aria-label="Community posts">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold">
              {tab === "mine" ? "My Posts" : tab === "saved" ? "Saved Posts" : "Community Discussions"}
            </h2>
            {activeQuery.isSuccess && (
              <span className="text-sm text-muted-foreground">
                {visiblePosts.length} posts
              </span>
            )}
          </div>

          {activeQuery.isLoading && (
            <p role="status" className="py-8 text-center text-muted-foreground">
              Loading community posts...
            </p>
          )}

          {activeQuery.isError && (
            <div className="rounded-xl border p-6 text-center">
              <p className="text-destructive">
                Could not load posts: {errorMessage(activeQuery.error)}
              </p>
              <button
                onClick={() => void activeQuery.refetch()}
                className="mt-3 rounded-lg border px-4 py-2 text-sm"
              >
                Retry
              </button>
            </div>
          )}

          {!activeQuery.isLoading && !activeQuery.isError && visiblePosts.length === 0 && (
            <div className="rounded-xl border border-dashed p-10 text-center">
              <Users className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
              <h3 className="font-semibold">
                {tab === "mine"
                  ? "You have not shared a post yet"
                  : tab === "saved"
                    ? "No saved posts yet"
                    : "No discussions in this category"}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {tab === "mine"
                  ? "Share a farming question or experience with the community."
                  : tab === "saved"
                    ? "Save useful community posts to find them here."
                    : "Be the first farmer to start a discussion!"}
              </p>
            </div>
          )}

          <div className="space-y-4">
            {visiblePosts.map((post) => (
              <article
                key={post.id}
                className="rounded-xl border bg-card p-5 shadow-sm"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium capitalize text-primary">
                    {post.category}
                  </span>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{post.farmer.name}</span>
                    <span aria-hidden="true">·</span>
                    <time dateTime={post.created_at}>
                      {new Date(post.created_at).toLocaleDateString()}
                    </time>
                  </div>
                </div>

                <h3 className="text-lg font-semibold">{post.title}</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                  {post.content}
                </p>
                {post.image_url && (
                  <img
                    src={post.image_url}
                    alt={post.title}
                    className="mt-4 max-h-96 w-full rounded-lg object-cover"
                  />
                )}

                <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3">
                  <button
                    onClick={() => voteMutation.mutate(post.id)}
                    disabled={voteMutation.isPending}
                    aria-label={post.is_liked ? "Unlike post" : "Like post"}
                    aria-pressed={post.is_liked}
                    className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted disabled:opacity-50"
                  >
                    <ThumbsUp className="h-4 w-4" />
                    {post.like_count}
                  </button>
                  <button
                    onClick={() => saveMutation.mutate({ postId: post.id, saved: !post.is_saved })}
                    disabled={saveMutation.isPending}
                    aria-label={post.is_saved ? "Remove saved post" : "Save post"}
                    aria-pressed={post.is_saved}
                    className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted disabled:opacity-50"
                  >
                    <Bookmark className="h-4 w-4" />
                    {post.is_saved ? "Saved" : "Save"}
                  </button>
                  <span className="inline-flex items-center gap-2 px-2 text-sm text-muted-foreground">
                    <MessageCircle className="h-4 w-4" />
                    Comments
                  </span>
                  {tab === "mine" && post.user_id === user.id && (
                    <div className="ml-auto flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEditPost(post)}
                        aria-label={`Edit ${post.title}`}
                        className="rounded-lg border p-2 hover:bg-muted"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm("Delete this post?")) {
                            deleteMutation.mutate(post.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        aria-label={`Delete ${post.title}`}
                        className="rounded-lg border p-2 text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>

                {(voteMutation.isError || saveMutation.isError || deleteMutation.isError) && (
                  <p role="alert" className="mt-2 text-sm text-destructive">
                    {errorMessage(
                      saveMutation.isError
                        ? saveMutation.error
                        : voteMutation.isError
                          ? voteMutation.error
                          : deleteMutation.error,
                    )}
                  </p>
                )}

                <PostComments postId={post.id} />
              </article>
            ))}
          </div>
        </section>
      </div>

      <button
        type="button"
        onClick={openNewPost}
        aria-label="Create a post"
        className="fixed bottom-6 right-6 z-30 inline-flex h-14 items-center gap-2 rounded-full bg-primary px-5 text-primary-foreground shadow-lg transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <Plus className="h-5 w-5" />
        <span className="font-semibold">Create Post</span>
      </button>

      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="community-composer-title"
          onClick={(event) => {
            if (event.target === event.currentTarget) closeComposer();
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") closeComposer();
          }}
        >
          <section className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border bg-card p-5 shadow-xl sm:p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 id="community-composer-title" className="text-xl font-bold">
                  {editingPost ? "Edit post" : "Create a post"}
                </h2>
                <p className="text-sm text-muted-foreground">
                  Share a question, crop update, or farming experience.
                </p>
              </div>
              <button
                type="button"
                onClick={closeComposer}
                disabled={publishMutation.isPending}
                aria-label="Close post composer"
                className="rounded-lg p-2 hover:bg-muted"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                if (title.trim().length < 3 || !content.trim()) return;
                publishMutation.mutate({
                  postId: editingPost?.id ?? null,
                  payload: { title: title.trim(), content: content.trim(), category },
                });
              }}
            >
              <label className="block space-y-1.5 text-sm font-medium">
                <span>Title</span>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  minLength={3}
                  maxLength={200}
                  required
                  className="w-full rounded-lg border bg-background px-4 py-3 font-normal"
                  placeholder="Give your post a title..."
                />
              </label>
              <label className="block space-y-1.5 text-sm font-medium">
                <span>Description</span>
                <textarea
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  rows={5}
                  required
                  className="w-full resize-y rounded-lg border bg-background px-4 py-3 font-normal"
                  placeholder="Share your farming experience or ask a question..."
                />
              </label>
              <label className="block space-y-1.5 text-sm font-medium">
                <span>Category</span>
                <select
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2.5 font-normal"
                >
                  <option value="general">General</option>
                  <option value="disease">Plant diseases</option>
                  <option value="pest">Pest problems</option>
                  <option value="fertilizer">Crop advice</option>
                  <option value="irrigation">Farming techniques</option>
                  <option value="harvesting">Harvesting</option>
                </select>
              </label>
              <label className="block space-y-1.5 text-sm font-medium">
                <span>Image (optional)</span>
                <input
                  ref={imageInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/bmp,image/gif,image/tiff"
                  onChange={(event) => setImage(event.target.files?.[0] ?? null)}
                  className="block w-full text-sm font-normal file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2"
                />
                {editingPost?.image_url && !image && (
                  <span className="block text-xs text-muted-foreground">
                    Current image will be kept.
                  </span>
                )}
              </label>

              {publishMutation.isError && (
                <p role="alert" className="text-sm text-destructive">
                  Failed to save your post. Please try again.
                </p>
              )}

              <div className="flex justify-end gap-2 border-t pt-4">
                <button
                  type="button"
                  onClick={closeComposer}
                  disabled={publishMutation.isPending}
                  className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={title.trim().length < 3 || !content.trim() || publishMutation.isPending}
                  className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
                >
                  {publishMutation.isPending
                    ? "Publishing..."
                    : editingPost
                      ? "Save changes"
                      : "Publish Post"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
