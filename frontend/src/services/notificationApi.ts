import { apiRequest } from "./apiClient";

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  isRead: boolean;
  createdAt: string;
  href?: string;
}

export const notificationApi = {
  list: () => apiRequest<AppNotification[]>("/notifications"),
  markRead: (id: string) => apiRequest<AppNotification>(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => apiRequest<{ status: string }>("/notifications/mark-all-read", { method: "POST" }),
};
