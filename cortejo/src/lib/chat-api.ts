

import { cookies } from "next/headers";

const API_URL = process.env.API_URL || "http://api:8000";
const COOKIE_NAME = "maracatu_token";

export type ChatListItem = {
  id: string;
  titulo: string;
  updated_at: string;
};

export async function getChats(): Promise<ChatListItem[]> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!token) return [];
  const res = await fetch(`${API_URL}/v1/conversas`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return [];
  const data = await res.json();
  return (data.data || []) as ChatListItem[];
}
