"use client";

import { motion } from "motion/react";

/**
 * Três pontinhos pulsando, indicador de "gerando resposta". Cor neutra (segue
 * o texto), sem acento de marca. Substitui o antigo spinner em emerald.
 */
export default function TypingDots() {
  return (
    <div className="flex items-center gap-1 h-6 my-2 text-zinc-400 dark:text-zinc-500" role="status" aria-label="Gerando resposta">
      <motion.div animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0 }} className="w-1.5 h-1.5 bg-current rounded-full" />
      <motion.div animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }} className="w-1.5 h-1.5 bg-current rounded-full" />
      <motion.div animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }} className="w-1.5 h-1.5 bg-current rounded-full" />
    </div>
  );
}
