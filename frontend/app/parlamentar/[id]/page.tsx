import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { AvisoErro } from "@/components/aviso-erro";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { GastosSecao } from "@/components/gastos-secao";
import { Foto } from "@/components/parlamentar-card";
import { PresencaSecao } from "@/components/presenca-secao";
import { ProjetosSecao } from "@/components/projetos-secao";
import { RemuneracaoSecao } from "@/components/remuneracao-secao";
import { ResumoPerfil } from "@/components/resumo-perfil";
import { TemasSecao } from "@/components/temas-secao";
import { VotosSecao } from "@/components/votos-secao";
import {
  getGastos,
  getParlamentar,
  getPresenca,
  getProjetos,
  getTemas,
  getVotos,
} from "@/lib/api";
import { FONTE_CASA, NOME_CASA } from "@/lib/formato";

export async function generateMetadata({
  params,
}: PageProps<"/parlamentar/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getParlamentar(id);
  if (!resultado.ok) return { title: "Parlamentar" };
  const p = resultado.dados;
  const descricao = `Gastos do gabinete, presença em votações e projetos de lei de ${p.nome_parlamentar} (${[p.partido, p.uf].filter(Boolean).join("-")}), com dados oficiais e link para a fonte.`;
  return {
    title: p.nome_parlamentar,
    description: descricao,
    openGraph: { title: `${p.nome_parlamentar} · ${NOME_CASA[p.casa]}`, description: descricao },
  };
}

export default function ParlamentarPage({
  params,
  searchParams,
}: PageProps<"/parlamentar/[id]">) {
  return (
    <Suspense fallback={<Carregando />}>
      {Promise.all([params, searchParams]).then(([{ id }, sp]) => {
        const texto = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);
        return (
          <Perfil
            id={id}
            ano={texto(sp.ano)}
            tema={texto(sp.tema)}
            paginaVotos={texto(sp.pagina_votos)}
          />
        );
      })}
    </Suspense>
  );
}

async function Perfil({
  id,
  ano,
  tema,
  paginaVotos,
}: {
  id: string;
  ano?: string;
  tema?: string;
  paginaVotos?: string;
}) {
  const [resultado, gastos, projetos, presenca, temas, votos] = await Promise.all([
    getParlamentar(id),
    getGastos(id, ano),
    getProjetos(id),
    getPresenca(id, ano),
    getTemas(id),
    getVotos(id, { ano, tema, pagina: paginaVotos }),
  ]);
  if (!resultado.ok) {
    if (resultado.status === 404 || resultado.status === 422) notFound();
    return <AvisoErro titulo="Não deu para carregar agora" mensagem={resultado.mensagem} />;
  }
  const p = resultado.dados;

  return (
    <article className="flex flex-col gap-6">
      <header className="flex items-start gap-4">
        <Foto parlamentar={p} largura={96} prioridade />
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight">{p.nome_parlamentar}</h1>
          {p.nome_civil && p.nome_civil !== p.nome_parlamentar && (
            <p className="text-sm text-muted-foreground">{p.nome_civil}</p>
          )}
          <p className="text-muted-foreground">
            {NOME_CASA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
          </p>
          {!p.em_exercicio && (
            <p className="text-sm font-medium">Fora de exercício no momento.</p>
          )}
        </div>
      </header>

      <ResumoPerfil
        gastos={gastos.ok ? gastos.dados : undefined}
        presenca={presenca.ok ? presenca.dados : undefined}
        projetos={projetos.ok ? projetos.dados : undefined}
        subsidio={p.remuneracao.subsidio_mensal}
      />

      <CompartilharWhatsApp
        caminho={`/parlamentar/${p.id}`}
        texto={`Veja os gastos, a presença e os projetos de ${p.nome_parlamentar} (${NOME_CASA[p.casa]}), com dados oficiais:`}
      />

      {gastos.ok ? (
        <GastosSecao gastos={gastos.dados} casa={p.casa} parlamentarId={p.id} />
      ) : (
        <p className="text-sm text-muted-foreground">Gastos do gabinete: {gastos.mensagem}</p>
      )}

      {presenca.ok && <PresencaSecao presenca={presenca.dados} casa={p.casa} />}

      {votos.ok && <VotosSecao dados={votos.dados} casa={p.casa} parlamentarId={p.id} />}

      {projetos.ok && <ProjetosSecao projetos={projetos.dados} casa={p.casa} />}

      {temas.ok && <TemasSecao dados={temas.dados} />}

      <RemuneracaoSecao remuneracao={p.remuneracao} />

      <section className="flex flex-col gap-2 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <h2 className="font-semibold">Contato do gabinete</h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          {p.email && (
            <>
              <dt className="text-muted-foreground">E-mail</dt>
              <dd className="break-all">
                <a href={`mailto:${p.email}`} className="underline underline-offset-2">
                  {p.email}
                </a>
              </dd>
            </>
          )}
          {p.telefone && (
            <>
              <dt className="text-muted-foreground">Telefone</dt>
              <dd>
                <a href={`tel:${p.telefone.replace(/\D/g, "")}`} className="underline underline-offset-2">
                  {p.telefone}
                </a>
              </dd>
            </>
          )}
          {p.pagina_url && (
            <>
              <dt className="text-muted-foreground">Página oficial</dt>
              <dd>
                <a
                  href={p.pagina_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-2"
                >
                  {NOME_CASA[p.casa]}
                </a>
              </dd>
            </>
          )}
        </dl>
      </section>

      <FonteRodape fonte={FONTE_CASA[p.casa]} url={p.fonte_url} atualizadoEm={p.atualizado_em} />
    </article>
  );
}

function Carregando() {
  return (
    <div className="flex gap-4" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando perfil…</span>
      <div className="h-32 w-24 animate-pulse rounded-lg bg-muted" />
      <div className="flex flex-1 flex-col gap-2">
        <div className="h-7 w-2/3 animate-pulse rounded-lg bg-muted" />
        <div className="h-5 w-1/2 animate-pulse rounded-lg bg-muted" />
      </div>
    </div>
  );
}
