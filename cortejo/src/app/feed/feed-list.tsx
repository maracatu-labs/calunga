"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "motion/react";
import {
  AlertTriangle,
  ArrowRight,
  Loader2,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { fetchFeed, type FeedEvento } from "@/lib/actions";
import { SeveridadePill, severidadeBarColor } from "./_components/severidade-pill";
import { LinkList } from "./_components/link-list";
import { timeAgo } from "./_components/time-ago";

type Props = {
  initialEventos: FeedEvento[];
  total: number;
  categoria?: string;
  pageSize: number;
};

const LABELS_ORIGEM: Record<string, string> = {
  dagster: "Análise automática",
  chat: "Descoberto por cidadão",
};

const ICONES_ORIGEM: Record<string, typeof Sparkles> = {
  dagster: Sparkles,
  chat: MessageSquare,
};

export default function FeedList({ initialEventos, total, categoria, pageSize }: Props) {
  const [eventos, setEventos] = useState<FeedEvento[]>(initialEventos);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(initialEventos.length >= total);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadingRef = useRef(false);

  useEffect(() => {
    setEventos(initialEventos);
    setDone(initialEventos.length >= total);
  }, [initialEventos, total]);

  const loadMore = useCallback(async () => {
    if (loadingRef.current || done) return;
    loadingRef.current = true;
    setLoading(true);
    try {
      const { eventos: next } = await fetchFeed({
        categoria,
        limit: pageSize,
        offset: eventos.length,
      });
      if (!next || next.length === 0) {
        setDone(true);
        return;
      }
      setEventos((prev) => {
        const seen = new Set(prev.map((e) => e.id));
        const merged = [...prev, ...next.filter((e) => !seen.has(e.id))];
        if (merged.length >= total) setDone(true);
        return merged;
      });
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [categoria, done, eventos.length, pageSize, total]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || done) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { rootMargin: "400px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [loadMore, done]);

  return (
    <div className="space-y-5">
      {eventos.map((evento, i) => (
        <FeedCard key={evento.id} evento={evento} index={i} />
      ))}

      {!done && (
        <div ref={sentinelRef} className="flex justify-center py-8">
          {loading && <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />}
        </div>
      )}

      {done && eventos.length > 0 && (
        <p className="text-center text-xs text-zinc-400 dark:text-zinc-500 py-6">
          Você chegou ao fim do feed.
        </p>
      )}
    </div>
  );
}

function FeedCard({ evento, index }: { evento: FeedEvento; index: number }) {
  const dados = evento.dados || {};
  const ator = dados.ator;
  const acao = dados.acao;
  const objeto = dados.objeto;
  const evidencia = dados.evidencia;
  const contexto = dados.contexto;
  const links = dados.links || [];
  const severidade = dados.severidade ?? "informativo";
  const OrigemIcone = ICONES_ORIGEM[evento.origem] || Sparkles;
  const origemLabel = LABELS_ORIGEM[evento.origem] || evento.origem;
  const barColor = severidadeBarColor(severidade);

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 10) * 0.03 }}
      className="relative overflow-hidden rounded-2xl bg-[#f4f4f4] dark:bg-[#2f2f2f]"
    >
      {}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${barColor}`} aria-hidden />

      <div className="p-5 pl-6">
        {}
        <header className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            {ator?.foto_url ? (
              <Image
                src={ator.foto_url}
                alt={ator.nome}
                width={40}
                height={40}
                className="w-10 h-10 rounded-full object-cover shrink-0 bg-white dark:bg-[#212121]"
                unoptimized
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-white dark:bg-[#212121] flex items-center justify-center shrink-0 text-xs font-semibold text-zinc-500">
                {initials(ator?.nome)}
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <SeveridadePill severidade={severidade} />
                <span className="text-xs text-zinc-400 dark:text-zinc-500 flex items-center gap-1">
                  <OrigemIcone className="w-3 h-3" />
                  {origemLabel}
                </span>
              </div>
              {ator && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 truncate">
                  <span className="font-medium text-zinc-700 dark:text-zinc-200">{ator.nome}</span>
                  {ator.papel && <span> · {ator.papel}</span>}
                  {ator.partido && ator.uf && <span> · {ator.partido}/{ator.uf}</span>}
                </p>
              )}
            </div>
          </div>
          <time className="text-xs text-zinc-400 dark:text-zinc-500 whitespace-nowrap shrink-0">
            {timeAgo(evento.created_at)}
          </time>
        </header>

        {}
        <h2 className="font-semibold text-[15px] leading-snug text-zinc-900 dark:text-zinc-100 mb-2">
          {evento.titulo}
        </h2>

        {}
        {acao?.valor_formatado && (
          <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 tabular-nums mb-3">
            {acao.valor_formatado}
          </p>
        )}

        {}
        <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed mb-3">
          {evento.descricao}
        </p>

        {}
        {objeto?.nome && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400 mb-3">
            <span className="font-medium text-zinc-600 dark:text-zinc-300">
              {labelObjeto(objeto.tipo)}:
            </span>
            <span>{objeto.nome}</span>
            {objeto.identificador_formatado && (
              <span className="font-mono text-[11px] bg-white dark:bg-[#212121] px-2 py-0.5 rounded">
                {objeto.identificador_formatado}
              </span>
            )}
          </div>
        )}

        {}
        {evidencia?.motivo_humano && (
          <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-700">
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1.5">
              Por que é suspeito
            </p>
            <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed">
              {evidencia.motivo_humano}
            </p>
          </div>
        )}

        {}
        {contexto?.alertas && contexto.alertas.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {contexto.alertas.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>{a}</span>
              </li>
            ))}
          </ul>
        )}

        {}
        <LinkList links={links} />

        {}
        <footer className="mt-5 pt-4 border-t border-zinc-200 dark:border-zinc-700 flex items-center justify-between gap-3 flex-wrap">
          <Link
            href={`/feed/${evento.id}`}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-200 hover:text-zinc-900 dark:hover:text-white transition-colors"
          >
            Ver detalhes <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            href={`/chat?q=${encodeURIComponent(
              ator?.nome
                ? `Me conte mais sobre o caso: ${evento.titulo}`
                : `Me explique este evento: ${evento.titulo}`,
            )}`}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
          >
            <MessageSquare className="w-3 h-3" />
            Perguntar ao Calunga
          </Link>
        </footer>
      </div>
    </motion.article>
  );
}

function initials(nome?: string | null): string {
  if (!nome) return "?";
  const parts = nome.trim().split(/\s+/);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

function labelObjeto(tipo: string): string {
  switch (tipo) {
    case "fornecedor":
      return "Fornecedor";
    case "proposicao":
      return "Proposição";
    case "emenda":
      return "Emenda";
    case "empresa":
      return "Empresa";
    default:
      return "Alvo";
  }
}
