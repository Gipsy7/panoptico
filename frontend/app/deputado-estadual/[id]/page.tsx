import type { Metadata } from "next";

import { PerfilMandatoLocal } from "@/components/mandato-local-perfil";
import { Revelacao } from "@/components/revelacao";
import { getVereador } from "@/lib/api";

export async function generateMetadata({ params }: PageProps<"/deputado-estadual/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getVereador(id);
  if (!resultado.ok) return { title: "Deputado estadual" };
  const v = resultado.dados;
  const descricao = `Deputado estadual${v.partido ? ` (${v.partido})` : ""}: projetos, proposições e contato, como a assembleia publica.`;
  return { title: v.nome, description: descricao, openGraph: { title: `${v.nome} · Deputado estadual`, description: descricao } };
}

export default function Pagina({ params, searchParams }: PageProps<"/deputado-estadual/[id]">) {
  return (
    <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
      {Promise.all([params, searchParams]).then(([{ id }, busca]) => (
        <PerfilMandatoLocal id={id} paginaVotos={typeof busca.votos === "string" ? busca.votos : undefined} />
      ))}
    </Revelacao>
  );
}
