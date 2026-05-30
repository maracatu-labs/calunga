"use client";

import Link from "next/link";
import { MessageSquare, Sparkles } from "lucide-react";
import ChatMessage from "@/components/chat/chat-message";
import AgentActivity, { parseToolEvents } from "@/components/chat/tool-activity";

type Message = { id: string; role: "user" | "model"; content: string; toolCalls?: unknown[] };
type SharedData = {
  chat: { id: string; title: string };
  messages: Message[];
} | null;

function stripSuggestions(content: string): string {
  const lines = content.trimEnd().split("\n");
  let cutIndex = lines.length;

  for (let i = lines.length - 1; i >= 0; i--) {
    const cleaned = lines[i].replace(/^[\s\-\d.*•►→#👉]+/, "").trim();
    if (cleaned.length > 10 && cleaned.endsWith("?")) {
      cutIndex = i;
    } else if (cutIndex < lines.length) {
      const isHeader = /^[\s#*]*(?:sugest|quer|pergunt|você|🤔|📌|💡|👉)/i.test(lines[i]);
      if (isHeader || lines[i].trim() === "") {
        cutIndex = i;
      } else {
        break;
      }
    }
  }

  return lines.slice(0, cutIndex).join("\n").trimEnd();
}

export default function SharedConversation({ data }: { data: SharedData }) {
  if (!data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white dark:bg-[#212121] text-zinc-900 dark:text-zinc-100 p-4">
        <MessageSquare className="w-12 h-12 text-zinc-400 dark:text-zinc-500 mb-4" />
        <h1 className="text-2xl font-semibold mb-2">Conversa não encontrada</h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-6 text-center max-w-md">
          Este link pode ter expirado ou a conversa não foi compartilhada publicamente.
        </p>
        <Link
          href="/login"
          className="px-6 py-3 bg-black dark:bg-white text-white dark:text-black rounded-full font-medium hover:opacity-80 transition-opacity"
        >
          Fiscalizar gastos públicos
        </Link>
      </div>
    );
  }

  const displayMessages = data.messages.map((m) => ({
    ...m,
    content: m.role !== "user" ? stripSuggestions(m.content) : m.content,
  }));

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-[#212121] text-zinc-900 dark:text-zinc-100">
      <header className="h-14 flex items-center justify-between px-4 sm:px-6 bg-white/80 dark:bg-[#212121]/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="bg-black dark:bg-white text-white dark:text-black w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold">M</div>
          <span className="font-semibold text-lg text-zinc-800 dark:text-zinc-200 hidden sm:inline">Maracatu</span>
          <span className="text-zinc-300 dark:text-zinc-700 hidden sm:inline">/</span>
          <span className="text-sm text-zinc-500 dark:text-zinc-400 truncate max-w-[150px] sm:max-w-xs">{data.chat.title}</span>
        </div>
        <Link
          href="/login"
          className="text-sm font-medium px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
        >
          Iniciar minha conversa
        </Link>
      </header>

      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-3xl mx-auto pt-6 pb-12">
          <div className="mb-10 flex items-start sm:items-center gap-3 p-4 sm:px-5 sm:py-4 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl border border-transparent dark:border-zinc-800 text-sm text-zinc-600 dark:text-zinc-300">
            <Sparkles className="w-5 h-5 text-zinc-500 dark:text-zinc-400 shrink-0 mt-0.5 sm:mt-0" />
            <p>
              Esta é uma conversa pública sobre gastos públicos, gerada pela <span className="font-semibold text-zinc-900 dark:text-zinc-100">Calunga</span>, a guardiã do dinheiro público do Maracatu.
              Os dados vêm de fontes oficiais do governo.
            </p>
          </div>

          {displayMessages.map((msg) => (
            <div key={msg.id}>
              {msg.role === "model" && (
                <AgentActivity events={parseToolEvents(msg.toolCalls)} status="done" />
              )}
              <ChatMessage role={msg.role} content={msg.content} />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
