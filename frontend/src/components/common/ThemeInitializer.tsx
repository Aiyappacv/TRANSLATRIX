import { useEffect } from "react";

function getPersistedTheme(): "light" | "dark" | "system" {
  try {
    const raw = localStorage.getItem("translatrix-ui");
    if (!raw) return "light";
    const parsed = JSON.parse(raw);
    const theme = parsed?.state?.theme;
    if (theme === "dark" || theme === "system") return theme;
    return "light";
  } catch {
    return "light";
  }
}

function resolveTheme(theme: "light" | "dark" | "system"): "light" | "dark" {
  if (theme === "dark") return "dark";
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return "light";
}

export function ThemeInitializer() {
  useEffect(() => {
    const theme = getPersistedTheme();
    const resolved = resolveTheme(theme);
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, []);

  return null;
}
