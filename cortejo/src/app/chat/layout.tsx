import { getChats } from "@/lib/chat-api";
import ChatShell from "./chat-shell";

export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const initialChats = await getChats();
  return <ChatShell initialChats={initialChats}>{children}</ChatShell>;
}
