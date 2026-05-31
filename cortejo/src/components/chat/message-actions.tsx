"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Copy, Check, ThumbsUp, ThumbsDown } from "lucide-react";
import { submitFeedback } from "@/lib/actions";

const DISLIKE_CATEGORIES = [
  "Informação incorreta",
  "Link ou fonte incorreta",
  "Não respondeu",
  "Ofensivo ou inadequado",
];

const iconButton =
  "p-1.5 rounded-lg text-zinc-400 dark:text-zinc-500 hover:bg-black/5 dark:hover:bg-white/5 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors";

/**
 * Barra de ações abaixo de cada resposta da Calunga: copiar, curtir e não
 * curtir. Os polegares ficam sempre disponíveis e neutros (sem estado de
 * selecionado, sem mudar de cor): clicar abre um modal de detalhe opcional
 * (categoria + comentário) e fechar o modal registra o feedback (append-only).
 */
export default function MessageActions({
  content,
  messageId,
}: {
  content: string;
  messageId: string | null;
}) {
  const [copied, setCopied] = useState(false);
  const [modalTipo, setModalTipo] = useState<"like" | "dislike" | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard blocked; nothing to do
    }
  }, [content]);

  const send = useCallback(
    async (tipo: "like" | "dislike", categoria?: string, comentario?: string) => {
      if (messageId == null) return;
      await submitFeedback(messageId, tipo, categoria, comentario);
    },
    [messageId],
  );

  return (
    <div className="flex items-center gap-1 -mt-2 mb-6">
      <button type="button" onClick={handleCopy} aria-label="Copiar resposta" title="Copiar" className={iconButton}>
        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      </button>

      <button
        type="button"
        onClick={() => setModalTipo("like")}
        aria-label="Resposta útil"
        title="Resposta útil"
        className={iconButton}
      >
        <ThumbsUp className="w-4 h-4" />
      </button>

      <button
        type="button"
        onClick={() => setModalTipo("dislike")}
        aria-label="Resposta não útil"
        title="Resposta não útil"
        className={iconButton}
      >
        <ThumbsDown className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {modalTipo && (
          <FeedbackModal
            tipo={modalTipo}
            onSubmit={(categoria, comentario) => {
              send(modalTipo, categoria, comentario);
              setModalTipo(null);
            }}
            onCancel={() => {
              send(modalTipo);
              setModalTipo(null);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function FeedbackModal({
  tipo,
  onSubmit,
  onCancel,
}: {
  tipo: "like" | "dislike";
  onSubmit: (categoria?: string, comentario?: string) => void;
  onCancel: () => void;
}) {
  const [categoria, setCategoria] = useState("");
  const [comentario, setComentario] = useState("");
  const isPositive = tipo === "like";

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onCancel}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative w-full max-w-md bg-white dark:bg-[#2f2f2f] rounded-2xl p-6 shadow-xl border border-zinc-200 dark:border-zinc-800"
      >
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
          {isPositive ? "Enviar feedback positivo" : "Enviar feedback negativo"}
        </h3>

        {!isPositive && (
          <div className="mb-4">
            <label className="block text-sm text-zinc-500 dark:text-zinc-400 mb-1.5">
              Tipo de problema (opcional)
            </label>
            <select
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              className="w-full bg-[#f4f4f4] dark:bg-[#212121] border border-zinc-200 dark:border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-500"
            >
              <option value="">Selecione...</option>
              {DISLIKE_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm text-zinc-500 dark:text-zinc-400 mb-1.5">
            Detalhes (opcional)
          </label>
          <textarea
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            rows={3}
            maxLength={2000}
            placeholder={isPositive ? "O que foi útil nesta resposta?" : "O que esteve errado nesta resposta?"}
            className="w-full bg-[#f4f4f4] dark:bg-[#212121] border border-zinc-200 dark:border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 resize-none focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-500"
          />
        </div>

        <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-6">
          Seu feedback ajuda a melhorar a Calunga.
        </p>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => onSubmit(categoria || undefined, comentario.trim() || undefined)}
            className="px-4 py-2 text-sm font-medium text-white dark:text-black bg-black dark:bg-white hover:opacity-80 rounded-full transition-opacity"
          >
            Enviar
          </button>
        </div>
      </motion.div>
    </div>
  );
}
