import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { queryClient } from "./queryClient";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { ApiErrorNotifier } from "@/components/common/ApiErrorNotifier";
import { ThemeInitializer } from "@/components/common/ThemeInitializer";
import type { ReactNode } from "react";

interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeInitializer />
      <ApiErrorNotifier />
      <ErrorBoundary>{children}</ErrorBoundary>
      <Toaster richColors closeButton position="top-right" />
    </QueryClientProvider>
  );
}
