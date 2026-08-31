/**
 * Interview Service - Handles all interview-related API calls
 */

import { api } from '../client';
import {
  InterviewFeedbackMain,
  InterviewFeedbackMainCreate,
  InterviewFeedbackMainUpdate,
  InterviewFeedbackMainWithAuthor,
  InterviewFeedbackMainComplete,
  InterviewTranscript,
  InterviewTranscriptCreate,
  InterviewTranscriptUpdate,
  InterviewTranscriptWithQuestions,
  InterviewQuestion,
  InterviewQuestionCreate,
  InterviewQuestionUpdate,
  InterviewSummary,
  InterviewSummaryCreate,
  InterviewSummaryUpdate,
  InterviewFeedbackCreateRequest,
  InterviewStatsResponse,
  InterviewAnalyticsResponse,
  InterviewDifficulty,
  PaginatedResponse,
  MessageResponse,
} from '../types';

export class InterviewService {
  // ============================================================================
  // INTERVIEW FEEDBACK MAIN ENDPOINTS
  // ============================================================================

  /**
   * Create interview feedback (authenticated)
   */
  async createInterviewFeedback(feedbackData: InterviewFeedbackMainCreate): Promise<InterviewFeedbackMain> {
    return api.post<InterviewFeedbackMain>('/interviews', feedbackData);
  }

  /**
   * Create interview feedback with request options (authenticated)
   */
  async createInterviewFeedbackWithOptions(requestData: InterviewFeedbackCreateRequest): Promise<InterviewFeedbackMain> {
    return api.post<InterviewFeedbackMain>('/interviews/create-with-options', requestData);
  }

  /**
   * Get current user's interview feedbacks (authenticated)
   */
  async getMyInterviewFeedbacks(params?: {
    skip?: number;
    limit?: number;
    difficulty?: InterviewDifficulty;
    completed_only?: boolean;
  }): Promise<PaginatedResponse<InterviewFeedbackMain>> {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params?.difficulty) searchParams.set('difficulty', params.difficulty);
    if (params?.completed_only !== undefined) searchParams.set('completed_only', params.completed_only.toString());

