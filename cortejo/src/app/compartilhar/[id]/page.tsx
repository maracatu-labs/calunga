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
    return { title: "Consulta não encontrada | Maracatu" };
  }

  const description = "Consulta pública sobre gastos públicos gerada pela Calunga, guardiã do dinheiro público do Maracatu.";

  return {
    title: `${data.chat.title} | Maracatu`,
    description,
    openGraph: { title: `${data.chat.title} | Maracatu`, description, type: "article" },
    twitter: { card: "summary", title: `${data.chat.title} | Maracatu`, description },
  };
}

export default async function SharedPage({ params }: Props) {
  const { id } = await params;
  const data = await fetchSharedChat(id);
  return <SharedConversation data={data} />;
}
