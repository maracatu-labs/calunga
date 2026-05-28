import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  MessageSquare,
  ScrollText,
} from "lucide-react";
import { getFeedEvento } from "@/lib/feed-api";
import { SeveridadePill, severidadeBarColor } from "../_components/severidade-pill";
import { LinkList } from "../_components/link-list";
import { RastreabilidadeBlock } from "../_components/rastreabilidade-block";
import { timeAgo } from "../_components/time-ago";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const evento = await getFeedEvento(Number(id));
  if (!evento) return { title: "Maracatu - Evento não encontrado" };
  return {
    title: `Maracatu - ${evento.titulo}`,
    description: evento.descricao?.slice(0, 160),
  };
}

export default async function FeedDetailPage({ params }: Props) {
  const { id } = await params;
  const evento = await getFeedEvento(Number(id));
  if (!evento) notFound();

  const dados = evento.dados || {};
  const ator = dados.ator;
  const acao = dados.acao;
  const objeto = dados.objeto;
  const evidencia = dados.evidencia;
  const contexto = dados.contexto;
  const links = dados.links || [];
  const severidade = dados.severidade ?? "informativo";
  const barColor = severidadeBarColor(severidade);

  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-zinc-900 dark:text-zinc-100">
      {}
      <header className="h-14 flex items-center justify-between px-4 sm:px-6 bg-white/80 dark:bg-[#212121]/80 backdrop-blur-md sticky top-0 z-10 border-b border-zinc-100 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <Link href="/feed" className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Voltar ao feed
          </Link>
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
        <section className="relative overflow-hidden rounded-3xl bg-[#f4f4f4] dark:bg-[#2f2f2f] p-6 sm:p-8">
          <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${barColor}`} aria-hidden />
          <div className="pl-2 sm:pl-4">
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <SeveridadePill severidade={severidade} />
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                {evento.origem === "dagster" ? "Análise automática" : "Descoberto por cidadão"}
              </span>
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                · {timeAgo(evento.created_at)}
              </span>
            </div>

            <div className="flex items-start gap-4 mb-5">
              {ator?.foto_url && (
                <Image
                  src={ator.foto_url}
                  alt={ator.nome}
                  width={64}
                  height={64}
                  className="w-16 h-16 rounded-full object-cover shrink-0 bg-white dark:bg-[#212121]"
                  unoptimized
                />
              )}
              <div className="min-w-0">
                <h1 className="text-xl sm:text-2xl font-bold leading-tight mb-2">
                  {evento.titulo}
                </h1>
                {ator && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    <span className="font-medium text-zinc-700 dark:text-zinc-200">{ator.nome}</span>
                    {ator.papel && <span> · {ator.papel}</span>}
                    {ator.partido && ator.uf && <span> · {ator.partido}/{ator.uf}</span>}
                  </p>
                )}
              </div>
            </div>

            {acao?.valor_formatado && (
              <div className="mb-5">
                <p className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">
                  Valor envolvido
                </p>
                <p className="text-4xl sm:text-5xl font-bold tabular-nums text-zinc-900 dark:text-zinc-100">
                  {acao.valor_formatado}
                </p>
              </div>
            )}
          </div>
        </section>

        {}
        <Section titulo="O que aconteceu" icone={ScrollText}>
          <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-200">
            {evento.descricao}
          </p>
          {objeto && objeto.nome && (
            <dl className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <KV label={labelObjeto(objeto.tipo)} value={objeto.nome} />
              {objeto.identificador_formatado && (
                <KV label="Identificador" value={objeto.identificador_formatado} mono />
              )}
              {objeto.detalhes?.cnae && <KV label="Atividade (CNAE)" value={objeto.detalhes.cnae} />}
              {objeto.detalhes?.situacao_cadastral && (
                <KV label="Situação cadastral" value={objeto.detalhes.situacao_cadastral} />
              )}
              {objeto.detalhes?.municipio && (
                <KV
                  label="Localização"
                  value={`${objeto.detalhes.municipio}${objeto.detalhes.uf_empresa ? ` / ${objeto.detalhes.uf_empresa}` : ""}`}
                />
              )}
              {objeto.detalhes?.autor && <KV label="Autor" value={objeto.detalhes.autor} />}
              {objeto.detalhes?.tema && <KV label="Tema" value={objeto.detalhes.tema} />}
              {acao?.data && <KV label="Data" value={new Date(acao.data).toLocaleDateString("pt-BR")} />}
              {acao?.local && <KV label="Local" value={acao.local} />}
            </dl>
          )}

          {objeto?.detalhes?.sancoes && Array.isArray(objeto.detalhes.sancoes) && objeto.detalhes.sancoes.length > 0 && (
            <div className="mt-5 p-4 rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50/60 dark:bg-red-900/10">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-red-700 dark:text-red-300 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                Sanções registradas
              </h4>
              <ul className="space-y-2">
                {objeto.detalhes.sancoes.map((s: any, i: number) => (
                  <li key={i} className="text-xs text-red-800 dark:text-red-200">
                    <span className="font-semibold">{s.tipo}</span> · {s.orgao}
                    {s.inicio && <span> · desde {new Date(s.inicio).toLocaleDateString("pt-BR")}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>

        {}
        {evidencia?.motivo_humano && (
          <Section titulo="Por que é suspeito" icone={AlertTriangle}>
            <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-200">
              {evidencia.motivo_humano}
            </p>
          </Section>
        )}

        {}
        {contexto?.alertas && contexto.alertas.length > 0 && (
          <Section titulo="Pontos de atenção" icone={AlertTriangle}>
            <ul className="space-y-2">
              {contexto.alertas.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-zinc-700 dark:text-zinc-200">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-500" />
                  <span>{a}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {}
        {links.length > 0 && (
          <Section titulo="Como verificar" icone={CheckCircle2}>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-3">
              Todos os links abaixo abrem fontes oficiais. O Maracatu não hospeda nem intermedia esses dados.
            </p>
            <LinkList links={links} compact />
          </Section>
        )}

        {}
        <RastreabilidadeBlock evento={evento} />

        {}
        <div className="mt-8 flex flex-col sm:flex-row gap-3">
          <Link
            href={`/chat?q=${encodeURIComponent(`Me conte mais sobre este caso: ${evento.titulo}`)}`}
            className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 bg-black dark:bg-white text-white dark:text-black rounded-full font-medium text-sm hover:opacity-80 transition-opacity"
          >
            <MessageSquare className="w-4 h-4" />
            Perguntar ao Calunga sobre este caso
          </Link>
          <Link
            href="/feed"
            className="inline-flex items-center justify-center gap-2 px-5 py-3 border border-zinc-300 dark:border-zinc-700 rounded-full font-medium text-sm text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-[#2f2f2f] transition-colors"
          >
            Voltar ao feed
          </Link>
        </div>
      </main>

      <footer className="max-w-3xl mx-auto px-4 sm:px-6 text-center text-xs text-zinc-400 dark:text-zinc-500 pt-8 pb-12 border-t border-zinc-100 dark:border-zinc-800 mt-12">
        <p>Maracatu. Controle social da administração pública brasileira, no ritmo do povo.</p>
      </footer>
    </div>
  );
}

function Section({
  titulo,
  icone: Icon,
  children,
}: {
  titulo: string;
  icone: typeof AlertTriangle;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-8">
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-3">
        <Icon className="w-3.5 h-3.5" />
        {titulo}
      </h3>
      {children}
    </section>
  );
}

function KV({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide text-zinc-400 dark:text-zinc-500 font-mono">
        {label}
      </dt>
      <dd className={`mt-0.5 text-zinc-700 dark:text-zinc-200 ${mono ? "font-mono text-xs" : ""}`}>
        {value}
      </dd>
    </div>
  );
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
