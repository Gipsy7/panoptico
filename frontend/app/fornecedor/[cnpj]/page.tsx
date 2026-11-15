import type { Metadata } from "next";

import { PaginaFornecedor, metadadosFornecedor } from "@/components/ficha-fornecedor";

export async function generateMetadata({ params }: PageProps<"/fornecedor/[cnpj]">): Promise<Metadata> {
  const { cnpj } = await params;
  return metadadosFornecedor(cnpj);
}

export default function FornecedorPage({ params }: PageProps<"/fornecedor/[cnpj]">) {
  return <PaginaFornecedor params={params} />;
}
