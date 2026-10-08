import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { CandidaturaSecao } from "@/components/candidatura-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { QuemESecao } from "@/components/dados-pessoais";
import { FotoOuIniciais } from "@/components/eleitos-secao";
import { Revelacao } from "@/components/revelacao";
import { getCanais, getEleito } from "@/lib/api";

export async function generateMetadata({ params }: PageProps<"/eleito/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getEleito(id);
  if (!resultado.ok) return { title: "Eleito" };
  const e = resultado.dados;
  const descricao = `${e.cargo} em ${e.unidade} (${[e.partido, e.uf].filter(Boolean).join("-")}): bens declarados e contas de campanha, com dados oficiais do TSE.`;
  return { title: e.nome_urna, description: descricao, openGraph: { title: `${e.nome_urna} · ${e.cargo}`, description: descricao } };
}

export default function EleitoPage({ params }: PageProps<"/eleito/[id]">) {
  return (
    <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
      {params.then(({ id }) => (
        <Perfil id={id} />
      ))}
    </Revelacao>
  );
}

async function Perfil({ id }: { id: string }) {
  const resultado = await getEleito(id);
  if (!resultado.ok) {
    if (resultado.status === 404) notFound();
    return <AvisoErro titulo="Não deu para carregar" mensagem={resultado.mensagem} />;
  }
  const e = resultado.dados;
  if (e.mandato_local) {
    redirect(`/${e.mandato_local.casa === "camara" ? "vereador" : "deputado-estadual"}/${e.mandato_local.id}`);
  }
  const canais = e.municipio_ibge ? await getCanais(e.municipio_ibge) : null;
  const temSapl = Boolean(canais?.ok && canais.dados.itens.some((c) => c.tipo === "sapl"));
  const voltar = e.municipio_ibge
    ? `/representantes?municipio=${e.municipio_ibge}`
    : e.uf === "BR"
      ? "/"
      : `/representantes?uf=${e.uf}`;

  return (
    <article className="flex flex-col gap-8">
      <header className="flex items-start gap-4">
        <FotoOuIniciais eleito={e} tamanho={72} />
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-3xl tracking-tight">{e.nome_urna}</h1>
          <p className="text-muted-foreground">
            {e.cargo} · {e.unidade}
          </p>
          <p className="flex flex-wrap gap-1">
            {e.partido && <span className="pilula">{e.partido}</span>}
            {e.numero && <span className="pilula">Número {e.numero}</span>}
            <span className="pilula">Eleição de {e.ano_eleicao}</span>
          </p>
          {e.situacao && <p className="text-sm text-muted-foreground">{e.situacao}</p>}
        </div>
      </header>

      <QuemESecao pessoais={e.pessoais} votos={e.votos != null ? { ano: e.ano_eleicao, total: e.votos } : null} />

      <section aria-labelledby="atividade-titulo" className="flex flex-col gap-3">
        <h2 id="atividade-titulo" className="text-2xl">
          No cargo
        </h2>
        <p className="text-sm text-muted-foreground">
          {e.cargo !== "Vereador"
            ? `${atividade(e.cargo)} ainda não estão no site. Por enquanto, aparece o que o TSE publica sobre a eleição.`
            : temSapl
              ? `A câmara de ${e.unidade} publica quem está no cargo hoje, mas este nome não aparece na lista dela: a pessoa pode ter deixado o cargo ou usar lá outro nome. Veja a lista da câmara na página da cidade.`
              : `A câmara de ${e.unidade} não publica votações e projetos num formato de dados abertos que o Panóptico consiga ler (o sistema SAPL, do Interlegis). Por isso, aqui aparece só o que o TSE publica sobre a eleição.`}{" "}
          Mudanças depois da eleição (suplente que assumiu, renúncia, cassação) também não aparecem.
        </p>
        {canais?.ok && canais.dados.itens.length > 0 && (
          <div className="flex flex-col gap-1">
            <p className="text-sm">Os canais oficiais da cidade:</p>
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {canais.dados.itens.map((c) => (
                <li key={c.tipo}>
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                    {NOME_CANAL[c.tipo] ?? c.tipo}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <CompartilharWhatsApp
        caminho={`/eleito/${e.id}`}
        texto={`Veja os bens e a campanha de ${e.nome_urna} (${e.cargo.toLowerCase()}, ${e.unidade}), com dados oficiais do TSE:`}
      />

      {e.depois && (
        <p className="text-sm">
          Eleito depois para{" "}
          <Link href={`/eleito/${e.depois.id}`} className="font-medium underline underline-offset-2">
            {e.depois.cargo.toLowerCase()} de {e.depois.unidade}
          </Link>{" "}
          em {e.depois.ano}.
        </p>
      )}

      <CandidaturaSecao dados={e} />

      {!e.bens && !e.campanha && (
        <p className="text-muted-foreground">O TSE não tem bens nem contas de campanha registrados para esta candidatura.</p>
      )}

      <Link href={voltar} className="self-start text-sm underline underline-offset-4">
        {e.uf === "BR" ? "Voltar ao início" : `Ver os outros eleitos de ${e.unidade}`}
      </Link>
    </article>
  );
}

const NOME_CANAL: Record<string, string> = {
  prefeitura: "Prefeitura",
  camara: "Câmara municipal",
  sapl: "Sistema legislativo da câmara",
  transparencia_prefeitura: "Transparência da prefeitura",
  transparencia_camara: "Transparência da câmara",
};

function atividade(cargo: string): string {
  if (cargo === "Vereador") return "Gastos e votos na câmara municipal";
  if (cargo.startsWith("Deputado")) return "Gastos e votos na assembleia";
  if (cargo.includes("Prefeito")) return "Gastos e decisões da prefeitura";
  if (cargo.includes("Governador")) return "Gastos e decisões do governo do estado";
  return "Gastos e decisões do governo federal";
}
