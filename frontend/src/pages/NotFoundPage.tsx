import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center dark:bg-navy-950">
      <div className="rounded-3xl border border-slate-200 bg-white p-10 shadow-enterprise dark:border-slate-800 dark:bg-slate-950">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">404</p>
        <h1 className="mt-3 text-3xl font-bold">Page not found</h1>
        <p className="mt-2 max-w-md text-sm text-slate-500">The workspace route does not exist or your role cannot access it.</p>
        <Button asChild className="mt-6"><Link to="/app/dashboard">Return to dashboard</Link></Button>
      </div>
    </div>
  );
}
