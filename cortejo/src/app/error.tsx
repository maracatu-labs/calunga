"use client";

import Link from "next/link";
import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {

    console.error("[app/error]", error);
  }, [error]);

  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center bg-white dark:bg-[#212121] p-6">
      <div className="w-full max-w-md text-center space-y-6">
        <div className="w-14 h-14 mx-auto rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
          <AlertTriangle className="w-7 h-7 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Estamos com instabilidade
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            O Maracatu não conseguiu completar sua requisição agora. Pode ser uma falha de conexão temporária; geralmente passa em alguns instantes.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={reset}
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-black dark:bg-white text-white dark:text-black text-sm font-medium hover:opacity-80 transition-opacity"
          >
            <RefreshCw className="w-4 h-4" /> Tentar de novo
          </button>
          <Link
            href="/"
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-full border border-zinc-200 dark:border-zinc-800 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
          >
            <Home className="w-4 h-4" /> Voltar ao início
          </Link>
        </div>
        {error.digest && (
          <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-4">
            Código de referência: {error.digest}
          </p>
        )}
      </div>
    </div>
  );
}
