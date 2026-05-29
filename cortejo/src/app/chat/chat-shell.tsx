"use client";

import { useState, useCallback, useTransition, useRef, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { Menu, X, Plus } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { fetchChats as fetchChatsAction, deleteChat as deleteChatAction, deleteAllChats as deleteAllChatsAction } from "@/lib/actions";
import { cn } from "@/lib/utils";
import ConversationMenu from "@/components/chat/conversation-menu";
import UserMenu from "@/components/chat/user-menu";
import Toast from "@/components/toast";
import { shareConversation } from "@/lib/share-chat-client";

type Chat = { id: string; titulo: string; updated_at: string };

function groupChatsByDate(chats: Chat[]): { label: string; chats: Chat[] }[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const sevenDaysAgo = new Date(today.getTime() - 7 * 86400000);
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 86400000);

  const groups: Record<string, Chat[]> = {};
  const order = ["Hoje", "Ontem", "Últimos 7 dias", "Últimos 30 dias", "Mais antigos"];

  for (const chat of chats) {
    const date = new Date(chat.updated_at);
    let label: string;
    if (date >= today) label = "Hoje";
    else if (date >= yesterday) label = "Ontem";
    else if (date >= sevenDaysAgo) label = "Últimos 7 dias";
    else if (date >= thirtyDaysAgo) label = "Últimos 30 dias";
    else label = "Mais antigos";

    if (!groups[label]) groups[label] = [];
    groups[label].push(chat);
  }

  return order.filter((l) => groups[l]).map((l) => ({ label: l, chats: groups[l] }));
}

