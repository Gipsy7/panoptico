import type { Metadata } from "next";

import { PaginaProjetoLocal, metadadosProjetoLocal } from "@/components/projeto-local";

export async function generateMetadata({ params }: PageProps<"/projeto/local/[id]">): Promise<Metadata> {
  const { id } = await params;
  return metadadosProjetoLocal(id);
}

export default function ProjetoLocalPage({ params }: PageProps<"/projeto/local/[id]">) {
  return <PaginaProjetoLocal params={params} />;
}
