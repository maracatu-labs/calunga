"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Search, Check, AlertTriangle, Loader2 } from "lucide-react";

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
 * Agrupa eventos de tool (tool_start + tool_end) em chamadas discretas e
 * renderiza como pills animadas. Cada tool_start abre uma chamada "running";
 * o primeiro tool_end correspondente com mesmo nome de tool fecha como ok ou
 * error.
 */
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

export default function ToolActivity({ events }: { events: ToolEvent[] }) {
  const calls = useMemo<ToolCall[]>(() => {
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
  }, [events]);

  if (calls.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5 my-2">
      <AnimatePresence initial={false}>
        {calls.map((call) => {
          const label = TOOL_LABELS[call.tool] || call.tool;
          const argsSummary = summarizeArgs(call.args);
          return (
            <motion.div
              key={call.id}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400"
            >
              <span className="flex items-center justify-center w-4 h-4 shrink-0">
                {call.status === "running" && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                )}
                {call.status === "ok" && (
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                )}
                {call.status === "error" && (
                  <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                )}
              </span>
              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800/70 border border-zinc-200 dark:border-zinc-700/60">
                <Search className="w-3 h-3" />
                <span className="font-medium">{label}</span>
                {argsSummary && (
                  <span className="text-zinc-400 dark:text-zinc-500 truncate max-w-[320px]">
                    · {argsSummary}
                  </span>
                )}
                {call.status === "error" && call.error && (
                  <span className="text-red-500 truncate max-w-[280px]">
                    · {call.error.slice(0, 120)}
                  </span>
                )}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export type { ToolEvent };
