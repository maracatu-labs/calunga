"use client";

import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Check, AlertTriangle, Loader2, Sparkles, ChevronRight, Terminal } from "lucide-react";

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
  const parts = entries.slice(0, 3).map(([, v]) => {
    const valueStr = typeof v === "string" ? v : JSON.stringify(v);
    return valueStr.length > 28 ? valueStr.slice(0, 28) + "…" : valueStr;
  });
  return parts.join(" · ");
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

function buildCalls(events: ToolEvent[]): ToolCall[] {
  const result: ToolCall[] = [];
  const openByTool = new Map<string, ToolCall>();
  for (const ev of events) {
    if (ev.type === "tool_start") {
      const call: ToolCall = { id: result.length, tool: ev.tool, args: ev.args || {}, status: "running" };
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

function StepIcon({ status }: { status: ToolCall["status"] }) {
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 animate-spin text-zinc-400 dark:text-zinc-500" />;
  if (status === "error") return <AlertTriangle className="w-3.5 h-3.5 text-red-500" />;
  return <Terminal className="w-3.5 h-3.5 text-zinc-400 dark:text-zinc-500" />;
}

/**
 * Timeline de raciocínio da Calunga (estilo dropdown), inspirada no padrão
 * de "tools/etapas" do claude.ai mas com a identidade do Maracatu.
 *
 * - Enquanto `loading`: cabeçalho animado "Analisando dados…" + a timeline
 *   das ferramentas (trilho vertical, cada passo com ícone + chip de args).
 * - Quando termina: colapsa num resumo "Consultei N fontes oficiais",
 *   expansível por clique para rever a timeline.
 *
 * Renderiza acima da resposta da LLM. O indicador de "escrevendo" fica
 * separado, abaixo do texto (ver StreamingIndicator).
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

  const open = loading || expanded;
  const n = calls.length;
  const headerLabel = loading
    ? "Analisando dados…"
    : `Consultei ${n} ${n === 1 ? "fonte oficial" : "fontes oficiais"}`;

  return (
    <div className="mb-4">
      <button
        type="button"
        onClick={() => !loading && setExpanded((v) => !v)}
        aria-expanded={open}
        disabled={loading}
        className="group flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400 disabled:cursor-default"
      >
        <motion.span
          animate={loading ? { opacity: [0.45, 1, 0.45] } : { opacity: 1 }}
          transition={loading ? { repeat: Infinity, duration: 1.4, ease: "easeInOut" } : { duration: 0.2 }}
          className="flex"
        >
          <Sparkles className="w-4 h-4 text-emerald-500" />
        </motion.span>
        <span className="font-medium">{headerLabel}</span>
        {!loading && (
          <ChevronRight
            className={"w-3.5 h-3.5 transition-transform group-hover:text-zinc-700 dark:group-hover:text-zinc-200 " + (open ? "rotate-90" : "")}
          />
        )}
      </button>

      <AnimatePresence initial={false}>
        {open && n > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="relative mt-2 ml-[7px] pl-5">
              <div className="absolute left-0 top-1 bottom-2 w-px bg-zinc-200 dark:bg-zinc-800" />
              {calls.map((call) => {
                const label = TOOL_LABELS[call.tool] || call.tool;
                const chip = summarizeArgs(call.args);
                return (
                  <div key={call.id} className="relative flex items-start gap-2.5 pb-3 last:pb-0">
                    <span className="absolute -left-[26px] top-0 flex items-center justify-center w-5 h-5 rounded-full bg-white dark:bg-[#212121]">
                      <StepIcon status={call.status} />
                    </span>
                    <div className="min-w-0 text-xs">
                      <span className="text-zinc-600 dark:text-zinc-300">{label}</span>
                      {chip && (
                        <span className="ml-2 inline-block px-1.5 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800/70 text-zinc-500 dark:text-zinc-400 align-middle max-w-[260px] truncate">
                          {chip}
                        </span>
                      )}
                      {call.status === "error" && call.error && (
                        <span className="block text-red-500 mt-1">{call.error.slice(0, 120)}</span>
                      )}
                    </div>
                  </div>
                );
              })}
              {!loading && (
                <div className="relative flex items-center gap-2.5">
                  <span className="absolute -left-[26px] top-0 flex items-center justify-center w-5 h-5 rounded-full bg-white dark:bg-[#212121]">
                    <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-500" />
                  </span>
                  <span className="text-xs text-zinc-500 dark:text-zinc-400">Concluído</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Indicador de "escrevendo" que fica abaixo do texto já streamado,
 * enquanto a resposta ainda está sendo gerada.
 */
export function StreamingIndicator() {
  return (
    <div className="flex items-center gap-2 mt-1 mb-4 text-sm text-zinc-400 dark:text-zinc-500">
      <motion.span
        animate={{ opacity: [0.45, 1, 0.45] }}
        transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
        className="flex"
      >
        <Sparkles className="w-4 h-4 text-emerald-500" />
      </motion.span>
      <span className="italic">Escrevendo resposta…</span>
    </div>
  );
}

export type { ToolEvent };
