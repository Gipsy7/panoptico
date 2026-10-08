import type { Metadata } from "next";

import { PerfilMandatoLocal } from "@/components/mandato-local-perfil";
import { Revelacao } from "@/components/revelacao";
import { getVereador } from "@/lib/api";

export async function generateMetadata({ params }: PageProps<"/vereador/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getVereador(id);
  if (!resultado.ok) return { title: "Vereador" };
  const v = resultado.dados;
  const descricao = `Vereador${v.partido ? ` (${v.partido})` : ""}: projetos, proposições e contato, como a câmara publica.`;
  return { title: v.nome, description: descricao, openGraph: { title: `${v.nome} · Vereador`, description: descricao } };
}

export default function Pagina({ params }: PageProps<"/vereador/[id]">) {
  return (
    <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
      {params.then(({ id }) => (
        <PerfilMandatoLocal id={id} />
      ))}
    </Revelacao>
  );
}
