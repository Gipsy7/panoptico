import type { Metadata } from "next";

import { PaginaVotacaoLocal, metadadosVotacaoLocal } from "@/components/projeto-local";

export async function generateMetadata({ params }: PageProps<"/votacao/local/[id]">): Promise<Metadata> {
  const { id } = await params;
  return metadadosVotacaoLocal(id);
}

export default function VotacaoLocalPage({ params }: PageProps<"/votacao/local/[id]">) {
  return <PaginaVotacaoLocal params={params} />;
}
