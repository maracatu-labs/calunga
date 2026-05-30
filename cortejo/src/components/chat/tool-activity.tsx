"use client";

import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle, Loader2, Terminal, Clock, CheckCircle2, ChevronDown } from "lucide-react";

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

/** Fase do agente, derivada do estado do stream pela página. */
type AgentStatus = "thinking" | "responding" | "done";

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

/**
 * Texto dinâmico do cabeçalho. Muda em tempo real conforme o agente avança,
 * dando um feedback fluido do que está acontecendo agora.
 */
function headerLabel(status: AgentStatus, calls: ToolCall[]): string {
  if (status !== "thinking") {
    const n = calls.length;
    return `Consultei ${n} ${n === 1 ? "fonte oficial" : "fontes oficiais"}`;
  }
  const running = calls.find((c) => c.status === "running");
  if (running) return (TOOL_LABELS[running.tool] || running.tool) + "…";
  if (calls.length === 0) return "Pensando…";
  return "Reunindo as fontes…";
}

/** Ícone da esquerda de cada nó do trilho. Mascara a linha com o bg da página. */
function RailNode({ children }: { children: React.ReactNode }) {
  return (
    <span className="absolute -left-[30px] top-0 flex items-center justify-center w-6 h-6 bg-white dark:bg-[#212121]">
      {children}
    </span>
  );
}

function ToolIcon({ status }: { status: ToolCall["status"] }) {
  if (status === "running") return <Loader2 className="w-4 h-4 animate-spin text-zinc-400 dark:text-zinc-500" />;
  if (status === "error") return <AlertTriangle className="w-4 h-4 text-red-500" />;
  return <Terminal className="w-4 h-4 text-zinc-400 dark:text-zinc-500" />;
}

/**
 * Loader de bolinhas em anel (estilo claude.ai), na cor da marca (emerald).
 * Um anel de pontos com opacidade graduada gira continuamente, criando o
 * efeito de "cometa". Fica abaixo da resposta enquanto ela é gerada.
 */
export function DotRingLoader() {
  const dots = Array.from({ length: 12 });
  return (
    <motion.div
      aria-label="Gerando resposta"
      role="status"
      className="relative w-5 h-5 my-3"
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 1.1, ease: "linear" }}
    >
      {dots.map((_, i) => (
        <span
          key={i}
          className="absolute left-1/2 top-1/2 w-[3px] h-[3px] rounded-full bg-emerald-500"
          style={{
            transform: `rotate(${i * 30}deg) translateY(-8px)`,
            transformOrigin: "center",
            marginLeft: "-1.5px",
            marginTop: "-1.5px",
            opacity: 0.15 + (i / dots.length) * 0.85,
          }}
        />
      ))}
    </motion.div>
  );
}

/**
 * Atividade da Calunga, fixada sempre acima da resposta da LLM.
 *
 * - Cabeçalho com texto dinâmico ("Pensando" -> nome da tool atual -> resumo),
 *   que muda em tempo real para dar feedback fluido.
 * - Dropdown colapsado por padrão (mesmo durante o loading) com a timeline de
 *   raciocínio + tools consultadas. O usuário abre/fecha pelo chevron.
 *
 * Não há cadeia de raciocínio real do modelo: o nó "Pensando" é um indicador
 * de fase honesto (interpretação da pergunta), não texto gerado pela LLM.
 *
 * O loader de geração da resposta (DotRingLoader) é separado e fica abaixo
 * da mensagem, não dentro deste componente.
 */
export default function AgentActivity({
  events,
  status,
}: {
  events: ToolEvent[];
  status: AgentStatus;
}) {
  const calls = useMemo(() => buildCalls(events), [events]);
  const [expanded, setExpanded] = useState(false);

  const n = calls.length;
  const thinking = status === "thinking";
  const toolsDone = status !== "thinking";

  // Sem nenhuma tool fora da fase de "pensando": nada estrutural a mostrar.
  if (!thinking && n === 0) return null;

  const label = headerLabel(status, calls);
  const hasTimeline = n > 0;

  return (
    <div className="mb-4">
      <button
        type="button"
        onClick={() => hasTimeline && setExpanded((v) => !v)}
        aria-expanded={expanded}
        disabled={!hasTimeline}
        className="group flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400 disabled:cursor-default"
      >
        <motion.span
          key={label}
          initial={{ opacity: 0, y: 2 }}
          animate={
            thinking
              ? { opacity: [0.55, 1, 0.55], y: 0 }
              : { opacity: 1, y: 0 }
          }
          transition={
            thinking
              ? { opacity: { repeat: Infinity, duration: 1.6, ease: "easeInOut" }, y: { duration: 0.2 } }
              : { duration: 0.2 }
          }
          className="font-medium"
        >
          {label}
        </motion.span>
        {hasTimeline && (
          <ChevronDown
            className={
              "w-4 h-4 transition-transform group-hover:text-zinc-700 dark:group-hover:text-zinc-200 " +
              (expanded ? "rotate-180" : "")
            }
          />
        )}
      </button>

      <AnimatePresence initial={false}>
        {expanded && hasTimeline && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="relative mt-3 ml-[15px] pl-[30px]">
              <div className="absolute left-[11px] top-2 bottom-2 w-px bg-zinc-200 dark:bg-zinc-800" />

              {/* Nó de raciocínio (indicador de fase, sem CoT real) */}
              <div className="relative flex items-start pb-5">
                <RailNode>
                  <Clock className="w-4 h-4 text-zinc-400 dark:text-zinc-500" />
                </RailNode>
                <span className="text-sm text-zinc-700 dark:text-zinc-200">
                  {thinking ? "Interpretando sua pergunta" : "Interpretei sua pergunta"}
                </span>
              </div>

              {/* Nós de tools */}
              {calls.map((call) => {
                const toolLabel = TOOL_LABELS[call.tool] || call.tool;
                const chip = summarizeArgs(call.args);
                return (
                  <div key={call.id} className="relative flex flex-col pb-5">
                    <div className="flex items-start">
                      <RailNode>
                        <ToolIcon status={call.status} />
                      </RailNode>
                      <span className="text-sm text-zinc-500 dark:text-zinc-400">{toolLabel}</span>
                    </div>
                    {chip && (
                      <span className="mt-1.5 self-start px-2 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-xs text-zinc-500 dark:text-zinc-400 max-w-[280px] truncate">
                        {chip}
                      </span>
                    )}
                    {call.status === "error" && call.error && (
                      <span className="mt-1.5 text-xs text-red-500">{call.error.slice(0, 120)}</span>
                    )}
                  </div>
                );
              })}

              {/* Nó final */}
              {toolsDone && (
                <div className="relative flex items-center">
                  <RailNode>
                    <CheckCircle2 className="w-4 h-4 text-zinc-400 dark:text-zinc-500" />
                  </RailNode>
                  <span className="text-sm text-zinc-500 dark:text-zinc-400">Concluído</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export type { ToolEvent };
