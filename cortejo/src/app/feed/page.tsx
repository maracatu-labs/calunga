import type { Metadata } from "next";
import Link from "next/link";
import { Rss, Search } from "lucide-react";
import { getFeed } from "@/lib/feed-api";
import FeedList from "./feed-list";

export const metadata: Metadata = {
  title: "Feed — Maracatu",
  description: "Acompanhe em tempo real as irregularidades, votações e emendas detectadas automaticamente pelo Maracatu.",
};

const PAGE_SIZE = 20;

const FILTROS = [
  { label: "Todos", value: "" },
  { label: "Irregularidades", value: "irregularidade" },
  { label: "Congresso", value: "congresso" },
  { label: "Governo Federal", value: "governo_federal" },
];

type Props = {
  searchParams: Promise<{ categoria?: string }>;
};

export default async function FeedPage({ searchParams }: Props) {
  const { categoria } = await searchParams;
  const categoriaFiltro = categoria || undefined;
  const { eventos, total } = await getFeed({
    categoria: categoriaFiltro,
    limit: PAGE_SIZE,
    offset: 0,
  });

  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-zinc-900 dark:text-zinc-100">
      {}
      <header className="h-14 flex items-center justify-between px-4 sm:px-6 bg-white/80 dark:bg-[#212121]/80 backdrop-blur-md sticky top-0 z-10 border-b border-zinc-100 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-3">
            <div className="bg-black dark:bg-white text-white dark:text-black w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold">M</div>
            <span className="font-semibold text-lg text-zinc-800 dark:text-zinc-200">Maracatu</span>
          </Link>
          <span className="text-zinc-300 dark:text-zinc-600">/</span>
          <span className="text-sm text-zinc-500 dark:text-zinc-400">Feed</span>
        </div>
        <Link
          href="/chat"
          className="text-sm font-medium px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
        >
          Consultar gastos
        </Link>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {}
        <section className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold mb-3">Feed de fiscalização</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
            Eventos detectados automaticamente pela análise diária do Maracatu e por cidadãos investigando no chat. Atualizado toda manhã com dados do dia anterior.
          </p>
        </section>

        {}
        <nav className="flex gap-2 mb-8 overflow-x-auto pb-2">
          {FILTROS.map((f) => {
            const active = (categoria || "") === f.value;
            return (
              <Link
                key={f.value}
                href={f.value ? `/feed?categoria=${f.value}` : "/feed"}
                className={`text-sm px-4 py-2 rounded-full whitespace-nowrap transition-colors ${
                  active
                    ? "bg-black dark:bg-white text-white dark:text-black"
                    : "border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-[#2f2f2f]"
                }`}
              >
                {f.label}
              </Link>
            );
          })}
        </nav>

        {}
        {eventos.length > 0 ? (
          <>
            <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-4">
              {total} {total === 1 ? "evento" : "eventos"}
            </p>
            <FeedList
              initialEventos={eventos}
              total={total}
              categoria={categoriaFiltro}
              pageSize={PAGE_SIZE}
            />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-20">
            <Rss className="w-12 h-12 text-zinc-300 dark:text-zinc-600 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Nenhum evento ainda</h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 text-center max-w-md mb-6">
              O feed é alimentado pela análise automática diária e pelas descobertas de cidadãos no chat. Os primeiros eventos aparecerão após a primeira rodada de análise.
            </p>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 text-sm font-medium px-6 py-3 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
            >
              <Search className="w-4 h-4" />
              Investigar no chat
            </Link>
          </div>
        )}
      </main>

      {}
      <footer className="max-w-3xl mx-auto px-4 sm:px-6 text-center text-xs text-zinc-400 dark:text-zinc-500 pt-8 pb-12 border-t border-zinc-100 dark:border-zinc-800">
        <p>Maracatu — Controle social da administração pública brasileira, no ritmo do povo.</p>
      </footer>
    </div>
  );
}
