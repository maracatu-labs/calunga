import type { Metadata } from "next";
import { fetchSharedChat } from "@/lib/actions";
import SharedConversation from "./shared-conversation";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const data = await fetchSharedChat(id);

  if (!data) {
    return { title: "Maracatu - Consulta não encontrada" };
  }

  const description = "Consulta pública sobre gastos públicos gerada pela Calunga, guardiã do dinheiro público do Maracatu.";

  return {
    title: `Maracatu - ${data.chat.title}`,
    description,
    openGraph: { title: `Maracatu - ${data.chat.title}`, description, type: "article" },
    twitter: { card: "summary", title: `Maracatu - ${data.chat.title}`, description },
  };
}

export default async function SharedPage({ params }: Props) {
  const { id } = await params;
  const data = await fetchSharedChat(id);
  return <SharedConversation data={data} />;
}
