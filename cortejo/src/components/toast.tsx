"use client";

import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, Check } from "lucide-react";

type Props = {
  message: string | null;
  kind?: "success" | "error";
};

// Single inline toast pinned to the top of the viewport. Animated in and
// out; the message string is the source of truth — pass null to dismiss.
// The caller is responsible for the dismiss timer (typically 3-4s).
export default function Toast({ message, kind = "success" }: Props) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          key={message}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.18 }}
          role="status"
          aria-live="polite"
          className={
            "fixed top-3 left-1/2 -translate-x-1/2 z-[100] max-w-md mx-auto px-4 py-2.5 text-sm rounded-full shadow-lg flex items-center gap-2 " +
            (kind === "error"
              ? "bg-red-600 text-white"
              : "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900")
          }
        >
          {kind === "error" ? (
            <AlertTriangle className="w-4 h-4 shrink-0" />
          ) : (
            <Check className="w-4 h-4 shrink-0" />
          )}
          <span className="truncate">{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
