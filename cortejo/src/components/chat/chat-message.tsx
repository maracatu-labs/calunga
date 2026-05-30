"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { useTypewriter } from "@/lib/use-typewriter";
import ChartRenderer from "./chart-renderer";

type MessageProps = {
  role: "user" | "model" | "assistant";
  content: string;
  streaming?: boolean;
};

const CHART_TYPES = new Set(["bar", "pie", "line"]);

function tryParseChart(children: any) {
  try {
    const text = String(children).trim();
    const config = JSON.parse(text);
    if (config.type && CHART_TYPES.has(config.type) && config.data && Array.isArray(config.data)) {
      return config as { type: "bar" | "pie" | "line"; data: any[]; xKey?: string; yKey?: string; title?: string };
    }
  } catch {

  }
  return null;
}

export default function ChatMessage({ role, content, streaming = false }: MessageProps) {
  const isUser = role === "user";
  const displayed = useTypewriter(content, streaming && !isUser);

  if (isUser) {
    return (
      <div className="flex w-full mb-6 justify-end">
        <div className="bg-[#f4f4f4] dark:bg-[#2f2f2f] text-zinc-900 dark:text-zinc-100 rounded-3xl px-5 py-2.5 max-w-[85%] md:max-w-[70%] break-words">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full mb-6 justify-start">
      <div className="flex w-full">
        <div className="flex-1 min-w-0 prose prose-sm md:prose-base dark:prose-invert max-w-none break-words">
          {!displayed ? null : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize]}
              components={{
              pre({ children }) {
                return <div className="not-prose">{children}</div>;
              },
              code({ inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                const lang = match?.[1];

                if (!inline && (lang === "chart" || lang === "json" || !lang)) {
                  const chart = tryParseChart(children);
                  if (chart) {
                    return <ChartRenderer config={chart} />;
                  }
                }

                return !inline ? (
                  <div className="relative bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-xl p-4 my-6 overflow-x-auto">
                    <pre className="bg-transparent p-0 m-0 border-none">
                      <code className={cn("text-sm font-mono text-zinc-800 dark:text-zinc-200", className)} {...props}>
                        {children}
                      </code>
                    </pre>
                  </div>
                ) : (
                  <code className="bg-[#f4f4f4] dark:bg-[#2f2f2f] px-1.5 py-0.5 rounded-md text-sm font-mono text-zinc-800 dark:text-zinc-200" {...props}>
                    {children}
                  </code>
                );
              },
              table({ children }) {
                return (
                  <div className="not-prose overflow-x-auto my-6 rounded-xl border border-zinc-200 dark:border-zinc-800">
                    <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800">
                      {children}
                    </table>
                  </div>
                );
              },
              th({ children }) {
                return <th className="px-4 py-3 bg-[#f9f9f9] dark:bg-[#171717] text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider whitespace-nowrap">{children}</th>;
              },
              td({ children }) {
                return <td className="px-4 py-3 text-sm text-zinc-900 dark:text-zinc-300 border-b border-zinc-100 dark:border-zinc-800/50 whitespace-nowrap">{children}</td>;
              },
            }}
          >
            {displayed}
          </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}
