import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, CheckCircle2, CircleAlert, Info, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { notificationApi, type AppNotification } from "@/services/notificationApi";

const icons: Record<AppNotification["type"], typeof Info> = {
  info: Info,
  success: CheckCircle2,
  warning: CircleAlert,
  error: XCircle,
};

export function NotificationMenu() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["notifications"], queryFn: notificationApi.list, staleTime: 30_000 });
  const markRead = useMutation({
    mutationFn: notificationApi.markRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const markAll = useMutation({
    mutationFn: notificationApi.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const notifications = query.data ?? [];
  const unread = notifications.filter((item) => !item.isRead).length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="relative h-9 w-9" aria-label="Open notifications">
          <Bell className="h-4 w-4" />
          {unread > 0 && <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-danger ring-2 ring-white dark:ring-navy-950" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between px-3 py-2">
          <p className="font-semibold">Notifications</p>
          <div className="flex items-center gap-2">
            {unread > 0 && <Badge variant="brand">{unread}</Badge>}
            {unread > 0 && (
              <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => markAll.mutate()} disabled={markAll.isPending}>
                <CheckCheck className="mr-1 h-3.5 w-3.5" /> Mark all
              </Button>
            )}
          </div>
        </div>
        {query.isLoading && <div className="px-3 py-5 text-sm text-slate-500">Loading notifications…</div>}
        {query.isError && <div className="px-3 py-5 text-sm text-danger">Notifications could not be loaded.</div>}
        {!query.isLoading && !query.isError && notifications.length === 0 && <div className="px-3 py-5 text-sm text-slate-500">No notifications.</div>}
        {notifications.map((item) => {
          const Icon = icons[item.type];
          return (
            <DropdownMenuItem key={item.id} className="items-start gap-3 py-3" onSelect={() => !item.isRead && markRead.mutate(item.id)}>
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span className={item.isRead ? "opacity-70" : ""}>
                <span className="block text-sm font-medium">{item.title}</span>
                <span className="block text-xs text-slate-500">{item.message}</span>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
