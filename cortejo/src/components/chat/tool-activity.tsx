"use client";

import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Check, AlertTriangle, Loader2, Sparkles, ChevronRight } from "lucide-react";

type ToolEvent =
  | {
      type: "tool_start";
      tool: string;
      args?: Record<string, unknown>;
    }
  | {
      type: "tool_end";
      tool: string;
      status: "ok" | "error";
      preview?: string;
      error?: string;
    };

type ToolCall = {
  id: number;
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "ok" | "error";
  error?: string;
};

const TOOL_LABELS: Record<string, string> = {
  buscar_despesas: "Buscando despesas",
  ranking_despesas: "Calculando ranking de gastos",
  listar_parlamentares: "Listando parlamentares",
  listar_executivos: "Listando governadores e prefeitos",
  buscar_suspeitas: "Buscando suspeitas",
  consultar_recibo: "Consultando recibo",
  buscar_empresa: "Consultando CNPJ",
  buscar_similar: "Busca semântica",
  explicar_termo: "Explicando termo",
  buscar_cpgf: "Buscando cartão corporativo",
  buscar_contratos: "Buscando contratos",
  buscar_viagens: "Buscando viagens",
  buscar_emendas: "Buscando emendas",
  buscar_dados_fiscais: "Buscando dados fiscais",
  buscar_despesas_federais: "Buscando execução orçamentária",
  buscar_votacoes: "Buscando votações",
};

function summarizeArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args).filter(([, v]) => v != null && v !== "");
  if (entries.length === 0) return "";
  const parts = entries.slice(0, 3).map(([k, v]) => {
    const valueStr = typeof v === "string" ? v : JSON.stringify(v);
    return `${k}: ${valueStr.length > 30 ? valueStr.slice(0, 30) + "…" : valueStr}`;
  });
  return parts.join(", ");
}

/**
 * Converte o array `data` crescente do useChat em eventos tipados de tool.
 * Ignora entradas que nao sao tool_start/tool_end.
 */
export function parseToolEvents(data: unknown): ToolEvent[] {
  if (!Array.isArray(data)) return [];
  const out: ToolEvent[] = [];
  for (const item of data) {
    if (typeof item !== "object" || item === null) continue;
    const obj = item as Record<string, unknown>;
    if (obj.type === "tool_start" && typeof obj.tool === "string") {
      out.push({
        type: "tool_start",
        tool: obj.tool,
        args: (obj.args as Record<string, unknown> | undefined) || {},
      });
    } else if (obj.type === "tool_end" && typeof obj.tool === "string") {
      out.push({
        type: "tool_end",
        tool: obj.tool,
        status: obj.status === "error" ? "error" : "ok",
        preview: typeof obj.preview === "string" ? obj.preview : undefined,
        error: typeof obj.error === "string" ? obj.error : undefined,
      });
    }
  }
  return out;
}

/**
 * Agrupa eventos (tool_start + tool_end) em chamadas discretas. Cada
 * tool_start abre uma chamada "running"; o primeiro tool_end com o mesmo
 * nome de tool a fecha como ok ou error.
 */
function buildCalls(events: ToolEvent[]): ToolCall[] {
  const result: ToolCall[] = [];
  const openByTool = new Map<string, ToolCall>();

  for (const ev of events) {
    if (ev.type === "tool_start") {
      const call: ToolCall = {
        id: result.length,
        tool: ev.tool,
        args: ev.args || {},
        status: "running",
      };
      result.push(call);
      openByTool.set(ev.tool, call);
    } else if (ev.type === "tool_end") {
      const open = openByTool.get(ev.tool);
      if (open) {
        open.status = ev.status;
        if (ev.status === "error") open.error = ev.error;
        openByTool.delete(ev.tool);
      }
    }
  }
  return result;
}

function StatusIcon({ status }: { status: ToolCall["status"] }) {
  if (status === "running") {
    return <Loader2 className="w-3.5 h-3.5 animate-spin text-zinc-400 dark:text-zinc-500" />;
  }
  if (status === "error") {
    return <AlertTriangle className="w-3.5 h-3.5 text-red-500" />;
  }
  return <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-500" />;
}

function ToolRow({ call }: { call: ToolCall }) {
  const label = TOOL_LABELS[call.tool] || call.tool;
  const argsSummary = summarizeArgs(call.args);
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="flex items-center justify-center w-4 h-4 shrink-0 mt-0.5">
        <StatusIcon status={call.status} />
      </span>
      <span className="min-w-0">
        <span
          className={
            call.status === "running"
              ? "font-medium text-zinc-600 dark:text-zinc-300"
              : "font-medium text-zinc-500 dark:text-zinc-400"
          }
        >
          {label}
        </span>
        {argsSummary && (
          <span className="text-zinc-400 dark:text-zinc-500"> · {argsSummary}</span>
        )}
        {call.status === "error" && call.error && (
          <span className="block text-red-500 mt-0.5">{call.error.slice(0, 120)}</span>
        )}
      </span>
    </div>
  );
}

/**
 * Feedback unificado de "raciocínio" da Calunga.
 *
 * - Enquanto `loading`: card com cabeçalho animado ("Analisando dados…") e o
 *   checklist das ferramentas (spinner vira check/erro).
 * - Quando termina (`!loading`) e houve ferramentas: colapsa num resumo
 *   discreto e expansível ("Consultei N fontes oficiais").
 */
export default function ToolActivity({
  events,
  loading,
}: {
  events: ToolEvent[];
  loading: boolean;
}) {
  const calls = useMemo(() => buildCalls(events), [events]);
  const [expanded, setExpanded] = useState(false);

  if (!loading && calls.length === 0) return null;

  if (!loading) {
    const n = calls.length;
    return (
      <div className="my-3">
        <button
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        >
          <ChevronRight
            className={"w-3.5 h-3.5 transition-transform " + (expanded ? "rotate-90" : "")}
          />
          Consultei {n} {n === 1 ? "fonte oficial" : "fontes oficiais"}
        </button>
        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.18 }}
              className="overflow-hidden"
            >
              <div className="flex flex-col gap-1.5 pt-2 pl-5">
                {calls.map((call) => (
                  <ToolRow key={call.id} call={call} />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="my-3 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-[#2f2f2f]/40 p-3"
    >
      <div className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300">
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
          className="flex"
        >
          <Sparkles className="w-4 h-4 text-emerald-500" />
        </motion.span>
        <span className="font-medium">Analisando dados…</span>
      </div>
      {calls.length > 0 && (
        <div className="flex flex-col gap-1.5 mt-2.5 pl-0.5">
          <AnimatePresence initial={false}>
            {calls.map((call) => (
              <motion.div
                key={call.id}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
              >
                <ToolRow call={call} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
}

export type { ToolEvent };
