"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { Check, Copy, Globe, Loader2, Mail, MessageCircle, Share2, X } from "lucide-react";
import { shareChat } from "@/lib/actions";

type Props = {
  chatId: string;
  chatTitle?: string;
  onClose: () => void;
};

// X (Twitter) logo as inline SVG: lucide-react does not ship one and we want
// a recognisable mark without dragging another icon library.
function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className={className} fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className={className} fill="currentColor">
      <path d="M20.52 3.48A11.93 11.93 0 0012.04 0C5.46 0 .12 5.34.12 11.92c0 2.1.55 4.15 1.6 5.96L0 24l6.27-1.65a11.86 11.86 0 005.76 1.47h.01c6.57 0 11.92-5.34 11.92-11.92 0-3.18-1.24-6.18-3.44-8.42zM12.04 21.5h-.01a9.93 9.93 0 01-5.07-1.39l-.36-.22-3.72.98 1-3.62-.24-.37a9.92 9.92 0 01-1.52-5.28c0-5.47 4.45-9.92 9.92-9.92 2.65 0 5.14 1.03 7.02 2.91a9.86 9.86 0 012.9 7.02c0 5.47-4.45 9.92-9.92 9.92zm5.44-7.42c-.3-.15-1.77-.87-2.04-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.95 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51l-.57-.01c-.2 0-.52.07-.79.37-.27.3-1.04 1.01-1.04 2.47 0 1.46 1.07 2.87 1.22 3.07.15.2 2.1 3.2 5.08 4.49.71.31 1.27.49 1.7.63.71.23 1.36.2 1.87.12.57-.08 1.77-.72 2.02-1.42.25-.7.25-1.3.18-1.42-.07-.12-.27-.2-.57-.35z" />
    </svg>
  );
}

const PUBLIC_WARNING =
  "Qualquer pessoa com este link poderá ver a consulta e todas as respostas. Não compartilhe se tiver informações que você não queira públicas.";

export default function ShareModal({ chatId, chatTitle, onClose }: Props) {
  const [status, setStatus] = useState<"sharing" | "ready" | "error">("sharing");
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const url = typeof window !== "undefined" ? `${window.location.origin}/compartilhar/${chatId}` : "";
  const shareText = chatTitle ? `${chatTitle} • Maracatu` : "Confira esta consulta no Maracatu";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await shareChat(chatId);
      if (cancelled) return;
      setStatus(result.ok ? "ready" : "error");
    })();
    return () => {
      cancelled = true;
    };
  }, [chatId]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      inputRef.current?.select();
    } catch {
      inputRef.current?.select();
      document.execCommand?.("copy");
    }
  }

  async function handleNativeShare() {
    if (typeof navigator === "undefined" || !navigator.share) return;
    try {
      await navigator.share({ url, title: shareText, text: shareText });
    } catch {
      // user cancelled or share failed; nothing to do
    }
  }

  const canNativeShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-modal-title"
        className="relative w-full max-w-md bg-white dark:bg-[#2f2f2f] rounded-2xl p-6 shadow-xl border border-zinc-200 dark:border-zinc-800"
      >
        <button
          onClick={onClose}
          aria-label="Fechar"
          className="absolute top-3 right-3 p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 mb-1">
          <Globe className="w-5 h-5 text-zinc-500 dark:text-zinc-400" />
          <h3 id="share-modal-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Compartilhar consulta
          </h3>
        </div>
        <p className="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 rounded-lg px-3 py-2 mt-3 mb-4">
          {PUBLIC_WARNING}
        </p>

        {status === "error" ? (
          <p className="text-sm text-red-600 dark:text-red-400">
            Não foi possível gerar o link agora. Tente novamente em alguns instantes.
          </p>
        ) : (
          <>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1.5">
              Link público
            </label>
            <div className="flex items-stretch gap-2 mb-5">
              <input
                ref={inputRef}
                readOnly
                value={status === "sharing" ? "Gerando link..." : url}
                onFocus={(e) => e.currentTarget.select()}
                className="flex-1 min-w-0 px-3 py-2.5 text-sm rounded-lg bg-zinc-50 dark:bg-[#1f1f1f] border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-200 font-mono truncate focus:outline-none focus:ring-2 focus:ring-zinc-300 dark:focus:ring-zinc-600"
              />
              <button
                onClick={handleCopy}
                disabled={status !== "ready"}
                className="flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium rounded-lg bg-black dark:bg-white text-white dark:text-black hover:opacity-80 disabled:opacity-40 transition-opacity"
                aria-label="Copiar link"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? "Copiado" : "Copiar"}</span>
              </button>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                Compartilhar via
              </p>
              <div className="grid grid-cols-2 gap-2">
                {canNativeShare && (
                  <button
                    onClick={handleNativeShare}
                    disabled={status !== "ready"}
                    className="col-span-2 flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:opacity-80 disabled:opacity-40 transition-opacity"
                  >
                    <Share2 className="w-4 h-4" />
                    Mais opções
                  </button>
                )}
                <a
                  href={`https://wa.me/?text=${encodeURIComponent(`${shareText}\n${url}`)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-disabled={status !== "ready"}
                  className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg bg-[#25d366] hover:bg-[#1ebe5d] text-white transition-colors aria-disabled:pointer-events-none aria-disabled:opacity-40"
                >
                  <WhatsAppIcon className="w-4 h-4" />
                  WhatsApp
                </a>
                <a
                  href={`https://x.com/intent/post?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(url)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-disabled={status !== "ready"}
                  className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg bg-black hover:bg-zinc-800 text-white transition-colors aria-disabled:pointer-events-none aria-disabled:opacity-40"
                >
                  <XIcon className="w-4 h-4" />
                  X / Twitter
                </a>
                <a
                  href={`mailto:?subject=${encodeURIComponent(shareText)}&body=${encodeURIComponent(`${shareText}\n\n${url}`)}`}
                  aria-disabled={status !== "ready"}
                  className={`flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors aria-disabled:pointer-events-none aria-disabled:opacity-40 ${canNativeShare ? "" : "col-span-2"}`}
                >
                  <Mail className="w-4 h-4" />
                  E-mail
                </a>
              </div>
              {status === "sharing" && (
                <p className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400 pt-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Gerando link público...
                </p>
              )}
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}
