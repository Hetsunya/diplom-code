import { create } from "zustand";

export type ThemeMode = "light" | "dark";

type UIState = {
  theme: ThemeMode;
  sidebarOpen: boolean;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
};

const THEME_KEY = "emeeting_theme";
const SIDEBAR_KEY = "emeeting_sidebar_open";

function readTheme(): ThemeMode {
  try {
    const v = localStorage.getItem(THEME_KEY);
    if (v === "dark" || v === "light") return v;
  } catch {
    /* ignore */
  }
  return "light";
}

function readSidebarOpen(): boolean {
  try {
    const v = localStorage.getItem(SIDEBAR_KEY);
    if (v === "0") return false;
    if (v === "1") return true;
  } catch {
    /* ignore */
  }
  return true;
}

function applyTheme(theme: ThemeMode) {
  document.documentElement.setAttribute("data-theme", theme);
}

export const useUIStore = create<UIState>((set, get) => ({
  theme: readTheme(),
  sidebarOpen: readSidebarOpen(),
  setTheme: (theme) => {
    applyTheme(theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* ignore */
    }
    set({ theme });
  },
  toggleTheme: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    get().setTheme(next);
  },
  setSidebarOpen: (open) => {
    try {
      localStorage.setItem(SIDEBAR_KEY, open ? "1" : "0");
    } catch {
      /* ignore */
    }
    set({ sidebarOpen: open });
  },
  toggleSidebar: () => {
    get().setSidebarOpen(!get().sidebarOpen);
  },
}));

export function initUIStore() {
  applyTheme(useUIStore.getState().theme);
}
