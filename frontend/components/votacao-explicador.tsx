/**
 * Explicador de uma votação nominal do Plenário (/votacao/[casa]/[id]), no padrão dos painéis:
 * cartões no topo, "Para entender" e o detalhe em abas (Partidos, Parlamentares, Proposição).
 * Sem cor por partido nem cor de aprovado/rejeitado: Sim em bronze e Não em cinza só na barra
 * do placar, como em toda barra do site.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { AvisoDiscursos, GruposDeDiscursos } from "@/components/discursos-secao";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { Revelacao } from "@/components/revelacao";
import { VotacaoParlamentares } from "@/components/votacao-parlamentares";
import { type VotacaoDetalhe, getVotacao } from "@/lib/api";
import { CASA_CURTA, CASA_DA, formatarData } from "@/lib/formato";
import { idDaProposicao, lerUf } from "@/lib/projetos";

const INTEIRO = new Intl.NumberFormat("pt-BR");
const n = (v: number) => INTEIRO.format(v);

export const RESULTADO: Record<string, string> = { aprovada: "Aprovada", rejeitada: "Rejeitada" };

/** Placar principal: o publicado pela Casa quando existe (é o que vale), senão a contagem da lista. */
export function placarPrincipal(d: VotacaoDetalhe) {
  const o = d.placar_oficial;
  return {
    sim: o?.sim ?? d.placar.sim,
    nao: o?.nao ?? d.placar.nao,
    abstencao: o?.abstencao ?? (d.secreta ? null : d.placar.abstencao),
    obstrucao: d.secreta ? null : d.placar.obstrucao,
    daFonte: o?.sim != null || o?.nao != null,
  };
}

export function textoOrientacao(o: string | null | undefined) {
  if (!o) return "Não orientou";
  if (o === "Liberado") return "Liberou o voto";
  return o;
}

function quem(casa: VotacaoDetalhe["casa"], plural: boolean) {
  if (casa === "camara") return plural ? "deputados" : "deputado";
  return plural ? "senadores" : "senador";
}

export async function metadadosVotacao(casa: string, id: string): Promise<Metadata> {
  const r = await getVotacao(casa, id);
  if (!r.ok) return { title: "Votação" };
  const d = r.dados;
  const p = placarPrincipal(d);
  const nome = d.proposicao ?? "Votação";
  const resultado = d.resultado ? `${RESULTADO[d.resultado]}. ` : "";
  return {
    title: `${nome}: como votou ${d.casa === "camara" ? "a Câmara" : "o Senado"} em ${formatarData(d.data)}`,
    description: `${resultado}Sim ${n(p.sim)}, Não ${n(p.nao)}. ${
      d.secreta ? "Votação secreta." : "Orientação do Governo e dos partidos e o voto de cada parlamentar."
    } Dados oficiais ${CASA_DA[d.casa]}, com fonte e data.`,
  };
}

