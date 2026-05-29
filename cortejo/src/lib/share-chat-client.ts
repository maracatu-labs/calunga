"use client";

import { shareChat } from "@/lib/actions";

export type ShareOutcome =
  | { kind: "shared" }
  | { kind: "copied" }
  | { kind: "error"; message: string };

// Drives the public-share flow from any client component. Returns an outcome
// the caller can use to surface a toast. Passes only `{ url }` to
// navigator.share because the native sheet on macOS / iOS concatenates every
// field when the user picks "Copy"; URL-only keeps the clipboard clean
// while rich previews still come from our OG metadata.
export async function shareConversation(chatId: string): Promise<ShareOutcome> {
  const result = await shareChat(chatId);
  if (!result.ok) {
    return { kind: "error", message: "Não foi possível gerar o link agora. Tente novamente." };
  }

  const url = `${window.location.origin}/compartilhar/${chatId}`;

  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share({ url });
      return { kind: "shared" };
    } catch {
      // Web Share rejected (user cancelled or platform error) — fall through to copy.
    }
  }

  try {
    await navigator.clipboard.writeText(url);
    return { kind: "copied" };
  } catch {
    return { kind: "error", message: "Não foi possível copiar o link. Selecione manualmente." };
  }
}
