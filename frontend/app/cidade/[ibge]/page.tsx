import type { Metadata } from "next";

import { DicaPagina } from "@/components/dica-pagina";
import { PaginaCidade, metadadosCidade } from "@/components/cidade-dinheiro";

export async function generateMetadata({ params }: PageProps<"/cidade/[ibge]">): Promise<Metadata> {
  const { ibge } = await params;
  return metadadosCidade(ibge);
}

export default function CidadePage({ params }: PageProps<"/cidade/[ibge]">) {
  return (
    <>
      <DicaPagina chave="cidade" />
      <PaginaCidade params={params} />
    </>
  );
}
