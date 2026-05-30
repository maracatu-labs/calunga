"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useChat } from "@ai-sdk/react";
import { motion } from "motion/react";
import { ArrowUp, Sparkles } from "lucide-react";
import ChatMessage from "@/components/chat/chat-message";
import AgentActivity, { parseToolEvents, DotRingLoader } from "@/components/chat/tool-activity";
import ChatErrorBoundary from "@/components/chat/chat-error-boundary";
import { useAutoScroll } from "@/lib/use-auto-scroll";

const SUGGESTIONS = [
  "Quanto o deputado Albuquerque gastou em 2024?",
  "Quais deputados mais gastaram com combustíveis em 2025?",
  "Quais despesas foram sinalizadas com CNPJ inválido?",
  "Ranking dos 10 deputados que mais gastaram em 2024"
];

export default function ChatPage() {
  return (
    <ChatErrorBoundary>
      <ChatPageInner />
    </ChatErrorBoundary>
  );
}

function ChatPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [localInput, setLocalInput] = useState("");
  const conversaIdRef = useRef<string | null>(null);
  const autoSubmitted = useRef(false);
  const { scrollContainerRef, handleScroll, scrollToBottom, resetScroll } = useAutoScroll();

  const extractFollowUps = useCallback((content: string) => {

    const match = content.match(/^[\s*#]*sugest(?:[ãa]o|[õo]es)\s*:?\s*$/im);
    if (!match || match.index === undefined) {
      setFollowUps([]);
      return;
    }
    const after = content.slice(match.index + match[0].length);
    const questions = after
      .split("\n")
      .map((l) => l.replace(/^[\s\-\d.*•►→#👉]+/, "").trim())
      .filter((l) => l.length > 10 && l.endsWith("?"));
    setFollowUps(questions.slice(0, 4));
  }, []);

  const { messages, isLoading, append, data, setData, error } = useChat({
    api: "/api/chat",
    onResponse: (response) => {
      setFollowUps([]);
      resetScroll();
      scrollToBottom();
      const id = response.headers.get("X-Conversa-Id");
      if (id) {
        conversaIdRef.current = id;
      }
    },
    onFinish: (message) => {
      extractFollowUps(message.content);
      scrollToBottom();
      if (conversaIdRef.current) {
        const id = conversaIdRef.current;
        conversaIdRef.current = null;
        router.push(`/chat/${id}`);
      }
    },
  });

  const toolEvents = parseToolEvents(data);

  useEffect(() => {
    scrollToBottom();
  }, [messages, toolEvents.length, scrollToBottom]);

  const stripSuggestions = (content: string) => {

    const match = content.match(/^[\s*#]*sugest(?:[ãa]o|[õo]es)\s*:?\s*$/im);
    if (!match || match.index === undefined) return content.trimEnd();
    return content.slice(0, match.index).trimEnd();
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleSubmit = async (e?: React.FormEvent, textOverride?: string) => {
    e?.preventDefault();
    const text = textOverride || localInput;
    if (!text.trim() || isLoading) return;

    setLocalInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setFollowUps([]);
    resetScroll();
    setData([]);

    append({ role: "user", content: text });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (autoSubmitted.current) return;
    const q = searchParams.get("q");
    if (q && q.trim()) {
      autoSubmitted.current = true;
      setData([]);
      append({ role: "user", content: q });
    }
  }, [searchParams, append, setData]);

  return (
    <div className="flex flex-col h-full">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center max-w-3xl w-full mx-auto flex flex-col items-center"
          >
            <div className="w-16 h-16 bg-black dark:bg-white rounded-full flex items-center justify-center mb-6 shadow-sm">
              <Sparkles className="w-8 h-8 text-white dark:text-black" />
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
              Pergunte sobre gastos públicos
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">
              Sou a Calunga, guardiã do dinheiro público. Pergunte sobre qualquer político brasileiro.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
              {SUGGESTIONS.map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => handleSubmit(undefined, suggestion)}
                  className="text-left p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#212121] hover:bg-zinc-50 dark:hover:bg-[#2f2f2f] transition-colors text-sm text-zinc-600 dark:text-zinc-300 shadow-sm"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </motion.div>
        </div>
      ) : (
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto scroll-smooth"
        >
          <div className="max-w-3xl w-full mx-auto px-4 md:px-6 pt-6 pb-6">
            {messages.map((msg, i) => {
              const isModel = msg.role === "assistant";
              const isLast = i === messages.length - 1;
              return (
                <div key={msg.id}>
                  {isModel && isLast && (
                    <AgentActivity events={toolEvents} status={isLoading ? "responding" : "done"} />
                  )}
                  <ChatMessage
                    role={isModel ? "model" : "user"}
                    content={isModel ? stripSuggestions(msg.content) : msg.content}
                  />
                  {isModel && isLast && isLoading && <DotRingLoader />}
                </div>
              );
            })}

            {isLoading && messages.length > 0 && messages[messages.length - 1].role === "user" && (
              <>
                <AgentActivity events={toolEvents} status="thinking" />
                <DotRingLoader />
              </>
            )}

            {error && (
              <div className="my-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/40 text-sm text-red-800 dark:text-red-200">
                Erro ao processar resposta: {error.message || "falha no stream"}. Tente enviar a pergunta novamente.
              </div>
            )}

            {messages.length > 0 && followUps.length > 0 && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full mt-2 mb-6"
              >
                {followUps.map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(undefined, suggestion)}
                    className="text-left p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#212121] hover:bg-zinc-50 dark:hover:bg-[#2f2f2f] transition-colors text-sm text-zinc-600 dark:text-zinc-300 shadow-sm"
                  >
                    {suggestion}
                  </button>
                ))}
              </motion.div>
            )}

            <div className="h-4" />
          </div>
        </div>
      )}

      <div className="w-full bg-gradient-to-t from-white via-white to-transparent dark:from-[#212121] dark:via-[#212121] dark:to-transparent pt-2 pb-4 md:pb-6 px-4 flex justify-center shrink-0">
        <div className="max-w-3xl w-full">
          <div className="relative flex items-end w-full bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-[24px] border border-transparent focus-within:border-zinc-300 dark:focus-within:border-zinc-600 transition-colors shadow-sm">
            <textarea
              ref={textareaRef}
              value={localInput}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Pergunte sobre gastos públicos..."
              className="w-full bg-transparent border-none focus:ring-0 focus:outline-none resize-none py-3.5 pl-5 pr-12 text-zinc-900 dark:text-zinc-100 max-h-[200px] overflow-y-auto"
              rows={1}
              style={{ minHeight: "52px" }}
            />
            <button
              onClick={() => handleSubmit()}
              disabled={!localInput.trim() || isLoading}
              className="absolute right-2 bottom-2 p-2 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 disabled:opacity-30 disabled:hover:opacity-30 transition-opacity"
            >
              <ArrowUp className="w-4 h-4 stroke-[3]" />
            </button>
          </div>
          <div className="text-center mt-2">
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              A Calunga usa dados oficiais, mas pode cometer erros. Verifique nas fontes oficiais.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
