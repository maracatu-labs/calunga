"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";
import { useTheme } from "@/lib/theme-context";

type ChartProps = {
  config: {
    type: "bar" | "pie" | "line";
    data: any[];
    xKey?: string;
    yKey?: string;
    title?: string;
    colors?: string[];
  };
};

const DEFAULT_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

const MESES: Record<string, string> = {
  "Jan": "Janeiro", "Fev": "Fevereiro", "Mar": "Março", "Abr": "Abril",
  "Mai": "Maio", "Jun": "Junho", "Jul": "Julho", "Ago": "Agosto",
  "Set": "Setembro", "Out": "Outubro", "Nov": "Novembro", "Dez": "Dezembro",
  "1": "Janeiro", "2": "Fevereiro", "3": "Março", "4": "Abril",
  "5": "Maio", "6": "Junho", "7": "Julho", "8": "Agosto",
  "9": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro",
};

function expandMonth(label: string): string {
  return MESES[label] || label;
}

function formatBRL(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatYAxis(value: number): string {
  if (value >= 1_000_000) return `R$ ${(value / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}M`;
  if (value >= 1_000) return `R$ ${(value / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}k`;
  return `R$ ${value.toLocaleString("pt-BR")}`;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 px-3 py-2 rounded-lg text-sm shadow-lg">
      <p className="font-medium">{expandMonth(String(label))}</p>
      <p>{formatBRL(payload[0].value)}</p>
    </div>
  );
}

function CustomPieTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 px-3 py-2 rounded-lg text-sm shadow-lg">
      <p className="font-medium">{payload[0].name}</p>
      <p>{formatBRL(payload[0].value)}</p>
    </div>
  );
}

export default function ChartRenderer({ config }: ChartProps) {
  const { type, data, xKey = "name", yKey = "value", title, colors = DEFAULT_COLORS } = config;
  const { theme } = useTheme();

  if (!data || data.length === 0) return null;

  const isDark = theme === "dark";
  const textColor = isDark ? "#a1a1aa" : "#71717a";
  const gridColor = isDark ? "#3f3f46" : "#e4e4e7";

  const chartData = data.map((d) => ({
    ...d,
    [xKey]: expandMonth(String(d[xKey])),
  }));

  return (
    <div className="w-full my-6 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-xl border border-zinc-200 dark:border-zinc-800 p-4 shadow-sm">
      {title && (
        <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-3">{title}</p>
      )}
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          {type === "bar" ? (
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: textColor }} axisLine={false} tickLine={false} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} tickFormatter={formatYAxis} width={70} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: isDark ? "#3f3f46" : "#e4e4e7" }} />
              <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : type === "pie" ? (
            <PieChart>
              <Tooltip content={<CustomPieTooltip />} />
              <Pie data={chartData} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={80} fill="#8884d8">
                {chartData.map((_entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} stroke={isDark ? "#2f2f2f" : "#f4f4f4"} strokeWidth={2} />
                ))}
              </Pie>
            </PieChart>
          ) : type === "line" ? (
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: textColor }} axisLine={false} tickLine={false} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} tickFormatter={formatYAxis} width={70} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey={yKey} stroke={colors[0]} strokeWidth={2} dot={{ r: 4, fill: colors[0], strokeWidth: 0 }} activeDot={{ r: 6, strokeWidth: 0 }} />
            </LineChart>
          ) : (
            <div className="flex items-center justify-center h-full text-zinc-500">Tipo de gráfico não suportado</div>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
