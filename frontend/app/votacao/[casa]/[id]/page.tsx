import type { Metadata } from "next";

import { PaginaVotacao, metadadosVotacao } from "@/components/votacao-explicador";

export async function generateMetadata({ params }: PageProps<"/votacao/[casa]/[id]">): Promise<Metadata> {
  const { casa, id } = await params;
  return metadadosVotacao(casa, id);
}

export default function VotacaoPage({ params, searchParams }: PageProps<"/votacao/[casa]/[id]">) {
  return <PaginaVotacao params={params} searchParams={searchParams} />;
}
