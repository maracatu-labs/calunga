import { AlertOctagon, AlertTriangle, Info } from "lucide-react";

type Severidade = "critico" | "atencao" | "informativo" | undefined;

const CONFIG: Record<Exclude<Severidade, undefined>, {
  label: string;
  icon: typeof AlertOctagon;
  pill: string;
  bar: string;
}> = {
  critico: {
    label: "Crítico",
    icon: AlertOctagon,
    pill: "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-300",
    bar: "bg-red-500",
  },
  atencao: {
    label: "Atenção",
    icon: AlertTriangle,
    pill: "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-300",
    bar: "bg-amber-500",
  },
  informativo: {
    label: "Informativo",
    icon: Info,
    pill: "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300",
    bar: "bg-blue-500",
  },
};

export function SeveridadePill({ severidade }: { severidade: Severidade }) {
  const cfg = CONFIG[severidade ?? "informativo"];
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide px-2 py-0.5 rounded-full ${cfg.pill}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

export function severidadeBarColor(severidade: Severidade): string {
  return CONFIG[severidade ?? "informativo"].bar;
}