export default function ChatShell({
  children,
  initialChats,
}: {
  children: React.ReactNode;
  initialChats: Chat[];
}) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isDesktopOpen, setIsDesktopOpen] = useState(true);
  const [chats, setChats] = useState<Chat[]>(initialChats);
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const pathname = usePathname();
  const [chatToDelete, setChatToDelete] = useState<string | null>(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [toast, setToast] = useState<{ message: string; kind: "success" | "error" } | null>(null);
  const toastTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [, startTransition] = useTransition();

  useEffect(() => () => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
  }, []);

  const flashToast = useCallback((message: string, kind: "success" | "error" = "success") => {
    setToast({ message, kind });
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = setTimeout(() => setToast(null), 4000);
  }, []);

  const handleShareChat = useCallback(async (chatId: string) => {
    const outcome = await shareConversation(chatId);
    if (outcome.kind === "copied") {
      flashToast("Link copiado. Qualquer pessoa com ele pode ver esta conversa.");
    } else if (outcome.kind === "error") {
      flashToast(outcome.message, "error");
    }
  }, [flashToast]);

  const refreshChats = useCallback(() => {
    startTransition(async () => {
      const data = await fetchChatsAction();
      setChats(data);
    });
  }, []);

  const lastPathname = useRef(pathname);
  if (pathname !== lastPathname.current) {
    lastPathname.current = pathname;
    refreshChats();
  }

  const handleDeleteChat = useCallback(async () => {
    if (!chatToDelete) return;
    startTransition(async () => {
      const result = await deleteChatAction(chatToDelete);
      if (result.ok) {
        setChats((prev) => prev.filter((c) => c.id !== chatToDelete));
        if (pathname === `/chat/${chatToDelete}`) {
          router.push("/chat");
        }
      }
      setChatToDelete(null);
    });
  }, [chatToDelete, pathname, router]);

  const handleDeleteAllConfirm = useCallback(async () => {
    startTransition(async () => {
      const result = await deleteAllChatsAction();
      if (result.ok) {
        setChats([]);
        if (pathname.startsWith("/chat/") && pathname !== "/chat") {
          router.push("/chat");
        }
      }
      setConfirmDeleteAll(false);
    });
  }, [pathname, router]);

  return (
    <div className="flex h-[100dvh] bg-white dark:bg-[#212121] overflow-hidden">
      <Toast message={toast?.message ?? null} kind={toast?.kind} />
      {}
      <AnimatePresence>
        {chatToDelete && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setChatToDelete(null)}
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm bg-white dark:bg-[#2f2f2f] rounded-2xl p-6 shadow-xl border border-zinc-200 dark:border-zinc-800"
            >
              <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
                Apagar conversa?
              </h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
                Esta ação não pode ser desfeita. A conversa será removida permanentemente.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setChatToDelete(null)}
                  className="px-4 py-2 text-sm font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeleteChat}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-full transition-colors"
                >
                  Apagar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {}
      <AnimatePresence>
        {confirmDeleteAll && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setConfirmDeleteAll(false)}
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm bg-white dark:bg-[#2f2f2f] rounded-2xl p-6 shadow-xl border border-zinc-200 dark:border-zinc-800"
            >
              <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
                Apagar todas as conversas?
              </h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
                Você está prestes a apagar {chats.length} {chats.length === 1 ? "conversa" : "conversas"}. Esta ação não pode ser desfeita.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setConfirmDeleteAll(false)}
                  className="px-4 py-2 text-sm font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeleteAllConfirm}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-full transition-colors"
                >
                  Apagar todas
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>


      {}
      <AnimatePresence>
        {isMobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsMobileOpen(false)}
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
          />
        )}
      </AnimatePresence>

      {}
      <aside
        className={cn(
          "fixed md:relative inset-y-0 left-0 z-50 h-full bg-[#f9f9f9] dark:bg-[#171717] transition-all duration-300 ease-in-out overflow-hidden",
          "w-[260px]",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          isDesktopOpen ? "md:w-[260px] md:opacity-100" : "md:w-0 md:opacity-0"
        )}
      >
        <div className="w-[260px] flex flex-col h-full">
          <div className="p-3 flex items-center justify-between">
            <Link
              href="/chat"
              onClick={() => setIsMobileOpen(false)}
              className="flex items-center justify-between w-full hover:bg-black/5 dark:hover:bg-white/5 p-2 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-2 font-medium text-sm">
                <div className="bg-black dark:bg-white text-white dark:text-black w-7 h-7 rounded-full flex items-center justify-center text-xs">M</div>
                Nova conversa
              </div>
              <Plus className="w-4 h-4" />
            </Link>
            <button
              onClick={() => setIsMobileOpen(false)}
              className="md:hidden p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
            {chats.length === 0 ? (
              <div className="text-xs text-zinc-400 dark:text-zinc-500 px-4 py-6 text-center">
                Nenhuma conversa ainda
              </div>
            ) : (
              groupChatsByDate(chats).map((group) => (
                <div key={group.label}>
                  <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 px-2 py-2">
                    {group.label}
                  </div>
                  {group.chats.map((chat) => {
                    const isActive = pathname === `/chat/${chat.id}`;
                    return (
                      <div
                        key={chat.id}
                        className={cn(
                          "group relative flex items-center gap-1 px-2 py-1.5 rounded-lg text-sm transition-colors",
                          isActive
                            ? "bg-black/5 dark:bg-white/10 text-zinc-900 dark:text-zinc-100 font-medium"
                            : "text-zinc-600 dark:text-zinc-300 hover:bg-black/5 dark:hover:bg-white/5"
                        )}
                      >
                        <Link
                          href={`/chat/${chat.id}`}
                          onClick={() => setIsMobileOpen(false)}
                          className="truncate flex-1 min-w-0 py-1"
                        >
                          {chat.titulo}
                        </Link>
                        <ConversationMenu
                          isActive={isActive}
                          onShare={() => handleShareChat(chat.id)}
                          onDelete={() => setChatToDelete(chat.id)}
                        />
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          <div className="p-3">
            <UserMenu
              email={user?.email}
              theme={theme}
              onToggleTheme={toggleTheme}
              onDeleteAll={() => setConfirmDeleteAll(true)}
              chatsCount={chats.length}
            />
          </div>
        </div>
      </aside>

      {}
      <main className="flex-1 flex flex-col min-w-0 relative">
        <header className="h-14 flex items-center justify-between px-3 absolute top-0 w-full z-10 bg-white/80 dark:bg-[#212121]/80 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (window.innerWidth >= 768) {
                  setIsDesktopOpen(!isDesktopOpen);
                } else {
                  setIsMobileOpen(true);
                }
              }}
              className="p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="font-semibold text-lg text-zinc-800 dark:text-zinc-200">Maracatu</span>
          </div>
        </header>

        <div className="flex-1 overflow-hidden relative pt-14">
          {children}
        </div>
      </main>
    </div>
  );
}
