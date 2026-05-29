"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronUp, LogOut, Moon, Sun, Trash2 } from "lucide-react";

type Props = {
  email?: string;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onDeleteAll?: () => void;
  chatsCount: number;
};

// Compact user pill that expands upward into an action menu. Replaces the
// stack of theme toggle / bulk delete / sign out that previously crowded the
// sidebar footer. Modeled after the bottom-pill pattern used in Discord,
// Slack and Linear, where the user object is also the entry point for app
// preferences and the sign-out action.
export default function UserMenu({ email, theme, onToggleTheme, onDeleteAll, chatsCount }: Props) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(event: MouseEvent) {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onEsc(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  const handleToggleTheme = useCallback(() => {
    onToggleTheme();
    // intentionally do not close — toggling theme often warrants a quick second tap
  }, [onToggleTheme]);

  const handleDeleteAll = useCallback(() => {
    setOpen(false);
    onDeleteAll?.();
  }, [onDeleteAll]);

  const initial = email?.[0]?.toUpperCase() ?? "?";

  return (
    <div ref={wrapperRef} className="relative">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.97 }}
            transition={{ duration: 0.14 }}
            role="menu"
            aria-label="Menu do usuário"
            className="absolute bottom-full left-0 right-0 mb-2 p-1 rounded-2xl bg-white dark:bg-[#2f2f2f] border border-zinc-200 dark:border-zinc-800 shadow-lg"
          >
            <button
              role="menuitem"
              onClick={handleToggleTheme}
              className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-sm rounded-xl text-zinc-700 dark:text-zinc-200 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              <span className="flex items-center gap-2.5">
                {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                <span>{theme === "dark" ? "Tema claro" : "Tema escuro"}</span>
              </span>
            </button>

            {onDeleteAll && chatsCount > 0 && (
              <button
                role="menuitem"
                onClick={handleDeleteAll}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm rounded-xl text-zinc-700 dark:text-zinc-200 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                <span>Apagar todas as conversas</span>
              </button>
            )}

            <div className="h-px my-1 bg-zinc-200 dark:bg-zinc-700" role="separator" />

            <a
              href="/logout"
              role="menuitem"
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm rounded-xl text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Sair</span>
            </a>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-2 p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <span className="flex items-center gap-2 min-w-0">
          <span className="w-8 h-8 rounded-full bg-gradient-to-tr from-emerald-400 to-cyan-400 shrink-0 flex items-center justify-center text-xs font-semibold text-white" aria-hidden>
            {initial}
          </span>
          <span className="text-sm font-medium truncate text-zinc-700 dark:text-zinc-200 text-left">
            {email}
          </span>
        </span>
        <ChevronUp
          className={`w-4 h-4 text-zinc-400 transition-transform ${open ? "" : "rotate-180"}`}
          aria-hidden
        />
      </button>
    </div>
  );
}
