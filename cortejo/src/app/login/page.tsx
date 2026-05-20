"use client";

import { useState, useActionState } from "react";
import { sendMagicLink } from "@/lib/actions";
import { motion } from "motion/react";
import { Loader2, Mail } from "lucide-react";

export default function Login() {
  const [sent, setSent] = useState(false);
  const [sentEmail, setSentEmail] = useState("");

  const [, formAction, isPending] = useActionState(async (_prev: unknown, formData: FormData) => {
    const email = formData.get("email") as string;
    if (!email) return;
    const result = await sendMagicLink(email);
    if (result.ok) {
      setSentEmail(email);
      setSent(true);
    }
  }, null);

  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center bg-white dark:bg-[#212121] p-4">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm"
      >
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-black dark:bg-white text-white dark:text-black rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-6">
            M
          </div>
          <h1 className="text-3xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">Fiscalize o dinheiro público</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Controle social, no ritmo do povo.</p>
        </div>

        {!sent ? (
          <form action={formAction} className="space-y-4">
            <div>
              <input
                name="email"
                type="email"
                placeholder="Endereço de e-mail"
                className="w-full px-4 py-4 rounded-xl border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-[#2f2f2f] text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent outline-none transition-all"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isPending}
              className="w-full flex items-center justify-center gap-2 bg-black dark:bg-white text-white dark:text-black py-4 rounded-full font-medium hover:opacity-80 transition-opacity disabled:opacity-50"
            >
              {isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : "Continuar"}
            </button>
            <p className="text-center text-sm text-zinc-500 dark:text-zinc-400 mt-4">
              Insira seu e-mail para acompanhar os gastos públicos.
            </p>
          </form>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center space-y-6"
          >
            <div className="p-6 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl">
              <Mail className="w-8 h-8 text-zinc-500 dark:text-zinc-400 mx-auto mb-3" />
              <p className="text-zinc-600 dark:text-zinc-400 mb-2">Enviamos um link de acesso para:</p>
              <strong className="text-lg font-medium text-zinc-900 dark:text-zinc-100">{sentEmail}</strong>
            </div>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Abra seu email e clique no link para acessar. O link expira em 15 minutos.
            </p>
            <button
              onClick={() => setSent(false)}
              className="text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors underline underline-offset-2"
            >
              Usar outro email
            </button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
