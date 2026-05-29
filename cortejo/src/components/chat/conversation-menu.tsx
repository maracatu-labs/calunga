"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { MoreVertical, Share2, Trash2 } from "lucide-react";

type Props = {
  onShare: () => void;
  onDelete: () => void;
  isActive: boolean;
};

// Per-conversation dropdown anchored to a three-dots trigger. Visible on
// hover for desktop, always visible while the menu is open. Matches the
// affordance used by ChatGPT and Claude conversation lists.
export default function ConversationMenu({ onShare, onDelete, isActive }: Props) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(event: MouseEvent) {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
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

  return (
    <div ref={wrapperRef} className="relative">
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Opções da conversa"
        title="Opções"
        className={
          "p-1 rounded-md transition-all " +
          (open || isActive
            ? "opacity-100 text-zinc-500 dark:text-zinc-400"
            : "opacity-0 group-hover:opacity-100 text-zinc-400") +
          " hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-black/5 dark:hover:bg-white/10"
        }
      >
        <MoreVertical className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.12 }}
            role="menu"
            aria-label="Opções da conversa"
            className="absolute z-50 right-0 top-full mt-1 min-w-[180px] p-1 rounded-xl bg-white dark:bg-[#2f2f2f] border border-zinc-200 dark:border-zinc-800 shadow-lg"
          >
            <button
              role="menuitem"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setOpen(false);
                onShare();
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg text-zinc-700 dark:text-zinc-200 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              <Share2 className="w-4 h-4" />
              <span>Compartilhar</span>
            </button>
            <button
              role="menuitem"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setOpen(false);
                onDelete();
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>Apagar</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
