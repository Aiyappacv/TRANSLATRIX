import { Moon, Sun } from "lucide-react";
import { Outlet } from "react-router-dom";
import { ShieldCheck, Sparkles, Workflow } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/store/uiStore";
import { APP_NAME } from "@/utils/constants";

export function AuthLayout() {
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  const toggleTheme = () => {
    setTheme(isDark ? "light" : "dark");
  };

  return (
    <main className="min-h-screen bg-mesh-finance dark:bg-navy-950">
      <div className="relative grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          className="absolute right-4 top-4 z-10 h-9 w-9 rounded-full text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <section className="hidden bg-navy-950 p-10 text-white lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-2 text-sm font-semibold backdrop-blur">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /> Enterprise finance automation
            </div>
            <div className="mt-24 max-w-xl">
              <h1 className="text-5xl font-extrabold tracking-tight">{APP_NAME}</h1>
              <p className="mt-5 text-lg leading-8 text-slate-300">Secure onboarding, shared-link ingestion, PaddleOCR evidence, AI translation, financial classification, human approval, and SAP S/4HANA posting in one controlled cockpit.</p>
            </div>
          </div>
          <div className="grid gap-4">
            {[{ icon: ShieldCheck, title: "Audit-ready controls", body: "Every change, validation, approval, and posting result is visible." }, { icon: Sparkles, title: "Explainable AI", body: "OCR, translation, classification, and mapping confidence are surfaced." }, { icon: Workflow, title: "SAP-first integration", body: "Designed for S/4HANA with extensible accounting connector contracts." }].map((item) => (
              <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <item.icon className="h-5 w-5 text-indigo-300" />
                <h3 className="mt-3 font-semibold">{item.title}</h3>
                <p className="mt-1 text-sm text-slate-400">{item.body}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="flex items-center justify-center p-6 dark:bg-navy-950">
          <div className="w-full max-w-md [&:has(.auth-wide)]:max-w-4xl"><Outlet /></div>
        </section>
      </div>
    </main>
  );
}