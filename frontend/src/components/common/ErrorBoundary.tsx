import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props { children: ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };
  static getDerivedStateFromError(error: Error): State { return { hasError: true, error }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("TRANSLATRIX PRO UI boundary captured an error", error, info);
  }
  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6 dark:bg-navy-950">
        <div className="max-w-xl rounded-3xl border border-red-200 bg-white p-8 shadow-enterprise dark:border-red-900 dark:bg-slate-950">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-danger dark:bg-red-950/40"><AlertTriangle className="h-6 w-6" /></div>
          <h1 className="mt-5 text-2xl font-bold">Workspace error</h1>
          <p className="mt-2 text-sm text-slate-500">The UI recovered safely. Refresh the workspace or contact support with the console trace.</p>
          {this.state.error?.message ? <pre className="mt-4 overflow-auto rounded-xl bg-slate-950 p-3 text-xs text-slate-100">{this.state.error.message}</pre> : null}
          <Button className="mt-5" onClick={() => location.reload()}>Reload workspace</Button>
        </div>
      </div>
    );
  }
}
