import type { Metadata } from "next";

import {
  PaginaDinheiroFederal,
  metadadosDinheiroFederal,
} from "@/components/dinheiro-federal/pagina-dinheiro-federal";

export async function generateMetadata({
  params,
  searchParams,
}: PageProps<"/impostos-e-repasses/[[...lugar]]">): Promise<Metadata> {
  const [p, s] = await Promise.all([params, searchParams]);
  return metadadosDinheiroFederal({ lugar: p.lugar, ano: s.ano });
}

export default function DinheiroFederalPage({ params, searchParams }: PageProps<"/impostos-e-repasses/[[...lugar]]">) {
  return <PaginaDinheiroFederal params={params} searchParams={searchParams} />;
}
