import Link from "next/link";
import { Compass, Home } from "lucide-react";

export const metadata = {
  title: "Maracatu - Página não encontrada",
};

export default function NotFound() {
  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center bg-white dark:bg-[#212121] p-6">
      <div className="w-full max-w-md text-center space-y-6">
        <div className="w-14 h-14 mx-auto rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
          <Compass className="w-7 h-7 text-zinc-500 dark:text-zinc-400" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Página não encontrada
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Esse endereço não existe ou foi removido. Volte ao início e tente outro caminho.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-black dark:bg-white text-white dark:text-black text-sm font-medium hover:opacity-80 transition-opacity"
        >
          <Home className="w-4 h-4" /> Voltar ao início
        </Link>
      </div>
    </div>
  );
}
