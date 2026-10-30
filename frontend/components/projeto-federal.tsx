/**
 * Página de um projeto do Congresso (/projeto/[casa]/[id]), no padrão do explicador de votação:
 * cartões no topo, "Para entender" e o detalhe em abas (Do que se trata, Votações, Quem votou,
 * O que disseram, Caminho). Cada bloco traz a própria fonte e data. Sem juízo: só o que a Casa
 * publica, com o termo oficial em letra menor.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { BotaoAviso } from "@/components/botao-aviso";
import { chaveAlvo } from "@/lib/avisos";
import { PlacarCompacto, CartaoPlacarLink } from "@/components/barra-placar";
import { CaminhoLinha } from "@/components/caminho-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { AvisoDiscursos, DiaDeDiscursosBloco } from "@/components/discursos-secao";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { QuemVotou } from "@/components/quem-votou";
import { Revelacao } from "@/components/revelacao";
import { type ProjetoFederal, getProjetoFederal } from "@/lib/api";
import { CASA_CURTA, CASA_DA, NOME_CASA, formatarData, textoResultado } from "@/lib/formato";
import { caminhoInterno, lerUf, placarDaVotacao, placarMaiorQueALista, recortar, situacaoSimples, textoCompartilharProjeto } from "@/lib/projetos";
import { LinkExterno } from "@/components/link-externo";

const INTEIRO = new Intl.NumberFormat("pt-BR");
const n = (v: number) => INTEIRO.format(v);

export const AVISO_SEM_VOTACAO =
  "Este projeto ainda não teve votação nominal no Plenário; quando tiver, o placar e o voto de cada um aparecem aqui. Decisões em votação simbólica, que não registra o voto de cada um, não entram.";

export async function metadadosProjetoFederal(casa: string, id: string): Promise<Metadata> {
  if (casa !== "camara" && casa !== "senado") return { title: "Projeto" };
  const r = await getProjetoFederal(casa, id);
  if (!r.ok) return { title: "Projeto" };
  const d = r.dados;
  const ultima = d.votacoes.itens[0];
  const placar = ultima ? placarDaVotacao(ultima) : null;
  return {
    title: `${d.rotulo}: o que diz, como foi votado e o que disseram`,
    description: `${d.ementa ? `${recortar(d.ementa, 140)} ` : ""}${
      placar
        ? `Última votação nominal (${formatarData(ultima.data)}): Sim ${n(placar.sim)}, Não ${n(placar.nao)}.`
        : "Sem votação nominal no Plenário até agora."
    } Dados oficiais ${CASA_DA[d.casa]}, com fonte e data.`,
  };
}

export function PaginaProjetoFederal({
  params,
  searchParams,
}: {
  params: Promise<{ casa: string; id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o projeto…" secoes={3} />}>
      {Promise.all([params, searchParams]).then(([{ casa, id }, sp]) => (
        <Projeto casa={casa} id={id} ufInicial={lerUf(sp.uf)} />
      ))}
    </Revelacao>
  );
}

async function Projeto({ casa, id, ufInicial }: { casa: string; id: string; ufInicial: string | null }) {
  if (casa !== "camara" && casa !== "senado") notFound();
  const r = await getProjetoFederal(casa, id);
  if (!r.ok) {
    if (r.status === 404 || r.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={r.mensagem} />;
  }
  const d = r.dados;
  const ultima = d.votacoes.itens[0] ?? null;
  const placar = ultima ? placarDaVotacao(ultima) : null;
  const sit = situacaoSimples(d.ficha.situacao, d.ficha.virou_lei);
  const ultimoPasso = d.caminho.itens.at(-1);
  const etapaDoPasso = ultimoPasso && ultimoPasso.etapa !== "Outro andamento" ? ultimoPasso.etapa : null;
  const proxima = d.pauta.proxima;
  // Só aparece o que existe: aba, cartão e pergunta sem conteúdo ficam de fora (e o que falta é dito numa frase).
  const temVotacao = d.votacoes.itens.length > 0;
  const temDiscursos = d.discursos.dias.some((x) => x.total > 0) || d.discursos_do_dia.quantidade_nao_atribuida > 0;
  const passos = d.caminho.itens.length;
  const situacao = sit.rotulo ?? etapaDoPasso ?? sit.oficial;
  const autores = d.ficha.autores.filter((a) => a.primeiro_autor);

  const abas: AbaDetalhe[] = [
    { id: "trata", rotulo: "Do que se trata", secoes: [{ id: "do-que-se-trata", titulo: "Do que se trata", conteudo: <DoQueSeTrata d={d} sit={sit} /> }] },
    ...(temVotacao
      ? [
          { id: "votacoes", rotulo: "Votações", secoes: [{ id: "votacoes", titulo: "Votações no Plenário", conteudo: <Votacoes d={d} /> }] },
          { id: "quem", rotulo: "Quem votou", secoes: [{ id: "quem-votou", titulo: "Quem votou", conteudo: <QuemVotouSecao d={d} ufInicial={ufInicial} /> }] },
        ]
      : []),
    ...(temDiscursos
      ? [{ id: "disseram", rotulo: "O que disseram", secoes: [{ id: "discursos", titulo: "O que disseram", conteudo: <Discursos d={d} /> }] }]
      : []),
    ...(passos > 0
      ? [{ id: "caminho", rotulo: "Caminho", secoes: [{ id: "caminho", titulo: "Caminho do projeto", conteudo: <Caminho d={d} /> }] }]
      : []),
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="sobretitulo">
            Projeto no Congresso · {NOME_CASA[d.casa]}
            {d.ficha.data_apresentacao && <> · apresentado em {formatarData(d.ficha.data_apresentacao)}</>}
          </p>
          <h1 className="titulo-pagina">{d.rotulo}</h1>
          {d.ementa ? (
            <p className="text-lg leading-snug">{d.ementa}</p>
          ) : (
            <p className="text-muted-foreground">A fonte não traz o resumo (ementa) deste projeto.</p>
          )}
        </div>

        <GradeCartoes rotulo="Números deste projeto">
          {situacao && (
            <CartaoNumero
              destino={passos > 0 ? "caminho" : "do-que-se-trata"}
              rotulo="Situação"
              valor={situacao}
              apoio={
                sit.oficial && sit.oficial !== situacao
                  ? `Texto oficial: ${sit.oficial}`
                  : ultimoPasso
                    ? `Último andamento em ${formatarData(ultimoPasso.data)}`
                    : undefined
              }
            />
          )}
          {temVotacao && (
            <CartaoNumero destino="votacoes" rotulo="Votações nominais" valor={n(d.votacoes.itens.length)} apoio="no Plenário" />
          )}
          {placar && ultima && (
            <CartaoPlacarLink
              destino="quem-votou"
              rotulo={`Última votação nominal · ${formatarData(ultima.data)}`}
              sim={placar.sim}
              nao={placar.nao}
              apoio={placar.daFonte ? `placar publicado ${CASA_DA[d.casa]}` : "contagem da lista nominal"}
            />
          )}
          {proxima && (
            <CartaoNumero destino={passos > 0 ? "caminho" : "do-que-se-trata"} rotulo="Na pauta do Plenário" valor={formatarData(proxima.data)} apoio={proxima.sessao} />
          )}
          {passos > 0 && (!temVotacao || !proxima) && (
            <CartaoNumero
              destino="caminho"
              rotulo="Caminho"
              valor={`${n(passos)} ${passos === 1 ? "passo" : "passos"}`}
              apoio={ultimoPasso ? `o último em ${formatarData(ultimoPasso.data)}` : undefined}
            />
          )}
          {!temVotacao && d.ficha.data_apresentacao && (
            <CartaoNumero destino="do-que-se-trata" rotulo="Apresentado em" valor={formatarData(d.ficha.data_apresentacao)} />
          )}
          {!temVotacao && autores.length > 0 && (
            <CartaoNumero
              destino="do-que-se-trata"
              rotulo={autores.length > 1 ? "Autores" : "Autor"}
              valor={autores.length > 1 ? `${autores[0].nome} e mais ${n(autores.length - 1)}` : autores[0].nome}
              apoio={[autores[0].partido, autores[0].uf].filter(Boolean).join(" · ") || undefined}
            />
          )}
          {!temVotacao && autores.length === 0 && d.ficha.autor_descricao && (
            <CartaoNumero destino="do-que-se-trata" rotulo="Autoria" valor={recortar(d.ficha.autor_descricao, 60)} apoio="como a fonte descreve" />
          )}
        </GradeCartoes>
        {!temVotacao && <p className="nota text-sm">{AVISO_SEM_VOTACAO}</p>}
        <p className="text-sm text-muted-foreground">Toque ou clique num número para ver o detalhe, com a fonte e a data.</p>
        <CompartilharWhatsApp
          caminho={`/projeto/${d.casa}/${d.id_externo}`}
          texto={textoCompartilharProjeto({
            rotulo: d.rotulo,
            ementa: d.ementa,
            casaCurta: CASA_CURTA[d.casa],
            placar: placar && ultima ? { sim: placar.sim, nao: placar.nao, data: formatarData(ultima.data) } : null,
          })}
        />
        <BotaoAviso alvoTipo="projeto" alvoChave={chaveAlvo(d.casa, d.id_externo)} destino={d.rotulo} />
      </div>

      <ListaPerguntas titulo="Para entender">
        <Pergunta
          id="entender-nominal"
          pergunta="O que quer dizer votação nominal?"
          resposta="Cada voto fica registrado com o nome"
        >
          <p>
            Na votação nominal, cada parlamentar vota no painel eletrônico e o voto fica público. Muitas decisões são
            tomadas em votação simbólica, sem registro individual, e essas não aparecem aqui. Por isso um projeto pode ter
            andado sem nenhuma votação listada.
          </p>
        </Pergunta>
        {temVotacao && (
          <Pergunta
            id="entender-quem-votou"
            pergunta="Qual votação aparece em &quot;Quem votou&quot;?"
            resposta="A última votação nominal do texto"
          >
            <p>
              {d.votacao_principal?.regra ??
                "Quando o projeto tem votação nominal, mostramos a mais recente que não seja de requerimento, destaque ou emenda."}
            </p>
            <p>As outras votações do projeto estão na aba &quot;Votações&quot;, cada uma com a sua página.</p>
          </Pergunta>
        )}
        {temDiscursos && (
          <Pergunta
            id="entender-discursos"
            pergunta="Como os discursos são separados?"
            resposta="Pelo voto que quem discursou registrou"
          >
            <p>
              Ligamos cada discurso de Plenário ao projeto e ao dia em que ele foi falado. Dentro do dia, o discurso fica no
              grupo do voto que o orador registrou na última votação nominal do projeto: Votou Sim, Votou Não, Outro registro
              ou Falou e não registrou voto. A separação é só pelo voto registrado; não lemos nem interpretamos o que foi dito.
            </p>
          </Pergunta>
        )}
      </ListaPerguntas>

      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />
    </article>
  );
}

function DoQueSeTrata({ d, sit }: { d: ProjetoFederal; sit: ReturnType<typeof situacaoSimples> }) {
  const f = d.ficha;
  const principais = f.autores.filter((a) => a.primeiro_autor);
  const coautores = f.autores.filter((a) => !a.primeiro_autor);
  return (
    <section aria-labelledby="trata-titulo" className="flex flex-col gap-4">
      <h3 id="trata-titulo" className="text-2xl">
        Do que se trata
      </h3>
      {d.ementa ? <p className="leading-relaxed">{d.ementa}</p> : <p className="text-muted-foreground">A fonte não traz o resumo (ementa) deste projeto.</p>}

      {(sit.rotulo || sit.oficial) && (
        <div className="flex flex-col gap-0.5">
          <p className="text-sm text-muted-foreground">Situação</p>
          {sit.rotulo && <p className="font-semibold">{sit.rotulo}</p>}
          {sit.oficial && <p className="text-sm text-muted-foreground">Texto oficial: {sit.oficial}</p>}
        </div>
      )}

      {f.temas.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Temas (classificação oficial)</p>
          <ul className="flex flex-wrap gap-2">
            {f.temas.map((t) => (
              <li key={t}>
                <Link href={`/projetos?tema=${encodeURIComponent(t)}`} className="pilula inline-flex min-h-11 items-center">
                  {t}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(f.autores.length > 0 || f.autor_descricao) && (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">{principais.length > 1 ? "Autores" : "Autor"}</p>
          {f.autores.length > 0 && (
            <ul className="lista-fios">
              {principais.map((a) => (
                <li key={a.parlamentar_id} className="flex min-h-11 flex-col justify-center py-2">
                  <Link href={`/parlamentar/${a.parlamentar_id}`} className="font-medium underline underline-offset-2">
                    {a.nome}
                  </Link>
                  <span className="text-sm text-muted-foreground">{[a.partido, a.uf].filter(Boolean).join(" · ")}</span>
                </li>
              ))}
            </ul>
          )}
          {coautores.length > 0 && (
            <details>
              <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
                Ver os {coautores.length} {coautores.length === 1 ? "coautor" : "coautores"}
              </summary>
              <ul className="lista-fios">
                {coautores.map((a) => (
                  <li key={a.parlamentar_id} className="flex min-h-11 flex-col justify-center py-2">
                    <Link href={`/parlamentar/${a.parlamentar_id}`} className="underline underline-offset-2">
                      {a.nome}
                    </Link>
                    <span className="text-sm text-muted-foreground">{[a.partido, a.uf].filter(Boolean).join(" · ")}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {f.autor_descricao && <p className="text-sm text-muted-foreground">Como a fonte descreve a autoria: {f.autor_descricao}</p>}
        </div>
      )}

      {f.relator && (
        <div className="flex flex-col gap-0.5">
          <p className="text-sm text-muted-foreground">Relator</p>
          {f.relator_parlamentar_id ? (
            <Link href={`/parlamentar/${f.relator_parlamentar_id}`} className="alvo-link font-medium underline underline-offset-2">
              {f.relator}
            </Link>
          ) : (
            <p className="font-medium">{f.relator}</p>
          )}
        </div>
      )}

      {f.data_apresentacao && (
        <div className="flex flex-col gap-0.5">
          <p className="text-sm text-muted-foreground">Apresentado em</p>
          <p className="font-medium tabular-nums">{formatarData(f.data_apresentacao)}</p>
        </div>
      )}

      {d.caminho.itens.length === 0 && (
        <p className="text-sm text-muted-foreground">
          O caminho do projeto (cada passo da tramitação) ainda não foi carregado aqui; está na ficha oficial, no link abaixo.
        </p>
      )}

      {f.url_oficial && (
        <LinkExterno href={f.url_oficial} className="alvo-link self-start font-medium underline underline-offset-4">
          Ficha do projeto no site {CASA_DA[d.casa]}
        </LinkExterno>
      )}
      <FonteRodape fonte={f.fonte_nome} url={f.fonte_url} atualizadoEm={f.atualizado_em} />
    </section>
  );
}

function Votacoes({ d }: { d: ProjetoFederal }) {
  const b = d.votacoes;
  return (
    <section aria-labelledby="votacoes-titulo" className="flex flex-col gap-4">
      <h3 id="votacoes-titulo" className="text-2xl">
        Votações no Plenário
      </h3>
      {b.itens.length === 0 ? (
        <p className="nota text-sm">{b.aviso ?? AVISO_SEM_VOTACAO}</p>
      ) : (
        <ul className="lista-fios">
          {b.itens.map((v) => {
            const p = placarDaVotacao(v);
            const resultado = textoResultado(v.resultado);
            return (
              <li key={v.id_externo} className="flex flex-col gap-2 py-4">
                <p className="text-sm text-muted-foreground tabular-nums">
                  {formatarData(v.data)}
                  {v.secreta && " · votação secreta"}
                  {resultado && ` · ${resultado}`}
                </p>
                <p className="text-sm leading-relaxed">{v.descricao}</p>
                {v.secreta ? (
                  <p className="text-sm text-muted-foreground">A Casa publica quem votou e o placar, mas não o voto de cada um.</p>
                ) : (
                  <PlacarCompacto sim={p.sim} nao={p.nao} />
                )}
                <Link href={caminhoInterno(v.link)} className="alvo-link self-start text-sm font-medium underline underline-offset-4">
                  Ver esta votação em detalhe
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      <FonteRodape fonte={b.fonte_nome} url={b.fonte_url} atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function QuemVotouSecao({ d, ufInicial }: { d: ProjetoFederal; ufInicial: string | null }) {
  const b = d.votacao_principal;
  if (!b) {
    return (
      <section aria-labelledby="quem-titulo" className="flex flex-col gap-3">
        <h3 id="quem-titulo" className="text-2xl">
          Quem votou
        </h3>
        <p className="nota text-sm">{AVISO_SEM_VOTACAO}</p>
        <FonteRodape fonte={d.votacoes.fonte_nome} url={d.votacoes.fonte_url} atualizadoEm={d.votacoes.atualizado_em} />
      </section>
    );
  }
  const diferenca = placarMaiorQueALista(b.votacao.placar_publicado, b.grupos);
  return (
    <section aria-labelledby="quem-titulo" className="flex flex-col gap-4">
      <div>
        <h3 id="quem-titulo" className="text-2xl">
          Quem votou
        </h3>
        <p className="text-sm text-muted-foreground">
          Votação de {formatarData(b.votacao.data)}: {b.votacao.descricao}
        </p>
        <Link href={caminhoInterno(b.votacao.link)} className="alvo-link text-sm font-medium underline underline-offset-4">
          Ver esta votação em detalhe, com os partidos
        </Link>
      </div>
      <QuemVotou grupos={b.grupos} porUf={b.por_uf} ufInicial={ufInicial} />
      {diferenca && (
        <div className="nota text-sm tabular-nums">
          <p className="font-medium">Por que a lista soma menos que o placar?</p>
          <p>
            O placar publicado pela Casa tem Sim {diferenca.sim.toLocaleString("pt-BR")} e Não{" "}
            {diferenca.nao.toLocaleString("pt-BR")}; a lista desta página tem Sim{" "}
            {diferenca.listaSim.toLocaleString("pt-BR")} e Não {diferenca.listaNao.toLocaleString("pt-BR")}. Os votos de
            quem já deixou o cargo contam no placar, mas não estão no nosso cadastro.
          </p>
        </div>
      )}
      <p className="text-sm text-muted-foreground">{b.regra}</p>
      <FonteRodape fonte={b.fonte_nome} url={b.fonte_url} atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function Discursos({ d }: { d: ProjetoFederal }) {
  const b = d.discursos;
  const dias = b.dias.filter((x) => x.total > 0);
  return (
    <section aria-labelledby="discursos-titulo" className="flex flex-col gap-4">
      <h3 id="discursos-titulo" className="text-2xl">
        O que disseram
      </h3>
      <AvisoDiscursos extra={b.aviso} naoAtribuidos={d.discursos_do_dia.quantidade_nao_atribuida} />
      {dias.length === 0 ? (
        <p className="text-muted-foreground">Nenhum discurso de Plenário ligado a este projeto nos dias de votação.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {dias.map((dia, i) => (
            <DiaDeDiscursosBloco key={dia.data} data={dia.data} total={dia.total} grupos={dia.grupos} aberto={i === 0} />
          ))}
        </div>
      )}
      <FonteRodape fonte={b.fonte_nome} url={b.fonte_url} atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function Caminho({ d }: { d: ProjetoFederal }) {
  const b = d.caminho;
  return (
    <section aria-labelledby="caminho-titulo" className="flex flex-col gap-4">
      <h3 id="caminho-titulo" className="text-2xl">
        Caminho do projeto
      </h3>
      <p className="text-sm text-muted-foreground">
        Do mais antigo ao mais recente. A etapa vem em linguagem simples; o texto oficial do andamento fica logo abaixo, em letra menor.
      </p>
      <CaminhoLinha itens={b.itens} />
      <FonteRodape fonte={b.fonte_nome} url={b.fonte_url} atualizadoEm={b.atualizado_em} />
    </section>
  );
}
