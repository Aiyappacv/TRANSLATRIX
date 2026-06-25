import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

function applyTheme(theme: Theme) {
  if (theme === "dark") {
    document.documentElement.classList.add("dark");
  } else if (theme === "system") {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", prefersDark);
  } else {
    document.documentElement.classList.remove("dark");
  }
}

interface UiState {
  sidebarCollapsed: boolean;
  theme: Theme;
  commandOpen: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: Theme) => void;
  setCommandOpen: (open: boolean) => void;
}

let mediaQuery: MediaQueryList | null = null;
let mediaListener: ((e: MediaQueryListEvent) => void) | null = null;

function watchSystemTheme(theme: Theme) {
  if (mediaListener) {
    mediaQuery?.removeEventListener("change", mediaListener);
    mediaListener = null;
  }
  if (theme !== "system") return;
  mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  mediaListener = (e: MediaQueryListEvent) => {
    document.documentElement.classList.toggle("dark", e.matches);
  };
  mediaQuery.addEventListener("change", mediaListener);
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: "light",
      commandOpen: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      setTheme: (theme) => {
        applyTheme(theme);
        watchSystemTheme(theme);
        set({ theme });
      },
      setCommandOpen: (commandOpen) => set({ commandOpen }),
    }),
    {
      name: "translatrix-ui",
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyTheme(state.theme);
          watchSystemTheme(state.theme);
        }
      },
    },
  ),
);
