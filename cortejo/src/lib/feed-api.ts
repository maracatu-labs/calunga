

import type { FeedEvento } from "./actions";

const API_URL = process.env.API_URL || "http://api:8000";

export async function getFeed(params?: {
  tipo?: string;
  categoria?: string;
  origem?: string;
  limit?: number;
  offset?: number;
}): Promise<{ eventos: FeedEvento[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.categoria) query.set("categoria", params.categoria);
  if (params?.origem) query.set("origem", params.origem);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const res = await fetch(`${API_URL}/v1/feed?${query}`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) return { eventos: [], total: 0 };
  return await res.json();
}

export async function getFeedEvento(id: number): Promise<FeedEvento | null> {
  const res = await fetch(`${API_URL}/v1/feed/${id}`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) return null;
  return await res.json();
}
