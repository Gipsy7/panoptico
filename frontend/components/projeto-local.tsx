/**
 * Projeto e votação de câmara municipal ou assembleia (/projeto/local/[id] e /votacao/local/[id]).
 * Mostra o que a casa publica (matéria, ementa quando existe, resultado, placar, voto de cada
 * parlamentar) e diz o que a casa não publica: orientação de bancada e discursos.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { BarraPlacar, PlacarCompacto } from "@/components/barra-placar";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { Revelacao } from "@/components/revelacao";
import { type CasaProjeto, type ProjetoLocal, type VotacaoLocal, getProjetoLocal, getVotacaoLocal } from "@/lib/api";
import { CASA_PROJETO_CURTA, formatarData, lugarDoProjeto, textoResultado } from "@/lib/formato";
import { agruparVotosLocais, caminhoInterno, recortar } from "@/lib/projetos";

const INTEIRO = new Intl.NumberFormat("pt-BR");
const n = (v: number) => INTEIRO.format(v);

const linkParlamentar = (casa: CasaProjeto, mandatoId: number) =>
  casa === "assembleia" ? `/deputado-estadual/${mandatoId}` : `/vereador/${mandatoId}`;
const quem = (casa: CasaProjeto) => (casa === "assembleia" ? "deputado estadual" : "vereador");

// ---------------------------------------------------------------------------------------------
// Projeto local
// ---------------------------------------------------------------------------------------------

export async function metadadosProjetoLocal(id: string): Promise<Metadata> {
  const r = await getProjetoLocal(id);
  if (!r.ok) return { title: "Projeto" };
  const d = r.dados;
  const lugar = lugarDoProjeto(d.casa, d.uf, d.municipio);
  return {
    title: `${d.rotulo}: ${lugar}`,
    description: `${recortar(d.ementa, 150)} ${d.votacoes.length ? `${d.votacoes.length} votação(ões) nominal(is) registrada(s). ` : ""}Dados publicados pela casa, com fonte e data.`,
  };
}

export function PaginaProjetoLocal({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o projeto…" secoes={3} />}>
      {params.then(({ id }) => (
        <ProjetoLocalConteudo id={id} />
      ))}
    </Revelacao>
  );
}

async function ProjetoLocalConteudo({ id }: { id: string }) {
  if (!/^\d+$/.test(id)) notFound();
  const r = await getProjetoLocal(id);
  if (!r.ok) {
    if (r.status === 404 || r.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={r.mensagem} />;
  }
  const d = r.dados;
  const lugar = lugarDoProjeto(d.casa, d.uf, d.municipio);
  const rodape = <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />;
  const situacao =
    d.em_tramitacao === true ? "Em tramitação" : d.em_tramitacao === false ? "Não está mais em tramitação" : null;
  const temVotacao = d.votacoes.length > 0;

  // Só o que existe: sem votação, a aba some e uma frase diz o que falta.
  const abas: AbaDetalhe[] = [
    {
      id: "trata",
      rotulo: "Do que se trata",
      secoes: [{ id: "do-que-se-trata", titulo: "Do que se trata", conteudo: <DoQueSeTrataLocal d={d} rodape={rodape} /> }],
    },
    ...(temVotacao
      ? [
          {
            id: "votacoes",
            rotulo: "Votações",
            secoes: [{ id: "votacoes", titulo: "Votações", conteudo: <VotacoesLocais d={d} rodape={rodape} /> }],
          },
        ]
      : []),
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="sobretitulo">Projeto · {lugar}</p>
          <h1 className="titulo-pagina">{d.rotulo}</h1>
          <p className="text-lg leading-snug">{d.ementa}</p>
        </div>
        <GradeCartoes rotulo="Números deste projeto">
          {situacao && <CartaoNumero destino="do-que-se-trata" rotulo="Situação" valor={situacao} apoio="Como a casa publica" />}
          {temVotacao && (
            <CartaoNumero destino="votacoes" rotulo="Votações nominais" valor={n(d.votacoes.length)} apoio="com o voto de cada um" />
          )}
          <CartaoNumero
            destino="do-que-se-trata"
            rotulo="Apresentado em"
            valor={d.data_apresentacao ? formatarData(d.data_apresentacao) : String(d.ano)}
            apoio={d.data_apresentacao ? undefined : "Só o ano é publicado"}
          />
          {d.autor && (
            <CartaoNumero destino="do-que-se-trata" rotulo="Autor" valor={d.autor.nome} apoio={d.autor.partido ?? undefined} />
          )}
        </GradeCartoes>
        {/* Sem votação, o aviso da API já diz o que falta (não tem votação nominal registrada nesta fonte). */}
        <p className="nota text-sm">{d.aviso}</p>
        <CompartilharWhatsApp
          caminho={`/projeto/local/${d.id}`}
          texto={`${d.rotulo} (${lugar}). ${recortar(d.ementa, 140)} Veja a ementa e as votações, com a fonte oficial:`}
        />
      </div>
      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />
    </article>
  );
}

