import { Fingerprint } from "lucide-react";
import type { FeedEvento } from "@/lib/actions";

export function RastreabilidadeBlock({ evento }: { evento: FeedEvento }) {
  const ev = evento.dados?.evidencia;
  return (
    <section className="mt-6 p-4 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50/50 dark:bg-[#1a1a1a]">
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-3">
        <Fingerprint className="w-3.5 h-3.5" />
        Rastreabilidade
      </h3>
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-xs">
        <Info label="ID do evento" value={`#${evento.id}`} />
        {evento.referencia_tipo && evento.referencia_id && (
          <Info
            label="Referência"
            value={`${evento.referencia_tipo} #${evento.referencia_id}`}
          />
        )}
        {ev?.classificador && <Info label="Classificador" value={ev.classificador} />}
        {ev?.probabilidade !== undefined && ev?.probabilidade !== null && (
          <Info
            label="Probabilidade"
            value={`${(Number(ev.probabilidade) * 100).toFixed(0)}%`}
          />
        )}
        <Info
          label="Origem"
          value={evento.origem === "dagster" ? "Análise automática (Baque)" : "Descoberta via chat"}
        />
        <Info label="Publicado em" value={new Date(evento.created_at).toLocaleString("pt-BR")} />
      </dl>
      {ev?.criterios && ev.criterios.length > 0 && (
        <div className="mt-4">
          <h4 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">
            Critérios aplicados
          </h4>
          <ul className="space-y-1.5 text-xs text-zinc-600 dark:text-zinc-300">
            {ev.criterios.map((c, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-zinc-400">•</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-zinc-400 dark:text-zinc-500 font-mono text-[10px] uppercase tracking-wide">
        {label}
      </dt>
      <dd className="text-zinc-700 dark:text-zinc-200 mt-0.5">{value}</dd>
    </div>
  );
}
