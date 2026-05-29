import { ImageResponse } from "next/og";

// Default Open Graph image rendered at request-time by next/og. Applies to
// every route that does not provide its own opengraph-image.tsx. Output is
// PNG 1200x630, the size recommended by Facebook, X, Slack, WhatsApp etc.

export const alt = "Maracatu — controle social no ritmo do povo";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export const runtime = "edge";

export default async function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#0a0a0a",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 80,
          color: "white",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 9999,
              background: "white",
              color: "#0a0a0a",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 44,
              fontWeight: 700,
              fontFamily: "system-ui, -apple-system, sans-serif",
            }}
          >
            M
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: 36, fontWeight: 700, lineHeight: 1 }}>Maracatu</div>
            <div style={{ fontSize: 20, color: "#a1a1aa", marginTop: 8 }}>maracatu.org</div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.1 }}>
            Fiscalize o dinheiro público,
          </div>
          <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.1, color: "#e4e4e7" }}>
            no ritmo do povo.
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", color: "#a1a1aa", fontSize: 22 }}>
          <span>Controle social via chat com IA</span>
          <span>Câmara · Senado · Transparência · TSE</span>
        </div>
      </div>
    ),
    { ...size }
  );
}
