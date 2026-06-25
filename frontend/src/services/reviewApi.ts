import type {
  ApprovalHistoryEvent,
  ReviewActor,
  ReviewBulkActionInput,
  ReviewBulkActionResult,
  ReviewTask,
  SaveReviewInput,
} from "@/types";
import { apiRequest } from "./apiClient";

export const reviewApi = {
  getTasks: () => apiRequest<ReviewTask[]>("/review/tasks"),
  getTask: (id: string) => apiRequest<ReviewTask>(`/review/tasks/${id}`),
  getApprovalHistory: (taskId?: string) => apiRequest<ApprovalHistoryEvent[]>(taskId ? `/review/history?taskId=${encodeURIComponent(taskId)}` : "/review/history"),
  startReview: (id: string, actor: ReviewActor) => apiRequest<ReviewTask>(`/review/tasks/${id}/start`, { method: "POST", body: JSON.stringify({ actor }) }),
  saveReview: (id: string, input: SaveReviewInput, actor: ReviewActor) => apiRequest<ReviewTask>(`/review/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ ...input, actor }) }),
  bulkAction: (input: ReviewBulkActionInput) => apiRequest<ReviewBulkActionResult>("/review/tasks/bulk", { method: "POST", body: JSON.stringify(input) }),
  approve: (id: string, actor: ReviewActor, comments?: string) => apiRequest<ReviewBulkActionResult>(`/review/tasks/${id}/approve`, { method: "POST", body: JSON.stringify({ actor, comments }) }),
  reject: (id: string, actor: ReviewActor, comments: string) => apiRequest<ReviewBulkActionResult>(`/review/tasks/${id}/reject`, { method: "POST", body: JSON.stringify({ actor, comments }) }),
  markReviewed: (id: string, actor: ReviewActor, comments?: string) => apiRequest<ReviewBulkActionResult>(`/review/tasks/${id}/mark-reviewed`, { method: "POST", body: JSON.stringify({ actor, comments }) }),
  requestChanges: (id: string, actor: ReviewActor, comments: string) => apiRequest<ReviewBulkActionResult>(`/review/tasks/${id}/request-changes`, { method: "POST", body: JSON.stringify({ actor, comments }) }),
  sendForSecondApproval: (id: string, actor: ReviewActor, comments?: string) => apiRequest<ReviewTask>(`/review/tasks/${id}/second-approval`, { method: "POST", body: JSON.stringify({ actor, comments }) }),
};
