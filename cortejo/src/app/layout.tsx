import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ThemeProvider } from "@/lib/theme-context";
import { AuthProvider } from "@/lib/auth-context";
import { getSession } from "@/lib/actions";
import ServiceStatusBanner from "@/components/service-status-banner";

const SITE = "https://maracatu.org";
const SITE_TITLE = "Maracatu - Controle social dos gastos públicos, no ritmo do povo";
const SITE_DESCRIPTION = "Pergunte em linguagem natural como o dinheiro público está sendo gasto e receba respostas claras, com dados, fontes oficiais e alertas de irregularidades.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  applicationName: "Maracatu",
  authors: [{ name: "Maracatu Labs", url: SITE }],
  keywords: [
    "transparência",
    "gastos públicos",
    "controle social",
    "CEAP",
    "deputados",
    "senadores",
    "Câmara",
    "Senado",
    "Portal da Transparência",
    "Brasil",
    "fiscalização",
  ],
  openGraph: {
    type: "website",
    url: SITE,
    siteName: "Maracatu",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    locale: "pt_BR",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
  alternates: {
    canonical: SITE,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Resize the layout when the soft keyboard opens (Android Chrome) so the
  // chat input stays above it instead of being covered.
  interactiveWidget: "resizes-content",
};

const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE}/#organization`,
      name: "Maracatu",
      url: SITE,
      logo: `${SITE}/opengraph-image`,
      description: "Plataforma open source de controle social dos gastos públicos brasileiros via chat com IA.",
      sameAs: ["https://github.com/maracatu-labs"],
    },
    {
      "@type": "WebSite",
      "@id": `${SITE}/#website`,
      url: SITE,
      name: "Maracatu",
      description: SITE_DESCRIPTION,
      inLanguage: "pt-BR",
      publisher: { "@id": `${SITE}/#organization` },
    },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const user = await getSession();

  return (
    <html lang="pt-BR" className="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=document.cookie.match(/(?:^|; )maracatu_theme=(dark|light)/);if((t?t[1]:"dark")==="dark")document.documentElement.classList.add("dark");else document.documentElement.classList.remove("dark")}catch(e){}})()`,
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
      </head>
      <body className="min-h-screen">
        <ThemeProvider>
          <AuthProvider initialUser={user}>
            <ServiceStatusBanner />
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
