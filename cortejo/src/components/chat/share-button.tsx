"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, Loader2, Share2 } from "lucide-react";
import { shareChat } from "@/lib/actions";

type Props = {
  chatId: string;
};

type Status = "idle" | "sharing" | "done" | "error";

/**
 * Header share button. Tap once and the right thing happens for the platform:
 *  - mobile / supported desktops: opens the native share sheet via Web Share API
 *  - everything else: copies the public link to the clipboard
 *
 * Either way the button morphs to a success state for ~3s and a toast surfaces
 * the public-link warning. No modal, no "are you sure" detour.
 */
export default function ShareButton({ chatId }: Props) {
  const [status, setStatus] = useState<Status>("idle");
  const [toast, setToast] = useState<string | null>(null);
  const resetTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (resetTimeout.current) clearTimeout(resetTimeout.current);
    if (toastTimeout.current) clearTimeout(toastTimeout.current);
  }, []);

  const url = typeof window !== "undefined" ? `${window.location.origin}/compartilhar/${chatId}` : "";

  const flashToast = (msg: string) => {
    setToast(msg);
    if (toastTimeout.current) clearTimeout(toastTimeout.current);
    toastTimeout.current = setTimeout(() => setToast(null), 4000);
  };

  const flashDone = () => {
    setStatus("done");
    if (resetTimeout.current) clearTimeout(resetTimeout.current);
    resetTimeout.current = setTimeout(() => setStatus("idle"), 2500);
  };

  const handleClick = useCallback(async () => {
    if (status === "sharing") return;
    setStatus("sharing");

    const result = await shareChat(chatId);
    if (!result.ok) {
      setStatus("error");
      flashToast("Não foi possível gerar o link agora. Tente novamente.");
      resetTimeout.current = setTimeout(() => setStatus("idle"), 3000);
      return;
    }

    if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
      try {
        // Pass only `url`: when the user picks "Copy" from the native share
        // sheet (macOS, iOS), the system concatenates every field we provide
        // into the clipboard. URL-only keeps the clipboard clean while still
        // letting WhatsApp/etc fetch a rich preview from our OG metadata.
        await navigator.share({ url });
        flashDone();
        return;
      } catch {
        // Web Share rejected (user cancelled or platform error) — fall through to copy.
      }
    }

    try {
      await navigator.clipboard.writeText(url);
      flashDone();
      flashToast("Link copiado. Qualquer pessoa com ele pode ver esta consulta.");
    } catch {
      setStatus("error");
      flashToast("Não foi possível copiar o link. Selecione manualmente.");
      resetTimeout.current = setTimeout(() => setStatus("idle"), 3000);
    }
  }, [chatId, url, status]);

  const label = {
    idle: "Compartilhar",
    sharing: "Gerando link...",
    done: "Link copiado",
    error: "Tente de novo",
  }[status];

  const Icon = {
    idle: Share2,
    sharing: Loader2,
    done: Check,
    error: Share2,
  }[status];

  return (
    <>
      <button
        onClick={handleClick}
        disabled={status === "sharing"}
        title="Compartilhar consulta como link público"
        aria-label="Compartilhar consulta como link público"
        className="flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-colors text-zinc-600 dark:text-zinc-300 disabled:opacity-60"
      >
        <Icon className={`w-4 h-4 ${status === "sharing" ? "animate-spin" : status === "done" ? "text-emerald-500" : ""}`} />
        <span className="hidden sm:inline">{label}</span>
      </button>

      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            role="status"
            aria-live="polite"
            className="fixed top-3 left-1/2 -translate-x-1/2 z-[100] max-w-md mx-auto px-4 py-2.5 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm rounded-full shadow-lg flex items-center gap-2"
          >
            <Check className="w-4 h-4 shrink-0" />
            <span className="truncate">{toast}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
