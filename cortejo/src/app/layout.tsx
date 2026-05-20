import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/lib/theme-context";
import { AuthProvider } from "@/lib/auth-context";
import { getSession } from "@/lib/actions";

export const metadata: Metadata = {
  title: "Maracatu — Controle social dos gastos públicos, no ritmo do povo",
  description: "Pergunte em linguagem natural como o dinheiro público está sendo gasto e receba respostas claras, com dados, fontes oficiais e alertas de irregularidades.",
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
      </head>
      <body className="min-h-screen">
        <ThemeProvider>
          <AuthProvider initialUser={user}>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
