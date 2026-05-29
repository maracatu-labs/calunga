"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useParams } from "next/navigation";
import { useChat } from "@ai-sdk/react";
import { motion } from "motion/react";
import { ArrowUp } from "lucide-react";
import { fetchChat } from "@/lib/actions";
import ChatMessage from "@/components/chat/chat-message";
import ToolActivity, { parseToolEvents, StreamingIndicator } from "@/components/chat/tool-activity";
import ChatErrorBoundary from "@/components/chat/chat-error-boundary";
import { useAutoScroll } from "@/lib/use-auto-scroll";

export default function ChatIdPage() {
  return (
    <ChatErrorBoundary>
      <ChatIdPageInner />
    </ChatErrorBoundary>
  );
}

function ChatIdPageInner() {
  const { id } = useParams<{ id: string }>();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [localInput, setLocalInput] = useState("");
  const loaded = useRef(false);
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

  const { messages, isLoading, append, setMessages, data, setData, error } = useChat({
    api: "/api/chat",
    body: { conversa_id: id },
    onResponse: () => {
      setFollowUps([]);
      resetScroll();
      scrollToBottom();
    },
    onFinish: (message) => {
      extractFollowUps(message.content);
      scrollToBottom();
    },
  });

  const toolEvents = parseToolEvents(data);

  useEffect(() => {
    scrollToBottom();
  }, [messages, toolEvents.length, scrollToBottom]);

  if (id && !loaded.current) {
    loaded.current = true;
    fetchChat(id).then((data) => {
      if (data && data.messages.length > 0) {
        const mapped = data.messages.map((m: any) => ({
          id: m.id,
          role: m.role === "model" ? "assistant" as const : "user" as const,
          content: m.content,
        }));
        setMessages(mapped);
        const lastMsg = data.messages[data.messages.length - 1];
        if (lastMsg) extractFollowUps(lastMsg.content);
      }
    }).catch(() => {});
  }

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

  return (
    <div className="flex flex-col h-full">
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
                {isModel && isLast && toolEvents.length > 0 && (
                  <ToolActivity events={toolEvents} loading={isLoading} />
                )}
                <ChatMessage
                  role={isModel ? "model" : "user"}
                  content={isModel ? stripSuggestions(msg.content) : msg.content}
                />
              </div>
            );
          })}

          {isLoading && messages.length > 0 && messages[messages.length - 1].role === "user" && (
            <ToolActivity events={toolEvents} loading />
          )}

          {isLoading && messages.length > 0 && messages[messages.length - 1].role === "assistant" && (
            <StreamingIndicator />
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
