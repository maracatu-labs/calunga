"use server";

import { cookies } from "next/headers";

const API_URL = process.env.API_URL || "http://api:8000";
const COOKIE_NAME = "maracatu_token";
const COOKIE_MAX_AGE = 7 * 24 * 60 * 60;

async function getToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(COOKIE_NAME)?.value ?? null;
}

export async function sendMagicLink(email: string) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/v1/auth/magic-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  } catch {
    return { ok: false, status: 0, error: "Sem conexão. Verifique sua internet e tente novamente." };
  }

  if (res.ok) return { ok: true as const, status: res.status };

  let error = "Não foi possível enviar o link. Tente novamente em alguns instantes.";
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") {
      error = detail;
    } else if (detail && typeof detail === "object") {
      if (typeof detail.erro === "string") error = detail.erro;
      else if (Array.isArray(detail) && detail[0]?.msg) error = String(detail[0].msg);
    }
  } catch {
    // body was not JSON; keep the generic message
  }

  return { ok: false as const, status: res.status, error };
}

export async function verifyMagicLink(token: string) {
  const res = await fetch(`${API_URL}/v1/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) return { error: true as const };
  const data = await res.json() as { token: string; user: { id: string; email: string } };

  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, data.token, {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE !== "false",
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE,
  });

  return { user: data.user };
}

export async function getSession() {
  const token = await getToken();
  if (!token) return null;

  const res = await fetch(`${API_URL}/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.user as { id: string; email: string };
}

export async function fetchChats() {
  const token = await getToken();
  if (!token) return [];
  const res = await fetch(`${API_URL}/v1/conversas`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return (data.data || []) as { id: string; titulo: string; updated_at: string }[];
}

export async function fetchChat(chatId: string) {
  const token = await getToken();
  if (!token) return null;
  const res = await fetch(`${API_URL}/v1/conversas/${chatId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return {
    chat: { id: data.id, title: data.titulo },
    messages: (data.mensagens || []).map((m: any) => ({
      id: m.id?.toString() || crypto.randomUUID(),
      role: m.role === "assistant" ? "model" : m.role,
      content: m.content,
    })),
  };
}

export async function deleteChat(chatId: string) {
  const token = await getToken();
  if (!token) return { ok: false };
  const res = await fetch(`${API_URL}/v1/conversas/${chatId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return { ok: res.ok };
}

export async function deleteAllChats() {
  const token = await getToken();
  if (!token) return { ok: false as const, deleted: 0 };
  const res = await fetch(`${API_URL}/v1/conversas`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return { ok: false as const, deleted: 0 };
  const data = await res.json() as { ok: boolean; deleted: number };
  return { ok: true as const, deleted: data.deleted ?? 0 };
}

export async function shareChat(chatId: string) {
  const token = await getToken();
  if (!token) return { ok: false };
  const res = await fetch(`${API_URL}/v1/conversas/${chatId}/compartilhar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return { ok: res.ok };
}

export type FeedLink = {
  label: string;
  url: string;
  tipo: "fonte_oficial" | "documento" | "consulta" | "perfil" | "processo";
};

export type FeedAtor = {
  nome: string;
  papel?: string | null;
  partido?: string | null;
  uf?: string | null;
  foto_url?: string | null;
  id_externo?: string | null;
};

export type FeedAcao = {
  verbo: string;
  descricao: string;
  valor?: number | null;
  valor_formatado?: string | null;
  data?: string | null;
  local?: string | null;
};

export type FeedObjeto = {
  tipo: string;
  nome?: string | null;
  identificador?: string | null;
  identificador_formatado?: string | null;
  detalhes?: Record<string, any>;
};

export type FeedEvidencia = {
  classificador?: string | null;
  probabilidade?: number | null;
  motivo_humano?: string | null;
  criterios?: string[];
};

export type FeedContexto = {
  comparacao_historica?: string | null;
  ranking?: string | null;
  percentual_cota?: number | null;
  alertas?: string[];
};

export type FeedDadosRicos = {
  ator?: FeedAtor | null;
  acao?: FeedAcao | null;
  objeto?: FeedObjeto | null;
  evidencia?: FeedEvidencia | null;
  contexto?: FeedContexto | null;
  links?: FeedLink[];
  severidade?: "critico" | "atencao" | "informativo";
  versao_contrato?: number;
  [key: string]: any;
};

export type FeedEvento = {
  id: number;
  tipo: string;
  categoria: string;
  origem: string;
  titulo: string;
  descricao: string;
  dados: FeedDadosRicos;
  relevancia: number;
  created_at: string;
  updated_at?: string;
  referencia_tipo?: string | null;
  referencia_id?: number | null;
};

export async function fetchFeed(params?: {
  tipo?: string;
  categoria?: string;
  origem?: string;
  limit?: number;
  offset?: number;
}) {
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
  return await res.json() as {
    eventos: FeedEvento[];
    total: number;
  };
}

export async function fetchFeedEvento(id: number): Promise<FeedEvento | null> {
  const res = await fetch(`${API_URL}/v1/feed/${id}`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) return null;
  return await res.json() as FeedEvento;
}

export async function fetchSharedChat(chatId: string) {
  const res = await fetch(`${API_URL}/v1/share/${chatId}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  const data = await res.json();
  return {
    chat: { id: data.id, title: data.titulo },
    messages: (data.mensagens || []).map((m: any) => ({
      id: m.id?.toString() || crypto.randomUUID(),
      role: m.role,
      content: m.content,
    })),
  };
}
