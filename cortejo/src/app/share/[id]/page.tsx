import { notFound } from "next/navigation";
import { fetchSharedChat } from "@/lib/actions";
import SharedConversation from "./shared-conversation";
import type { Metadata } from "next";

type Props = { params: Promise<{ id: string }> };

const SITE = "https://maracatu.org";

function buildDescription(messages: { content: string; role: string }[]): string {
  // First user prompt makes for a more meaningful description than a static
  // "shared Calunga consultation" line. Fall back to the static text if the
  // conversation has no user message yet.
  const firstUser = messages.find((m) => m.role === "user");
  if (firstUser?.content) {
    const cleaned = firstUser.content.replace(/\s+/g, " ").trim();
    return cleaned.length > 157 ? `${cleaned.slice(0, 157)}...` : cleaned;
  }
  return "Conversa pública sobre gastos públicos brasileiros gerada pela Calunga.";
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const data = await fetchSharedChat(id);

  if (!data) {
    return {
      title: "Maracatu - Conversa não encontrada",
      robots: { index: false, follow: false },
    };
  }

  const description = buildDescription(data.messages);
  const title = `Maracatu - ${data.chat.title}`;
  const url = `${SITE}/share/${id}`;

  return {
    title,
    description,
    // Shared conversations are private-by-design (only accessible via the
    // direct link). Tell search engines explicitly not to index them so a
    // stray social-graph crawl does not surface them.
    robots: { index: false, follow: false },
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      url,
      title,
      description,
      siteName: "Maracatu",
      locale: "pt_BR",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}

export default async function SharedPage({ params }: Props) {
  const { id } = await params;
  const data = await fetchSharedChat(id);
  if (!data) notFound();

  const description = buildDescription(data.messages);
  const url = `${SITE}/share/${id}`;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: data.chat.title,
    description,
    url,
    inLanguage: "pt-BR",
    isAccessibleForFree: true,
    publisher: {
      "@type": "Organization",
      name: "Maracatu",
      url: SITE,
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <SharedConversation data={data} />
    </>
  );
}
