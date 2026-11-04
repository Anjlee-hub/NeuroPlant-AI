export interface CommunityPost {
  id: number;
  user_id: number;
  title: string;
  content: string;
  image_url: string | null;
  category: string;
  is_active: boolean;
}

export interface CreatePostInput {
  title: string;
  content: string;
  image_url?: string | null;
  category?: string;
}

export interface CommunityComment {
  id: number;
  post_id: number;
  user_id: number;
  content: string;
  parent_id: number | null;
}

export interface CreateCommentInput {
  content: string;
  parent_id?: number | null;
}

export interface Expert {
  user_id: number;
  name: string;
  email: string;
  avatar_url: string | null;
  specialization: string;
  experience_years: number;
  certifications: unknown;
  bio: string | null;
  verified: boolean;
  rating: number;
}

export interface Consultation {
  id: number;
  farmer_id: number;
  expert_id: number;
  subject: string;
  description: string;
  status: string;
  scheduled_at: string | null;
  expert_response: string | null;
}

export interface CreateConsultationInput {
  expert_id: number;
  subject: string;
  description: string;
  scheduled_at?: string | null;
}
