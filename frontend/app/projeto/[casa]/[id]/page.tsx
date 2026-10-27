import type { Metadata } from "next";

import { PaginaProjetoFederal, metadadosProjetoFederal } from "@/components/projeto-federal";

export async function generateMetadata({ params }: PageProps<"/projeto/[casa]/[id]">): Promise<Metadata> {
  const { casa, id } = await params;
  return metadadosProjetoFederal(casa, id);
}

export default function ProjetoPage({ params, searchParams }: PageProps<"/projeto/[casa]/[id]">) {
  return <PaginaProjetoFederal params={params} searchParams={searchParams} />;
}