function DoQueSeTrataLocal({ d, rodape }: { d: ProjetoLocal; rodape: React.ReactNode }) {
  return (
    <section aria-labelledby="trata-titulo" className="flex flex-col gap-4">
      <h3 id="trata-titulo" className="text-2xl">
        Do que se trata
      </h3>
      <p className="leading-relaxed">{d.ementa}</p>
      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-muted-foreground">Tipo</dt>
          <dd className="font-medium">{d.tipo}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Casa</dt>
          <dd className="font-medium">{lugarDoProjeto(d.casa, d.uf, d.municipio)}</dd>
        </div>
        {d.autor && (
          <div>
            <dt className="text-muted-foreground">Autor</dt>
            <dd className="font-medium">
              <Link href={linkParlamentar(d.casa, d.autor.mandato_id)} className="alvo-link underline underline-offset-2">
                {d.autor.nome}
              </Link>
              {d.autor.partido && <span className="font-normal text-muted-foreground"> · {d.autor.partido}</span>}
            </dd>
          </div>
        )}
      </dl>
      <a href={d.url_oficial} target="_blank" rel="noopener noreferrer" className="alvo-link self-start font-medium underline underline-offset-4">
        Ver o projeto no site da casa
      </a>
      {rodape}
    </section>
  );
}

