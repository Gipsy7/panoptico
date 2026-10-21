import type { Metadata } from "next";

import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { PerfilMandatoLocal } from "@/components/mandato-local-perfil";
import { Revelacao } from "@/components/revelacao";
import { JsonLdPerfil, montarDescricao, nomeComSigla } from "@/components/json-ld";
import { getVereador, urlFotoTse } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

export async function generateMetadata({ params }: PageProps<"/vereador/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getVereador(id);
  if (!resultado.ok) return { title: "Vereador" };
  const v = resultado.dados;
  const g = v.gastos && v.gastos.total > 0 ? v.gastos : null;
  const pr = v.presenca && v.presenca.sessoes > 0 ? v.presenca : null;
  const descricao =
    g || pr
      ? montarDescricao([
          g &&
            `Gastou ${formatarReais(g.total, true)} em ${g.ano}${g.media_casa ? ` (média da Câmara: ${formatarReais(g.media_casa, true)})` : ""}.`,
          pr && `Esteve em ${pr.presencas} de ${pr.sessoes} sessões.`,
        ])
      : `Vereador${v.partido ? ` (${v.partido})` : ""}: projetos, proposições e contato, como a câmara publica.`;
  const sufixo = g || pr ? "gastos, presença e projetos" : "projetos e proposições";
  return {
    title: `${nomeComSigla(v.nome, v.partido, v.uf)}: ${sufixo}`,
    description: descricao,
    openGraph: { title: `${v.nome} · Vereador`, description: descricao },
  };
}

async function DadosEstruturados({ id }: { id: string }) {
  const resultado = await getVereador(id);
  if (!resultado.ok) return null;
  const v = resultado.dados;
  const foto = v.foto_tse && v.candidatura_id ? urlFotoTse(v.candidatura_id) : v.foto_url;
  return (
    <JsonLdPerfil
      caminho={`/vereador/${v.id}`}
      nome={v.nome}
      cargo="Vereador"
      casa="Câmara Municipal"
      partido={v.partido}
      uf={v.uf}
      imagem={foto}
      oficial={v.sapl_url}
    />
  );
}

export default function Pagina({ params, searchParams }: PageProps<"/vereador/[id]">) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o perfil…" secoes={3} />}>
      {Promise.all([params, searchParams]).then(([{ id }, busca]) => (
        <>
          <DadosEstruturados id={id} />
          <PerfilMandatoLocal id={id} paginaVotos={typeof busca.votos === "string" ? busca.votos : undefined} />
        </>
      ))}
    </Revelacao>
  );
}
