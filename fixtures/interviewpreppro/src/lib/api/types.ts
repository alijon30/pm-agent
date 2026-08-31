/**
 * TypeScript types matching backend Pydantic schemas
 */

// ============================================================================
// COMMON TYPES
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface MessageResponse {
  message: string;
}

// ============================================================================
// USER TYPES
// ============================================================================

export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface UserUpdate {
  email?: string;
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  is_admin?: boolean;
  is_verified?: boolean;
}

export interface UserWithPosts extends User {
  posts: Post[];
}

// ============================================================================
// POST TYPES
// ============================================================================

export interface Post {
  id: string;
  title: string;
  content: string;
  is_published: boolean;
  author_id: string;
  created_at: string;
  updated_at: string;
}

export interface PostCreate {
  title: string;
  content: string;
  is_published?: boolean;
}

export interface PostUpdate {
  title?: string;
  content?: string;
  is_published?: boolean;
}

export interface PostWithAuthor extends Post {
  author: User;
}

export interface PostWithComments extends Post {
  comments: Comment[];
}

// ============================================================================
// COMMENT TYPES
// ============================================================================

export interface Comment {
  id: string;
  content: string;
  post_id: string;
  author_id: string;
  created_at: string;
  updated_at: string;
}

export interface CommentCreate {
  content: string;
  post_id: string;
}

export interface CommentUpdate {
  content?: string;
}

export interface CommentWithAuthor extends Comment {
  author: User;
}

// ============================================================================
// INTERVIEW TYPES
// ============================================================================

export type InterviewDifficulty = 'easy' | 'medium' | 'hard';

export interface InterviewQuestion {
  id: string;
  question_order: number;
  question_text: string;
  question_context: string;
  response_text: string;
  strengths: string | null;
  areas_for_improvement: string | null;
  quick_tip: string | null;
  transcript_id: string;
  created_at: string;
  updated_at: string;
}

export interface InterviewQuestionCreate {
  question_order: number;
  question_text: string;
  question_context: string;
  response_text: string;
  strengths?: string;
  areas_for_improvement?: string;
  quick_tip?: string;
}

export interface InterviewQuestionUpdate {
  question_order?: number;
  question_text?: string;
  question_context?: string;
  response_text?: string;
  strengths?: string;
  areas_for_improvement?: string;
  quick_tip?: string;
}

export interface InterviewTranscript {
  id: string;
  score: number;
  duration_minutes: number;
  interview_feedback_id: string;
  created_at: string;
  updated_at: string;
}

export interface InterviewTranscriptCreate {
  score: number;
  duration_minutes: number;
  questions?: InterviewQuestionCreate[];
}

export interface InterviewTranscriptUpdate {
  score?: number;
  duration_minutes?: number;
}

export interface InterviewTranscriptWithQuestions extends InterviewTranscript {
  questions: InterviewQuestion[];
}

export interface InterviewSummary {
  id: string;
  score: number;
  duration_minutes: number;
  performance_highlights: string | null;
  areas_for_improvement: string | null;
  detailed_analysis: string | null;
  question_analysis: string | null;
  interview_feedback_id: string;
  created_at: string;
  updated_at: string;
}

export interface InterviewSummaryCreate {
  score: number;
  duration_minutes: number;
  performance_highlights?: string;
  areas_for_improvement?: string;
  detailed_analysis?: string;
  question_analysis?: string;
}

export interface InterviewSummaryUpdate {
  score?: number;
  duration_minutes?: number;
  performance_highlights?: string;
  areas_for_improvement?: string;
  detailed_analysis?: string;
  question_analysis?: string;
}

export interface InterviewFeedbackMain {
  id: string;
  question_count: number;
  difficulty_level: InterviewDifficulty;
  performance_highlights: string;
  development_areas: string;
  score: number;
  is_review_completed: boolean;
  author_id: string;
  created_at: string;
  updated_at: string;
}

export interface InterviewFeedbackMainCreate {
  question_count: number;
  difficulty_level: InterviewDifficulty;
  performance_highlights: string;
  development_areas: string;
  score: number;
  is_review_completed?: boolean;
  interviewtranscript?: InterviewTranscriptCreate;
  summary?: InterviewSummaryCreate;
}

export interface InterviewFeedbackMainUpdate {
  question_count?: number;
  difficulty_level?: InterviewDifficulty;
  performance_highlights?: string;
  development_areas?: string;
  score?: number;
  is_review_completed?: boolean;
}

export interface InterviewFeedbackMainWithAuthor extends InterviewFeedbackMain {
  author: User;
}

export interface InterviewFeedbackMainWithTranscript extends InterviewFeedbackMain {
  interviewtranscript: InterviewTranscript | null;
}

export interface InterviewFeedbackMainWithSummary extends InterviewFeedbackMain {
  summary: InterviewSummary | null;
}

export interface InterviewFeedbackMainComplete extends InterviewFeedbackMain {
  author: User;
  interviewtranscript: InterviewTranscriptWithQuestions | null;
  summary: InterviewSummary | null;
}

// ============================================================================
// REQUEST/RESPONSE TYPES
// ============================================================================

export interface InterviewFeedbackCreateRequest {
  feedback: InterviewFeedbackMainCreate;
  create_transcript?: boolean;
  create_summary?: boolean;
}

export interface InterviewStatsResponse {
  total_interviews: number;
  average_score: number;
  difficulty_breakdown: Record<string, number>;
  recent_performance_trend: Array<Record<string, unknown>>;
}

export interface InterviewAnalyticsResponse {
  user_id: string;
  total_interviews: number;
  average_score: number;
  improvement_areas: string[];
  strengths: string[];
  recommended_difficulty: InterviewDifficulty;
}

// ============================================================================
// AUTHENTICATION TYPES
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type RegisterRequest = UserCreate;

export interface RegisterResponse {
  user: User;
  message: string;
} 