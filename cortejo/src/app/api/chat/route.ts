import { cookies } from "next/headers";

const INTERNAL_API_URL = process.env.API_URL || "http://api:8000";
const COOKIE_NAME = "maracatu_token";

export async function POST(req: Request) {
  const body = await req.json();

  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value || "";

  const response = await fetch(`${INTERNAL_API_URL}/v1/chats`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      messages: body.messages,
      stream: true,
      ...(body.conversa_id && { conversa_id: body.conversa_id }),
    }),
  });

  if (!response.ok) {
    return new Response("Erro ao conectar com a API", {
      status: response.status,
    });
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const readable = new ReadableStream({
    async start(controller) {
      const reader = response.body?.getReader();
      if (!reader) {
        controller.close();
        return;
      }

      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();

            if (data === "[DONE]") {
              controller.enqueue(
                encoder.encode(`d:{"finishReason":"stop"}\n`)
              );
              controller.close();
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "text" && parsed.content) {
                controller.enqueue(
                  encoder.encode(`0:${JSON.stringify(parsed.content)}\n`)
                );
              } else if (
                parsed.type === "tool_start" ||
                parsed.type === "tool_end"
              ) {

                controller.enqueue(
                  encoder.encode(`2:${JSON.stringify([parsed])}\n`)
                );
              } else if (parsed.type === "error") {
                controller.enqueue(
                  encoder.encode(`3:${JSON.stringify(parsed.content || "Erro no stream")}\n`)
                );
              }
            } catch {

            }
          }
        }
      } catch (error) {
        console.error("Stream error:", error);
      } finally {
        if (!controller.desiredSize) return;
        controller.enqueue(
          encoder.encode(`d:{"finishReason":"stop"}\n`)
        );
        controller.close();
      }
    },
  });

  const conversaId = response.headers.get("X-Conversa-Id") || "";

  return new Response(readable, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "x-vercel-ai-data-stream": "v1",
      ...(conversaId && { "X-Conversa-Id": conversaId }),
    },
  });
}
