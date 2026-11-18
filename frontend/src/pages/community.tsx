import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, ThumbsUp, Users, Leaf } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";

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
              Farmer #{comment.user_id}
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

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");

  const postsQuery = useQuery({
    queryKey: ["community-posts"],
    queryFn: api.listCommunityPosts,
    enabled: !!user,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createCommunityPost({
        title: title.trim(),
        content: content.trim(),
        category,
      }),
    onSuccess: async () => {
      setTitle("");
      setContent("");
      setCategory("general");
      await queryClient.invalidateQueries({
        queryKey: ["community-posts"],
      });
    },
  });

  const voteMutation = useMutation({
    mutationFn: (postId: number) => api.voteForPost(postId),
  });

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

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-8">
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
        </div>

        <section className="mb-8 rounded-xl border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold">Create a post</h2>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (title.trim().length >= 3 && content.trim()) {
                createMutation.mutate();
              }
            }}
          >
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Give your post a title..."
              minLength={3}
              maxLength={200}
              required
              className="w-full rounded-lg border bg-background px-4 py-3"
            />

            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder="Share your farming experience or ask a question..."
              rows={4}
              required
              className="w-full resize-y rounded-lg border bg-background px-4 py-3"
            />

            <div className="flex flex-wrap items-center justify-between gap-3">
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="rounded-lg border bg-background px-3 py-2"
              >
                <option value="general">General</option>
                <option value="disease">Crop Disease</option>
                <option value="pest">Pest Management</option>
                <option value="fertilizer">Fertilizers</option>
                <option value="irrigation">Irrigation</option>
                <option value="harvesting">Harvesting</option>
              </select>

              <button
                type="submit"
                disabled={
                  title.trim().length < 3 ||
                  !content.trim() ||
                  createMutation.isPending
                }
                className="rounded-lg bg-primary px-6 py-2.5 font-medium text-primary-foreground disabled:opacity-50"
              >
                {createMutation.isPending ? "Publishing..." : "Publish Post"}
              </button>
            </div>
          </form>

          {createMutation.isError && (
            <p className="mt-3 text-sm text-destructive">
              Failed to publish your post. Please try again.
            </p>
          )}
          {createMutation.isSuccess && (
            <p className="mt-3 text-sm text-green-600">
              Your post was published successfully!
            </p>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold">Community Discussions</h2>
            <span className="text-sm text-muted-foreground">
              {postsQuery.data?.length ?? 0} posts
            </span>
          </div>

          {postsQuery.isLoading && (
            <p className="py-8 text-center text-muted-foreground">
              Loading community posts...
            </p>
          )}

          {postsQuery.isError && (
            <div className="rounded-xl border p-6 text-center">
              <p className="text-destructive">
                Could not load posts. Please refresh and try again.
              </p>
              <button
                onClick={() => void postsQuery.refetch()}
                className="mt-3 rounded-lg border px-4 py-2 text-sm"
              >
                Retry
              </button>
            </div>
          )}

          {postsQuery.data?.length === 0 && (
            <div className="rounded-xl border border-dashed p-10 text-center">
              <Users className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
              <h3 className="font-semibold">No discussions yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Be the first farmer to start a discussion!
              </p>
            </div>
          )}

          <div className="space-y-4">
            {postsQuery.data?.map((post) => (
              <article
                key={post.id}
                className="rounded-xl border bg-card p-5 shadow-sm"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium capitalize text-primary">
                    {post.category}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Farmer #{post.user_id}
                  </span>
                </div>

                <h3 className="text-lg font-semibold">{post.title}</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                  {post.content}
                </p>

                <div className="mt-4 flex items-center gap-4">
                  <button
                    onClick={() => voteMutation.mutate(post.id)}
                    disabled={voteMutation.isPending}
                    className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted disabled:opacity-50"
                  >
                    <ThumbsUp className="h-4 w-4" />
                    Vote
                  </button>
                  <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                    <MessageCircle className="h-4 w-4" />
                    Comments
                  </span>
                </div>

                {voteMutation.isError && (
                  <p className="mt-2 text-sm text-destructive">
                    Could not submit vote. Please try again.
                  </p>
                )}

                <PostComments postId={post.id} />
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