function VotacoesLocais({ d, rodape }: { d: ProjetoLocal; rodape: React.ReactNode }) {
  return (
    <section aria-labelledby="votacoes-titulo" className="flex flex-col gap-4">
      <h3 id="votacoes-titulo" className="text-2xl">
        Votações
      </h3>
      {d.votacoes.length === 0 ? (
        <p className="nota text-sm">
          A casa não publicou votação nominal deste projeto. Pode ter sido votado de forma simbólica, que não registra o
          voto de cada um.
        </p>
      ) : (
        <ul className="lista-fios">
          {d.votacoes.map((v) => (
            <li key={v.id} className="flex flex-col gap-2 py-4">
              {(v.data || v.resultado) && (
                <p className="text-sm text-muted-foreground tabular-nums">
                  {[v.data ? formatarData(v.data) : null, v.resultado ? textoResultado(v.resultado) : null].filter(Boolean).join(" · ")}
                </p>
              )}
              <p className="text-sm leading-relaxed">{v.materia}</p>
              <PlacarCompacto sim={v.sim} nao={v.nao} />
              {v.abstencoes > 0 && (
                <p className="text-sm text-muted-foreground tabular-nums">
                  {n(v.abstencoes)} {v.abstencoes === 1 ? "abstenção" : "abstenções"}
                </p>
              )}
              <Link href={caminhoInterno(v.link)} className="alvo-link self-start text-sm font-medium underline underline-offset-4">
                Ver o voto de cada {quem(d.casa)}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {rodape}
    </section>
  );
}

// ---------------------------------------------------------------------------------------------
// Votação local
// ---------------------------------------------------------------------------------------------

export async function metadadosVotacaoLocal(id: string): Promise<Metadata> {
  const r = await getVotacaoLocal(id);
  if (!r.ok) return { title: "Votação" };
  const d = r.dados;
  return {
    title: `${recortar(d.materia, 70)}: como votaram na ${CASA_PROJETO_CURTA[d.casa]}${d.municipio ? ` de ${d.municipio}` : ""}`,
    description: `${textoResultado(d.resultado) ? `${textoResultado(d.resultado)}. ` : ""}Sim ${n(d.sim)}, Não ${n(d.nao)}. O voto de cada ${quem(d.casa)}, como a casa publica, com fonte e data.`,
  };
}

export function PaginaVotacaoLocal({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando a votação…" secoes={3} />}>
      {params.then(({ id }) => (
        <VotacaoLocalConteudo id={id} />
      ))}
    </Revelacao>
  );
}

async function VotacaoLocalConteudo({ id }: { id: string }) {
  if (!/^\d+$/.test(id)) notFound();
  const r = await getVotacaoLocal(id);
  if (!r.ok) {
    if (r.status === 404 || r.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={r.mensagem} />;
  }
  const d = r.dados;
  const lugar = lugarDoProjeto(d.casa, d.uf, d.municipio);
  const resultado = textoResultado(d.resultado);
  const rodape = <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />;
  const grupos = agruparVotosLocais(d.votos);

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="sobretitulo">
            Votação · {lugar}
            {d.data && <> · {formatarData(d.data)}</>}
          </p>
          <h1 className="titulo-pagina">{d.materia}</h1>
          {d.ementa && <p className="text-lg leading-snug">{d.ementa}</p>}
        </div>

        <div className="figura flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">Resultado{resultado ? ` publicado pela casa: ${resultado}` : " não publicado pela casa"}</p>
          <p className="numero text-[1.625rem] leading-none tabular-nums">
            {n(d.sim)} <span className="text-base text-muted-foreground">Sim</span> × {n(d.nao)}{" "}
            <span className="text-base text-muted-foreground">Não</span>
          </p>
          <BarraPlacar sim={d.sim} nao={d.nao} />
          {d.abstencoes > 0 && (
            <p className="text-sm text-muted-foreground tabular-nums">
              {n(d.abstencoes)} {d.abstencoes === 1 ? "abstenção" : "abstenções"}
            </p>
          )}
        </div>

        <p className="nota text-sm">{d.aviso}</p>

        <div className="flex flex-wrap gap-3">
          {d.projeto_link && (
            <Link href={caminhoInterno(d.projeto_link)} className="botao-linha">
              Ver tudo sobre o projeto
            </Link>
          )}
          {d.url_oficial && (
            <a href={d.url_oficial} target="_blank" rel="noopener noreferrer" className="botao-linha">
              Ver no site da casa
            </a>
          )}
        </div>
        <CompartilharWhatsApp
          caminho={`/votacao/local/${d.id}`}
          texto={`${recortar(d.materia, 90)} (${lugar}): ${resultado ? `${resultado.toLowerCase()}, ` : ""}Sim ${n(d.sim)} x Não ${n(d.nao)}. Veja o voto de cada ${quem(d.casa)}:`}
        />
        {rodape}
      </div>

      <AbasDetalhe
        titulo="Tudo em detalhe"
        abas={[
          {
            id: "votos",
            rotulo: `Como votou cada ${quem(d.casa)}`,
            secoes: [{ id: "votos", titulo: "Votos", conteudo: <VotosLocais d={d} grupos={grupos} rodape={rodape} /> }],
          },
        ]}
      />
    </article>
  );
}

function VotosLocais({
  d,
  grupos,
  rodape,
}: {
  d: VotacaoLocal;
  grupos: ReturnType<typeof agruparVotosLocais>;
  rodape: React.ReactNode;
}) {
  return (
    <section aria-labelledby="votos-titulo" className="flex flex-col gap-5">
      <div>
        <h3 id="votos-titulo" className="text-2xl">
          Como votou cada {quem(d.casa)}
        </h3>
        <p className="text-sm text-muted-foreground">Sim, Não e outros registros, como a casa publica. Quem não aparece não teve voto registrado.</p>
      </div>
      {d.votos.length === 0 && <p className="text-muted-foreground">A casa não publicou o voto de cada um.</p>}
      {grupos
        .filter((g) => g.votos.length > 0)
        .map((g) => (
          <section key={g.chave} aria-label={g.rotulo} className="flex flex-col gap-1">
            <h4 className="text-base font-semibold">
              {g.rotulo} <span className="font-normal text-muted-foreground tabular-nums">({n(g.votos.length)})</span>
            </h4>
            <ul className="lista-fios">
              {g.votos.map((v) => (
                <li key={v.mandato_id} className="flex min-h-11 items-center justify-between gap-3 py-2">
                  <span className="flex min-w-0 flex-col">
                    <Link href={linkParlamentar(d.casa, v.mandato_id)} className="truncate underline underline-offset-2">
                      {v.nome}
                    </Link>
                    {v.partido && <span className="text-xs text-muted-foreground">{v.partido}</span>}
                  </span>
                  {g.chave === "outros" && <span className="shrink-0 text-right text-sm text-muted-foreground">{v.voto}</span>}
                </li>
              ))}
            </ul>
          </section>
        ))}
      {rodape}
    </section>
  );
}
