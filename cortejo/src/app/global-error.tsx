"use client";

// Last-resort error boundary. Replaces the root layout when even the layout
// crashes (e.g. server-side issue serializing user). Must be self-contained:
// cannot rely on app/layout or theme/auth context.

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {

  console.error("[app/global-error]", error);
  return (
    <html lang="pt-BR">
      <body style={{ margin: 0, padding: 0, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", background: "#212121", color: "#fff" }}>
        <main style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "24px", textAlign: "center" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "8px" }}>Maracatu está indisponível no momento</h1>
          <p style={{ fontSize: "0.875rem", color: "#a1a1aa", maxWidth: "28rem", marginBottom: "24px" }}>
            Não conseguimos carregar a página. Tente recarregar em alguns instantes. Se o problema persistir, é possível que estejamos em manutenção.
          </p>
          <button
            onClick={reset}
            style={{ padding: "10px 24px", borderRadius: "9999px", background: "#fff", color: "#000", border: "none", fontSize: "0.875rem", fontWeight: 500, cursor: "pointer" }}
          >
            Tentar de novo
          </button>
          {error.digest && (
            <p style={{ fontSize: "0.75rem", color: "#71717a", marginTop: "16px" }}>
              Código: {error.digest}
            </p>
          )}
        </main>
      </body>
    </html>
  );
}
