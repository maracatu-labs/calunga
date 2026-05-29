import Link from "next/link";
import { Home, Rss } from "lucide-react";

export const metadata = {
  title: "Maracatu - Página não encontrada",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center px-4 text-center bg-white dark:bg-[#212121]">
      <div className="max-w-md w-full flex flex-col items-center">
        <div className="bg-black dark:bg-white text-white dark:text-black w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold mb-6 shadow-sm">
          M
        </div>
        <p className="text-sm font-medium text-emerald-600 dark:text-emerald-500 mb-2">
          Erro 404
        </p>
        <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 mb-3">
          Essa página sumiu do cortejo
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8 leading-relaxed">
          O link pode estar quebrado, ter expirado ou a página foi movida. Se você chegou
          aqui por uma conversa compartilhada, talvez ela não seja mais pública.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-black dark:bg-white text-white dark:text-black rounded-full font-medium hover:opacity-80 transition-opacity"
          >
            <Home className="w-4 h-4" />
            Voltar ao início
          </Link>
          <Link
            href="/feed"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-full font-medium hover:bg-zinc-50 dark:hover:bg-[#2f2f2f] transition-colors"
          >
            <Rss className="w-4 h-4" />
            Ver o feed
          </Link>
        </div>
      </div>
    </div>
  );
}