    const endpoint = `/interviews/my${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    return api.get<PaginatedResponse<InterviewFeedbackMain>>(endpoint);
  }

  /**
   * Get current user's interview feedback by ID (authenticated)
   */
  async getMyInterviewFeedbackById(feedbackId: string): Promise<InterviewFeedbackMain> {
    return api.get<InterviewFeedbackMain>(`/interviews/my/${feedbackId}`);
  }

  /**
   * Update current user's interview feedback (authenticated)
   */
  async updateMyInterviewFeedback(feedbackId: string, feedbackData: InterviewFeedbackMainUpdate): Promise<InterviewFeedbackMain> {
    return api.patch<InterviewFeedbackMain>(`/interviews/my/${feedbackId}`, feedbackData);
  }

  /**
   * Delete current user's interview feedback (authenticated)
   */
  async deleteMyInterviewFeedback(feedbackId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/interviews/my/${feedbackId}`);
  }

  /**
   * Mark interview feedback as completed (authenticated)
   */
  async markInterviewFeedbackCompleted(feedbackId: string): Promise<InterviewFeedbackMain> {
    return api.patch<InterviewFeedbackMain>(`/interviews/my/${feedbackId}/complete`);
  }

  /**
   * Get current user's interview feedback with full details (authenticated)
   */
  async getMyInterviewFeedbackComplete(feedbackId: string): Promise<InterviewFeedbackMainComplete> {
    return api.get<InterviewFeedbackMainComplete>(`/interviews/my/${feedbackId}/complete`);
  }

  // ============================================================================
  // INTERVIEW TRANSCRIPT ENDPOINTS
  // ============================================================================

  /**
   * Create interview transcript (authenticated)
   */
  async createInterviewTranscript(feedbackId: string, transcriptData: InterviewTranscriptCreate): Promise<InterviewTranscript> {
    return api.post<InterviewTranscript>(`/interviews/${feedbackId}/transcript`, transcriptData);
  }

  /**
   * Get interview transcript (authenticated)
   */
  async getInterviewTranscript(feedbackId: string): Promise<InterviewTranscript> {
    return api.get<InterviewTranscript>(`/interviews/${feedbackId}/transcript`);
  }

  /**
   * Get interview transcript with questions (authenticated)
   */
  async getInterviewTranscriptWithQuestions(feedbackId: string): Promise<InterviewTranscriptWithQuestions> {
    return api.get<InterviewTranscriptWithQuestions>(`/interviews/${feedbackId}/transcript/questions`);
  }

  /**
   * Update interview transcript (authenticated)
   */
  async updateInterviewTranscript(transcriptId: string, transcriptData: InterviewTranscriptUpdate): Promise<InterviewTranscript> {
    return api.patch<InterviewTranscript>(`/interviews/transcript/${transcriptId}`, transcriptData);
  }

  /**
   * Delete interview transcript (authenticated)
   */
  async deleteInterviewTranscript(transcriptId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/interviews/transcript/${transcriptId}`);
  }

  // ============================================================================
  // INTERVIEW QUESTION ENDPOINTS
  // ============================================================================

  /**
   * Create interview question (authenticated)
   */
  async createInterviewQuestion(transcriptId: string, questionData: InterviewQuestionCreate): Promise<InterviewQuestion> {
    return api.post<InterviewQuestion>(`/interviews/transcript/${transcriptId}/questions`, questionData);
  }

  /**
   * Get interview questions (authenticated)
   */
  async getInterviewQuestions(transcriptId: string, params?: {
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<InterviewQuestion>> {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());

    const endpoint = `/interviews/transcript/${transcriptId}/questions${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    return api.get<PaginatedResponse<InterviewQuestion>>(endpoint);
  }

  /**
   * Get interview question by ID (authenticated)
   */
  async getInterviewQuestionById(questionId: string): Promise<InterviewQuestion> {
    return api.get<InterviewQuestion>(`/interviews/question/${questionId}`);
  }

  /**
   * Update interview question (authenticated)
   */
  async updateInterviewQuestion(questionId: string, questionData: InterviewQuestionUpdate): Promise<InterviewQuestion> {
    return api.patch<InterviewQuestion>(`/interviews/question/${questionId}`, questionData);
  }

  /**
   * Delete interview question (authenticated)
   */
  async deleteInterviewQuestion(questionId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/interviews/question/${questionId}`);
  }

  // ============================================================================
  // INTERVIEW SUMMARY ENDPOINTS
  // ============================================================================

  /**
   * Create interview summary (authenticated)
   */
  async createInterviewSummary(feedbackId: string, summaryData: InterviewSummaryCreate): Promise<InterviewSummary> {
    return api.post<InterviewSummary>(`/interviews/${feedbackId}/summary`, summaryData);
  }

  /**
   * Get interview summary (authenticated)
   */
  async getInterviewSummary(feedbackId: string): Promise<InterviewSummary> {
    return api.get<InterviewSummary>(`/interviews/${feedbackId}/summary`);
  }

  /**
   * Update interview summary (authenticated)
   */
  async updateInterviewSummary(summaryId: string, summaryData: InterviewSummaryUpdate): Promise<InterviewSummary> {
    return api.patch<InterviewSummary>(`/interviews/summary/${summaryId}`, summaryData);
  }

  /**
   * Delete interview summary (authenticated)
   */
  async deleteInterviewSummary(summaryId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/interviews/summary/${summaryId}`);
  }

  // ============================================================================
  // ADMIN ENDPOINTS
  // ============================================================================

  /**
   * Get all interview feedbacks (admin only)
   */
  async getAllInterviewFeedbacks(params?: {
    skip?: number;
    limit?: number;
    difficulty?: InterviewDifficulty;
    completed_only?: boolean;
  }): Promise<PaginatedResponse<InterviewFeedbackMainWithAuthor>> {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params?.difficulty) searchParams.set('difficulty', params.difficulty);
    if (params?.completed_only !== undefined) searchParams.set('completed_only', params.completed_only.toString());

    const endpoint = `/interviews/admin${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    return api.get<PaginatedResponse<InterviewFeedbackMainWithAuthor>>(endpoint);
  }

  /**
   * Get interview feedback by ID (admin only)
   */
  async getInterviewFeedbackByIdAdmin(feedbackId: string): Promise<InterviewFeedbackMainWithAuthor> {
    return api.get<InterviewFeedbackMainWithAuthor>(`/interviews/admin/${feedbackId}`);
  }

  /**
   * Update interview feedback (admin only)
   */
  async updateInterviewFeedbackAdmin(feedbackId: string, feedbackData: InterviewFeedbackMainUpdate): Promise<InterviewFeedbackMain> {
    return api.patch<InterviewFeedbackMain>(`/interviews/admin/${feedbackId}`, feedbackData);
  }

  /**
   * Delete interview feedback (admin only)
   */
  async deleteInterviewFeedbackAdmin(feedbackId: string): Promise<MessageResponse> {
    return api.delete<MessageResponse>(`/interviews/admin/${feedbackId}`);
  }

  /**
   * Get interview feedbacks by user (admin only)
   */
  async getInterviewFeedbacksByUserAdmin(userId: string, params?: {
    skip?: number;
    limit?: number;
    difficulty?: InterviewDifficulty;
  }): Promise<PaginatedResponse<InterviewFeedbackMain>> {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params?.difficulty) searchParams.set('difficulty', params.difficulty);

    const endpoint = `/interviews/admin/user/${userId}${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    return api.get<PaginatedResponse<InterviewFeedbackMain>>(endpoint);
  }

  // ============================================================================
  // ANALYTICS ENDPOINTS
  // ============================================================================

  /**
   * Get interview statistics (authenticated)
   */
  async getMyInterviewStats(): Promise<InterviewStatsResponse> {
    return api.get<InterviewStatsResponse>('/interviews/my/stats');
  }

  /**
   * Get interview analytics (authenticated)
   */
  async getMyInterviewAnalytics(): Promise<InterviewAnalyticsResponse> {
    return api.get<InterviewAnalyticsResponse>('/interviews/my/analytics');
  }

  /**
   * Get global interview statistics (admin only)
   */
  async getGlobalInterviewStats(): Promise<{
    total_interviews: number;
    completed_interviews: number;
    average_score: number;
    difficulty_distribution: Record<string, number>;
    monthly_trends: Array<{
      month: string;
      count: number;
      average_score: number;
    }>;
  }> {
    return api.get('/interviews/admin/stats');
  }

  /**
   * Get user interview analytics (admin only)
   */
  async getUserInterviewAnalyticsAdmin(userId: string): Promise<InterviewAnalyticsResponse> {
    return api.get<InterviewAnalyticsResponse>(`/interviews/admin/user/${userId}/analytics`);
  }

  // ============================================================================
  // SEARCH AND FILTER ENDPOINTS
  // ============================================================================

  /**
   * Search interview feedbacks (admin only)
   */
  async searchInterviewFeedbacks(params: {
    query: string;
    skip?: number;
    limit?: number;
    difficulty?: InterviewDifficulty;
  }): Promise<PaginatedResponse<InterviewFeedbackMainWithAuthor>> {
    const searchParams = new URLSearchParams();
    searchParams.set('query', params.query);
    if (params.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params.limit !== undefined) searchParams.set('limit', params.limit.toString());
    if (params.difficulty) searchParams.set('difficulty', params.difficulty);

    return api.get<PaginatedResponse<InterviewFeedbackMainWithAuthor>>(`/interviews/admin/search?${searchParams.toString()}`);
  }

  /**
   * Get interview feedbacks by difficulty (authenticated)
   */
  async getInterviewFeedbacksByDifficulty(difficulty: InterviewDifficulty, params?: {
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<InterviewFeedbackMain>> {
    const searchParams = new URLSearchParams();
    searchParams.set('difficulty', difficulty);
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());

    const endpoint = `/interviews/my/difficulty/${difficulty}${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    return api.get<PaginatedResponse<InterviewFeedbackMain>>(endpoint);
  }

  /**
   * Get interview feedbacks by score range (authenticated)
   */
  async getInterviewFeedbacksByScoreRange(minScore: number, maxScore: number, params?: {
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<InterviewFeedbackMain>> {
    const searchParams = new URLSearchParams();
    searchParams.set('min_score', minScore.toString());
    searchParams.set('max_score', maxScore.toString());
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());

    return api.get<PaginatedResponse<InterviewFeedbackMain>>(`/interviews/my/score-range?${searchParams.toString()}`);
  }

  // ============================================================================
  // BULK OPERATIONS (Admin only)
  // ============================================================================

  /**
   * Bulk delete interview feedbacks (admin only)
   */
  async bulkDeleteInterviewFeedbacks(feedbackIds: string[]): Promise<MessageResponse> {
    return api.post<MessageResponse>('/interviews/admin/bulk/delete', { feedback_ids: feedbackIds });
  }

  /**
   * Bulk mark as completed (admin only)
   */
  async bulkMarkCompleted(feedbackIds: string[]): Promise<MessageResponse> {
    return api.post<MessageResponse>('/interviews/admin/bulk/complete', { feedback_ids: feedbackIds });
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Get recommended difficulty for user (authenticated)
   */
  async getRecommendedDifficulty(): Promise<{ recommended_difficulty: InterviewDifficulty }> {
    return api.get('/interviews/my/recommended-difficulty');
  }

  /**
   * Get recent interview feedbacks (authenticated)
   */
  async getRecentInterviewFeedbacks(limit: number = 5): Promise<InterviewFeedbackMain[]> {
    return api.get<InterviewFeedbackMain[]>(`/interviews/my/recent?limit=${limit}`);
  }

  /**
   * Get interview progress (authenticated)
   */
  async getInterviewProgress(): Promise<{
    total_interviews: number;
    completed_interviews: number;
    completion_rate: number;
    average_score: number;
    improvement_trend: number;
  }> {
    return api.get('/interviews/my/progress');
  }

  /**
   * Export interview data (authenticated)
   */
  async exportInterviewData(format: 'json' | 'csv' = 'json'): Promise<Blob> {
    const response = await api.get(`/interviews/my/export?format=${format}`);
    return new Blob([JSON.stringify(response)], { 
      type: format === 'json' ? 'application/json' : 'text/csv' 
    });
  }

  /**
   * Check if user can edit interview feedback
   */
  async canEditInterviewFeedback(feedbackId: string): Promise<{ can_edit: boolean }> {
    try {
      await api.get(`/interviews/my/${feedbackId}`);
      return { can_edit: true };
    } catch {
      return { can_edit: false };
    }
  }
}

// Export singleton instance
export const interviewService = new InterviewService();

// Export individual methods for convenience
export const {
  createInterviewFeedback,
  createInterviewFeedbackWithOptions,
  getMyInterviewFeedbacks,
  getMyInterviewFeedbackById,
  updateMyInterviewFeedback,
  deleteMyInterviewFeedback,
  markInterviewFeedbackCompleted,
  getMyInterviewFeedbackComplete,
  createInterviewTranscript,
  getInterviewTranscript,
  getInterviewTranscriptWithQuestions,
  updateInterviewTranscript,
  deleteInterviewTranscript,
  createInterviewQuestion,
  getInterviewQuestions,
  getInterviewQuestionById,
  updateInterviewQuestion,
  deleteInterviewQuestion,
  createInterviewSummary,
  getInterviewSummary,
  updateInterviewSummary,
  deleteInterviewSummary,
  getAllInterviewFeedbacks,
  getInterviewFeedbackByIdAdmin,
  updateInterviewFeedbackAdmin,
  deleteInterviewFeedbackAdmin,
  getInterviewFeedbacksByUserAdmin,
  getMyInterviewStats,
  getMyInterviewAnalytics,
  getGlobalInterviewStats,
  getUserInterviewAnalyticsAdmin,
  searchInterviewFeedbacks,
  getInterviewFeedbacksByDifficulty,
  getInterviewFeedbacksByScoreRange,
  bulkDeleteInterviewFeedbacks,
  bulkMarkCompleted,
  getRecommendedDifficulty,
  getRecentInterviewFeedbacks,
  getInterviewProgress,
  exportInterviewData,
  canEditInterviewFeedback,
} = interviewService; 