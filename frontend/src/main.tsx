import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "@/app/router";
import { AppProviders } from "@/app/providers";
import { LoadingState } from "@/components/common/LoadingState";
import { environment } from "@/config/environment";
import "@/styles/globals.css";
import "@/lib/pdfWorker";

const MaintenancePage = lazy(() => import("@/pages/MaintenancePage").then((module) => ({ default: module.MaintenancePage })));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      {environment.maintenanceMode ? (
        <Suspense fallback={<div className="min-h-screen p-6"><LoadingState label="Loading maintenance status" /></div>}>
          <MaintenancePage />
        </Suspense>
      ) : <RouterProvider router={router} />}
    </AppProviders>
  </React.StrictMode>,
);