export function PaginaVotacao({
  params,
  searchParams,
}: {
  params: Promise<{ casa: string; id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando a votação…" secoes={3} />}>
      {Promise.all([params, searchParams]).then(([{ casa, id }, sp]) => (
        <Votacao casa={casa} id={id} ufInicial={lerUf(sp.uf)} />
      ))}
    </Revelacao>
  );
}

async function Votacao({ casa, id, ufInicial }: { casa: string; id: string; ufInicial: string | null }) {
  if (casa !== "camara" && casa !== "senado") notFound();
  const r = await getVotacao(casa, id);
  if (!r.ok) {
    if (r.status === 404 || r.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={r.mensagem} />;
  }
  const d = r.dados;
  const p = placarPrincipal(d);
  const casaCurta = CASA_CURTA[d.casa];
  const governo = d.liderancas.find((l) => l.bancada === "Governo");
  // Votos publicados pela Casa x votos na lista nominal (só quem está no nosso cadastro).
  const votaramSecreto = d.outros_registros.find((o) => o.rotulo.startsWith("Votou"))?.quantidade ?? 0;
  const publicados = d.secreta ? p.sim + p.nao + (p.abstencao ?? 0) : p.sim + p.nao;
  const listados = d.secreta ? votaramSecreto : d.placar.sim + d.placar.nao;
  const diferenca = p.daFonte && publicados > listados ? publicados - listados : 0;
  const rodape = <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />;
  const idProjeto = d.proposicao_id_externo ?? idDaProposicao(d.proposicao_url);

  const abas: AbaDetalhe[] = [
    {
      id: "partidos",
      rotulo: "Partidos",
      secoes: [{ id: "partidos", titulo: "Como cada partido orientou e votou", conteudo: <Partidos d={d} rodape={rodape} /> }],
    },
    {
      id: "parlamentares",
      rotulo: "Parlamentares",
      secoes: [
        {
          id: "parlamentares",
          titulo: `Como votou cada ${quem(d.casa, false)}`,
          conteudo: (
            <section aria-labelledby="parlamentares-titulo" className="flex flex-col gap-4">
              <div>
                <h3 id="parlamentares-titulo" className="text-2xl">
                  Como votou cada {quem(d.casa, false)}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {d.casa === "camara"
                    ? `${n(d.registros)} ${quem(d.casa, true)} registraram presença nesta votação, de ${n(d.cadeiras)} cadeiras. A Câmara só publica quem registrou.`
                    : `O Senado publica os ${n(d.cadeiras)} senadores, com o motivo de quem não votou. Aqui aparecem ${n(d.registros)}.`}
                </p>
              </div>
              <VotacaoParlamentares
                parlamentares={d.parlamentares}
                ordemPartidos={d.partidos.map((x) => x.partido)}
                casa={d.casa}
                porUf={d.por_uf ?? []}
                ufInicial={ufInicial}
              />
              {rodape}
            </section>
          ),
        },
      ],
    },
    {
      id: "discursos",
      rotulo: "O que disseram",
      secoes: [{ id: "discursos", titulo: "O que disseram", conteudo: <Discursos d={d} idProjeto={idProjeto} /> }],
    },
    {
      id: "proposicao",
      rotulo: "Proposição",
      secoes: [{ id: "proposicao", titulo: "O que estava em votação", conteudo: <Proposicao d={d} rodape={rodape} /> }],
    },
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="sobretitulo">
            Votação no Plenário {CASA_DA[d.casa]} · {formatarData(d.data)}
          </p>
          <h1 className="titulo-pagina">{d.proposicao ?? `Votação de ${formatarData(d.data)}`}</h1>
          {d.proposicao_ementa && <p className="text-lg leading-snug">{d.proposicao_ementa}</p>}
          <p className="text-sm text-muted-foreground">
            <span className="font-medium">Texto oficial da votação:</span> {d.descricao}
          </p>
        </div>

        <GradeCartoes rotulo="Números desta votação">
          <CartaoPlacar d={d} />
          <CartaoNumero
            destino="proposicao"
            rotulo="Resultado"
            valor={d.resultado ? RESULTADO[d.resultado] : "Não publicado"}
            apoio={formatarData(d.data)}
          />
          {d.secreta ? (
            <CartaoNumero
              destino="parlamentares"
              rotulo="Voto secreto"
              valor={n(votaramSecreto)}
              complemento="votaram"
              apoio="Só se sabe quem votou, não como"
            />
          ) : (
            <CartaoNumero
              destino="partidos"
              rotulo="O Governo orientou"
              valor={textoOrientacao(governo?.orientacao)}
              apoio={
                d.seguiram_governo.total
                  ? `${n(d.seguiram_governo.iguais)} de ${n(d.seguiram_governo.total)} votaram assim`
                  : governo
                    ? undefined
                    : `Sem orientação do Governo publicada`
              }
            />
          )}
          {!d.secreta && (
            <CartaoNumero
              destino="partidos"
              rotulo="Votaram como o próprio partido orientou"
              largo
              valor={d.seguiram_partido.total ? n(d.seguiram_partido.iguais) : "—"}
              complemento={d.seguiram_partido.total ? `de ${n(d.seguiram_partido.total)}` : undefined}
              apoio={d.seguiram_partido.total ? "Contando quem tinha orientação Sim, Não ou Obstrução" : "Nenhum partido orientou Sim, Não ou Obstrução"}
            />
          )}
        </GradeCartoes>
        <p className="text-sm text-muted-foreground">Toque num número para ver o detalhe, com a fonte e a data.</p>
        {idProjeto && (
          <Link href={`/projeto/${d.casa}/${idProjeto}`} className="botao-linha self-start">
            Ver tudo sobre o projeto
          </Link>
        )}
        <CompartilharWhatsApp
          caminho={`/votacao/${d.casa}/${d.id_externo}`}
          texto={`${d.proposicao ?? "Votação"} no ${casaCurta}: ${d.resultado ? `${RESULTADO[d.resultado].toLowerCase()}, ` : ""}Sim ${n(p.sim)} x Não ${n(p.nao)}. Veja como votou cada partido e cada parlamentar:`}
        />
      </div>

      <ListaPerguntas titulo="Para entender">
        <Pergunta
          id="entender-orientacao"
          pergunta="O que é orientação de bancada?"
          resposta="A recomendação do líder sobre como votar"
        >
          <p>
            Antes de cada votação, o líder do Governo, os líderes da Maioria, da Minoria e da Oposição e os líderes de cada
            partido, bloco ou federação dizem em microfone como recomendam que seu grupo vote: Sim, Não, Obstrução ou
            &quot;liberado&quot; (cada um vota como quiser). A orientação não obriga ninguém.
          </p>
          <p>
            Quando um partido não orienta sozinho, mostramos a orientação do bloco ou da federação de que ele faz parte,
            com o nome que a {casaCurta} publica (às vezes cortado, como &quot;Bl UniPpPsd...&quot;).
          </p>
          {rodape}
        </Pergunta>
        <Pergunta id="entender-obstrucao" pergunta="O que é obstrução?" resposta="Uma forma de tentar adiar a votação">
          <p>
            Quem está em obstrução se recusa a votar Sim ou Não para tentar impedir que se chegue ao número mínimo de
            presentes (quórum) e, assim, adiar a decisão. No registro, aparece como &quot;Obstrução&quot;. É um recurso
            previsto no regimento.
          </p>
        </Pergunta>
        <Pergunta
          id="entender-sem-voto"
          pergunta="Por que alguém aparece sem voto, ou não aparece?"
          resposta={d.casa === "camara" ? "A Câmara só publica quem registrou presença" : "O Senado publica o motivo de quem não votou"}
        >
          {d.casa === "camara" ? (
            <p>
              A lista da Câmara traz só os deputados que registraram presença na votação. Quem não aparece não registrou
              presença, e a Câmara não informa o motivo. Quem presidia a sessão aparece como &quot;Presidiu a sessão&quot;:
              pelo regimento, não vota.
            </p>
          ) : (
            <p>
              O Senado lista todos os senadores. Quem não votou aparece com o motivo informado: atividade parlamentar,
              licença, missão oficial, ou &quot;não compareceu&quot;. Quem presidia a sessão não vota.
            </p>
          )}
          {d.outros_registros.length > 0 && (
            <ul className="flex flex-col gap-1">
              {d.outros_registros.map((o) => (
                <li key={o.rotulo} className="flex justify-between gap-3">
                  <span>{o.rotulo}</span>
                  <span className="tabular-nums">{n(o.quantidade)}</span>
                </li>
              ))}
            </ul>
          )}
          {rodape}
        </Pergunta>
        <Pergunta
          id="entender-nominal"
          pergunta="O que quer dizer votação nominal?"
          resposta={d.secreta ? "Fica registrado quem votou; nesta, o voto é secreto" : "Cada voto fica registrado com o nome"}
        >
          <p>
            Na votação nominal, cada parlamentar vota no painel eletrônico e o voto fica público, com o nome. Muitas
            decisões são tomadas em votação simbólica, sem registro individual, e essas não aparecem aqui.
          </p>
          {d.secreta && (
            <p>
              Algumas votações são secretas por regra da Constituição (por exemplo, a escolha de autoridades). Nelas, a
              {" "}{casaCurta} publica quem votou e o placar total, mas não o voto de cada um.
            </p>
          )}
        </Pergunta>
        {diferenca > 0 && (
          <Pergunta
            id="entender-placar"
            pergunta="Por que a lista soma menos que o placar?"
            resposta={`${n(diferenca)} ${diferenca === 1 ? "voto é" : "votos são"} de quem não está no nosso cadastro`}
          >
            <p>
              O placar do topo é o publicado pela {casaCurta}: Sim {n(p.sim)}, Não {n(p.nao)}
              {p.abstencao != null ? `, abstenção ${n(p.abstencao)}` : ""}.{" "}
              {d.secreta
                ? `Na lista desta página, ${n(listados)} aparecem como "votou".`
                : `Na lista nominal desta página aparecem Sim ${n(d.placar.sim)} e Não ${n(d.placar.nao)}.`}{" "}
              A lista só traz quem está no nosso cadastro de parlamentares; os votos de quem já deixou o cargo (por
              exemplo, um suplente que votou e depois saiu) ficam de fora dela, mas contam no placar.
            </p>
            {rodape}
          </Pergunta>
        )}
      </ListaPerguntas>

      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />
    </article>
  );
}

/** Cartão largo do placar: Sim x Não numa barra só (bronze e cinza), com os outros números ao lado. */
function CartaoPlacar({ d }: { d: VotacaoDetalhe }) {
  const p = placarPrincipal(d);
  const total = p.sim + p.nao;
  const extras = [
    p.abstencao ? `${n(p.abstencao)} ${p.abstencao === 1 ? "abstenção" : "abstenções"}` : null,
    p.obstrucao ? `${n(p.obstrucao)} em obstrução` : null,
  ].filter(Boolean);
  return (
    <li className="col-span-2 min-w-0">
      <a
        href="#ver-parlamentares"
        className="flex h-full min-h-11 min-w-0 flex-col gap-2 rounded-[var(--radius)] border border-border bg-card p-3 transition-colors duration-200 hover:border-foreground/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze sm:p-4"
      >
        <span className="text-sm leading-snug text-muted-foreground">Placar</span>
        <span className="numero text-[1.375rem] leading-none sm:text-[1.625rem]">
          {n(p.sim)} <span className="text-base text-muted-foreground">Sim</span> × {n(p.nao)}{" "}
          <span className="text-base text-muted-foreground">Não</span>
        </span>
        {total > 0 && (
          <div
            role="img"
            aria-label={`Sim ${n(p.sim)}, Não ${n(p.nao)}`}
            className="flex h-2 w-full gap-px overflow-hidden rounded-[2px] bg-muted"
          >
            <span className="h-full bg-bronze" style={{ flexGrow: p.sim }} />
            <span className="h-full bg-chart-3" style={{ flexGrow: p.nao }} />
          </div>
        )}
        <span className="text-sm text-muted-foreground tabular-nums">
          {[...extras, p.daFonte ? `placar publicado ${CASA_DA[d.casa]}` : "contagem da lista nominal"].join(" · ")}
        </span>
        <span className="mt-auto pt-1 text-sm text-bronze-texto" aria-hidden>
          Ver detalhe ›
        </span>
      </a>
    </li>
  );
}

function Partidos({ d, rodape }: { d: VotacaoDetalhe; rodape: React.ReactNode }) {
  const membros = quem(d.casa, true);
  // Na votação secreta só se sabe quem votou: contamos por partido a partir da lista.
  const votaramNoPartido = new Map<string, number>();
  if (d.secreta) {
    for (const x of d.parlamentares) {
      if (x.registro.startsWith("Votou")) votaramNoPartido.set(x.partido, (votaramNoPartido.get(x.partido) ?? 0) + 1);
    }
  }
  return (
    <section aria-labelledby="partidos-titulo" className="flex flex-col gap-5">
      <div>
        <h3 id="partidos-titulo" className="text-2xl">
          Como cada partido orientou e votou
        </h3>
        <p className="text-sm text-muted-foreground">
          Partidos em ordem do número de {membros} nesta votação (empate em ordem alfabética).
        </p>
        {d.secreta && (
          <p className="nota mt-3 text-sm">
            Votação secreta: a {CASA_CURTA[d.casa]} não publica o voto de cada um nem a orientação dos partidos. Abaixo,
            quantos de cada partido votaram.
          </p>
        )}
      </div>

      {d.liderancas.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-base font-semibold">Orientação das lideranças</h4>
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {d.liderancas.map((l) => (
              <div key={l.bancada} className="figura flex flex-col gap-0.5">
                <dt className="text-sm text-muted-foreground">{l.bancada}</dt>
                <dd className="font-semibold">{textoOrientacao(l.orientacao)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <ul className="lista-fios">
        {d.partidos.map((x) => (
          <li key={x.partido} className="flex flex-col gap-1 py-3">
            <p className="flex items-baseline justify-between gap-3">
              <span className="font-semibold">{x.partido}</span>
              <span className="text-sm text-muted-foreground tabular-nums">
                {n(x.parlamentares)} {x.parlamentares === 1 ? quem(d.casa, false) : membros}
              </span>
            </p>
            {!d.secreta && (
              <p className="text-sm">
                Orientação: <span className="font-semibold">{textoOrientacao(x.orientacao)}</span>
                {x.orientacao_por && (
                  <span className="text-muted-foreground"> (pelo grupo &quot;{x.orientacao_por}&quot;)</span>
                )}
              </p>
            )}
            {d.secreta ? (
              <p className="text-sm tabular-nums">
                {n(votaramNoPartido.get(x.partido) ?? 0)} votaram
                {x.parlamentares - (votaramNoPartido.get(x.partido) ?? 0) > 0 &&
                  ` · ${n(x.parlamentares - (votaramNoPartido.get(x.partido) ?? 0))} não votaram`}
              </p>
            ) : (
              <p className="text-sm tabular-nums">
                {[
                  `${n(x.sim)} sim`,
                  `${n(x.nao)} não`,
                  x.abstencao ? `${n(x.abstencao)} abstenção` : null,
                  x.obstrucao ? `${n(x.obstrucao)} obstrução` : null,
                  x.outros ? `${n(x.outros)} sem voto` : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
            {x.seguiram != null && x.votos_efetivos > 0 && (
              <p className="text-sm text-muted-foreground tabular-nums">
                {n(x.seguiram)} de {n(x.votos_efetivos)} votaram como a orientação
              </p>
            )}
          </li>
        ))}
      </ul>

      {d.outras_bancadas.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-base font-semibold">Blocos, federações e outras bancadas</h4>
          <p className="text-sm text-muted-foreground">
            Com o nome como a {CASA_CURTA[d.casa]} publica. A composição vem da lista de blocos da própria Câmara, quando o
            nome publicado casa com um só bloco dela; a lista oficial é a atual, sem datas.
          </p>
          <ul className="lista-fios">
            {d.outras_bancadas.map((b) => (
              <li key={b.bancada} className="flex flex-col gap-0.5 py-2">
                <p className="flex items-baseline justify-between gap-3">
                  <span className="font-medium">{b.bancada}</span>
                  <span className="font-semibold">{textoOrientacao(b.orientacao)}</span>
                </p>
                <p className="text-sm text-muted-foreground">
                  {b.tipo === "federacao" ? "Federação" : b.tipo === "bloco" ? "Bloco" : "Bancada"}
                  {b.partidos.length > 0 ? `: ${b.partidos.join(", ")}` : " (composição não publicada)"}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
      {rodape}
    </section>
  );
}

function Discursos({ d, idProjeto }: { d: VotacaoDetalhe; idProjeto: string | null }) {
  const projeto = idProjeto ? `/projeto/${d.casa}/${idProjeto}` : null;
  const disc = d.discursos;
  return (
    <section aria-labelledby="discursos-titulo" className="flex flex-col gap-4">
      <h3 id="discursos-titulo" className="text-2xl">
        O que disseram
      </h3>
      {disc ? (
        <>
          <AvisoDiscursos extra="Discursos de Plenário deste dia sobre o projeto, separados pelo voto que quem discursou registrou nesta votação." />
          <GruposDeDiscursos grupos={disc.grupos} />
          <FonteRodape fonte={disc.fonte_nome} url={disc.fonte_url} atualizadoEm={disc.atualizado_em} />
        </>
      ) : (
        <p className="nota text-sm">
          Os discursos desse dia aparecem na última votação do projeto naquele dia, para não ligar a fala a uma votação que
          não é a dela. {projeto && "Veja todos na página do projeto."}
        </p>
      )}
      {projeto && (
        <Link href={projeto} className="alvo-link self-start font-medium underline underline-offset-4">
          Ver tudo sobre o projeto
        </Link>
      )}
    </section>
  );
}

function Proposicao({ d, rodape }: { d: VotacaoDetalhe; rodape: React.ReactNode }) {
  return (
    <section aria-labelledby="proposicao-titulo" className="flex flex-col gap-4">
      <h3 id="proposicao-titulo" className="text-2xl">
        O que estava em votação
      </h3>
      {d.proposicao && <p className="font-semibold">{d.proposicao}</p>}
      {d.proposicao_ementa ? (
        <p className="leading-relaxed">{d.proposicao_ementa}</p>
      ) : (
        <p className="text-muted-foreground">A fonte não traz o resumo (ementa) desta proposição.</p>
      )}
      {d.temas.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Temas (classificação oficial)</p>
          <ul className="flex flex-wrap gap-2">
            {d.temas.map((t) => (
              <li key={t} className="pilula">
                {t}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="nota flex flex-col gap-1">
        <p className="text-sm font-medium">Texto oficial da votação</p>
        <p className="text-sm text-muted-foreground">{d.descricao}</p>
      </div>
      {d.proposicao_url && (
        <a
          href={d.proposicao_url}
          target="_blank"
          rel="noopener noreferrer"
          className="alvo-link self-start font-medium underline underline-offset-4"
        >
          Ficha da proposição no site {CASA_DA[d.casa]}
        </a>
      )}
      {rodape}
    </section>
  );
}
