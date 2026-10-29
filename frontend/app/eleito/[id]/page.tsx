import type { Metadata } from "next";
import Link from "next/link";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { notFound, redirect } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { SeloEleitoFuturo } from "@/components/eleito-futuro";
import { CarreiraSecao } from "@/components/carreira-secao";
import { SancoesSecao, TEXTO_REGISTRO } from "@/components/sancoes-secao";
import { ServicoFederalSecao } from "@/components/servico-federal-secao";
import { CandidaturaSecao } from "@/components/candidatura-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { QuemESecao } from "@/components/dados-pessoais";
import { FotoOuIniciais } from "@/components/eleitos-secao";
import { ContratosSocioSecao } from "@/components/contratos-socio-secao";
import { LinhaDoTempoSecao } from "@/components/linha-do-tempo-secao";
import { Revelacao } from "@/components/revelacao";
import { FonteRodape } from "@/components/fonte-rodape";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { formatarNumero } from "@/components/painel/barra-comparacao";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { AgendaSecao } from "@/components/executivo-agenda";
import { AtosPresidenciaisSecao } from "@/components/executivo-atos";
import {
  AvisoDoGoverno,
  BlocoIndisponivel,
  ContasDoGoverno,
  ContratosDaCidade,
  EmendasDaCidade,
  comparacaoContas,
  nomeDoGoverno,
  num,
  rotuloPeriodo,
} from "@/components/executivo-dinheiro";
import {
  type EleitoDetalhe,
  getAgenda,
  getAtosPresidente,
  getCanais,
  getCarreira,
  getContasEstado,
  getEleito,
  getLinhaDoTempo,
  getPainelExecutivo,
  getSancoes,
  urlFotoDe,
} from "@/lib/api";
import { formatarData, formatarReais, formatarReaisCompacto } from "@/lib/formato";
import { JsonLdPerfil, montarDescricao, nomeComSigla } from "@/components/json-ld";
import { LinkExterno } from "@/components/link-externo";

export async function generateMetadata({ params }: PageProps<"/eleito/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getEleito(id);
  if (!resultado.ok) return { title: "Eleito" };
  const e = resultado.dados;
  // Candidatura nova de quem já tem perfil: quem indexa deve guardar o perfil principal.
  if (e.perfil_principal) return { title: e.nome_urna, alternates: { canonical: e.perfil_principal } };
  const bens = e.bens && e.bens.quantidade > 0 ? e.bens.total : null;
  const descricao = montarDescricao([
    `${e.cargo} em ${e.unidade}${e.ano_eleicao ? `, eleição de ${e.ano_eleicao}` : ""}.`,
    bens !== null && bens > 0 && `Declarou bens de ${formatarReais(bens, true)} ao TSE.`,
    "Contas de campanha e bens declarados.",
  ], "Dados oficiais do TSE com fonte.");
  return {
    title: `${nomeComSigla(e.nome_urna, e.partido, e.uf)}: ${e.cargo.toLowerCase()}, bens e contas de campanha`,
    description: descricao,
    openGraph: { title: `${e.nome_urna} · ${e.cargo}`, description: descricao },
  };
}

async function DadosEstruturados({ id }: { id: string }) {
  const resultado = await getEleito(id);
  if (!resultado.ok || resultado.dados.mandato_local || resultado.dados.perfil_principal) return null;
  const e = resultado.dados;
  return (
    <JsonLdPerfil
      caminho={`/eleito/${e.id}`}
      nome={e.nome_urna}
      cargo={e.cargo}
      casa={e.unidade}
      partido={e.partido}
      uf={e.uf}
      imagem={e.foto ? urlFotoDe(e) : null}
    />
  );
}

const CARGO_EXECUTIVO = /^(vice-)?(presidente|governador|prefeito)/i;

function texto(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

export default function EleitoPage({ params, searchParams }: PageProps<"/eleito/[id]">) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o perfil…" secoes={3} />}>
      {Promise.all([params, searchParams]).then(([{ id }, sp]) => (
        <>
          <DadosEstruturados id={id} />
          <Perfil
            id={id}
            agendaTipo={texto(sp.agenda_tipo)}
            agendaAno={texto(sp.agenda_ano)}
            agendaPagina={texto(sp.agenda_pagina)}
            mpvGrupo={texto(sp.mpv_grupo)}
            mpvPagina={texto(sp.mpv_pagina)}
            vetoGrupo={texto(sp.veto_grupo)}
            vetoPagina={texto(sp.veto_pagina)}
          />
        </>
      ))}
    </Revelacao>
  );
}

async function Perfil({
  id,
  agendaTipo,
  agendaAno,
  agendaPagina,
  mpvGrupo,
  mpvPagina,
  vetoGrupo,
  vetoPagina,
}: {
  id: string;
  agendaTipo?: string;
  agendaAno?: string;
  agendaPagina?: string;
  mpvGrupo?: string;
  mpvPagina?: string;
  vetoGrupo?: string;
  vetoPagina?: string;
}) {
  const resultado = await getEleito(id);
  if (!resultado.ok) {
    if (resultado.status === 404) notFound();
    return <AvisoErro titulo="Não deu para carregar" mensagem={resultado.mensagem} />;
  }
  const e = resultado.dados;
  // Eleito de novo (ou no 2º turno) por quem já tem perfil: um perfil só, com os dados de 2026
  // dentro dele. A página da candidatura nova não abre; o redirecionamento é temporário porque
  // o perfil principal muda com a posse.
  if (e.perfil_principal) redirect(e.perfil_principal);
  if (e.mandato_local) {
    redirect(`/${e.mandato_local.casa === "camara" ? "vereador" : "deputado-estadual"}/${e.mandato_local.id}`);
  }
  const executivo = CARGO_EXECUTIVO.test(e.cargo);
  const [canais, linha, painelR] = await Promise.all([
    e.municipio_ibge ? getCanais(e.municipio_ibge) : null,
    getLinhaDoTempo("candidatura", id),
    executivo ? getPainelExecutivo(id) : null,
  ]);
  // API antiga sem a rota do painel: o perfil cai no comportamento de antes.
  const painel = painelR?.ok ? painelR.dados : null;
  // Medidas provisórias e vetos: só o Presidente do mandato em curso (eleito em 2022); vice,
  // ex-presidentes e candidatos de outras eleições não têm a seção.
  const comAtos = painel?.ente.tipo === "uniao" && painel.titular && painel.ano_eleicao === 2022;
  const [contasEstadoR, agendaR, mpvR, vetoR] = await Promise.all([
    painel?.ente.tipo === "estado" && painel.contas.disponivel && painel.ente.uf ? getContasEstado(painel.ente.uf) : null,
    painel?.ente.tipo === "uniao" && painel.agenda.disponivel
      ? getAgenda(id, { tipo: agendaTipo, ano: agendaAno, pagina: agendaPagina })
      : null,
    comAtos && painel.medidas_provisorias.disponivel
      ? getAtosPresidente(id, { tipo: "mpv", grupo: mpvGrupo, pagina: mpvPagina })
      : null,
    comAtos && painel.vetos.disponivel
      ? getAtosPresidente(id, { tipo: "veto", grupo: vetoGrupo, pagina: vetoPagina })
      : null,
  ]);
  const temSapl = Boolean(canais?.ok && canais.dados.itens.some((c) => c.tipo === "sapl"));
  const voltar = e.municipio_ibge
    ? `/representantes?municipio=${e.municipio_ibge}`
    : e.uf === "BR"
      ? "/"
      : `/representantes?uf=${e.uf}`;

  const pessoaId = linha.ok ? linha.dados.pessoa_id : null;
  const [sancoes, carreira] = await Promise.all([
    pessoaId !== null ? getSancoes(pessoaId) : null,
    pessoaId !== null ? getCarreira(pessoaId) : null,
  ]);
  const emCargoFuturo = e.eleito_2026?.id === e.id;
  const recente = e.eleicao_recente ?? null;
  const posseRecente = recente ? `a da eleição para o mandato que começa em ${recente.ano_eleicao + 1}` : undefined;
  const disputadas = carreira?.ok ? carreira.dados.itens.length : 0;

  const abas: AbaDetalhe[] = [];
  if (painel) {
    const d = painel.ente.tipo;
    const secoesGoverno: AbaDetalhe["secoes"] = [
      {
        id: "gov-contas",
        titulo: "Contas do governo",
        conteudo: painel.contas.disponivel ? (
          <ContasDoGoverno painel={painel} estado={contasEstadoR?.ok ? contasEstadoR.dados : null} />
        ) : (
          <BlocoIndisponivel titulo="Contas do governo" bloco={painel.contas} painel={painel} />
        ),
      },
      {
        id: "gov-emendas",
        titulo: "Emendas recebidas",
        conteudo: painel.emendas.disponivel ? (
          <EmendasDaCidade painel={painel} />
        ) : (
          <BlocoIndisponivel titulo="Emendas recebidas" bloco={painel.emendas} painel={painel} />
        ),
      },
      {
        id: "gov-contratos",
        titulo: "Contratos",
        conteudo: painel.contratos.disponivel ? (
          <ContratosDaCidade painel={painel} />
        ) : (
          <BlocoIndisponivel titulo="Contratos" bloco={painel.contratos} painel={painel} />
        ),
      },
    ];
    if (d === "uniao") {
      secoesGoverno.push(
        {
          id: "gov-viagens",
          titulo: "Viagens e cartão de pagamento",
          conteudo: painel.viagens_cartao.disponivel ? (
            <section className="flex flex-col gap-1">
              <h2 className="text-2xl">Viagens e cartão de pagamento</h2>
              <p className="text-sm">
                Há registros no Portal da Transparência. Veja em{" "}
                <a href="#ver-servico-federal" className="alvo-link underline underline-offset-2">
                  Trabalho no governo federal
                </a>
                .
              </p>
              <FonteRodape
                fonte={painel.viagens_cartao.fonte_nome ?? "Portal da Transparência"}
                url={painel.viagens_cartao.fonte_url ?? undefined}
                atualizadoEm={painel.viagens_cartao.atualizado_em}
              />
            </section>
          ) : (
            <BlocoIndisponivel titulo="Viagens e cartão de pagamento" bloco={painel.viagens_cartao} painel={painel} />
          ),
        },
      );
    }
    abas.push({ id: "governo", rotulo: "Dinheiro do governo", secoes: secoesGoverno });
    if (comAtos) {
      abas.push({
        id: "atos",
        rotulo: "Medidas e vetos",
        secoes: [
          {
            id: "gov-mpv",
            titulo: "Medidas provisórias",
            conteudo: painel.medidas_provisorias.disponivel ? (
              <AtosPresidenciaisSecao
                tipo="mpv"
                bloco={painel.medidas_provisorias}
                lista={mpvR?.ok ? mpvR.dados : null}
                candidaturaId={painel.candidatura_id}
                outroFiltro={{ veto_grupo: vetoGrupo, veto_pagina: vetoPagina }}
              />
            ) : (
              <BlocoIndisponivel titulo="Medidas provisórias" bloco={painel.medidas_provisorias} painel={painel} />
            ),
          },
          {
            id: "gov-vetos",
            titulo: "Vetos",
            conteudo: painel.vetos.disponivel ? (
              <AtosPresidenciaisSecao
                tipo="veto"
                bloco={painel.vetos}
                lista={vetoR?.ok ? vetoR.dados : null}
                candidaturaId={painel.candidatura_id}
                outroFiltro={{ mpv_grupo: mpvGrupo, mpv_pagina: mpvPagina }}
              />
            ) : (
              <BlocoIndisponivel titulo="Vetos" bloco={painel.vetos} painel={painel} />
            ),
          },
        ],
      });
    }
    if (d === "uniao") {
      abas.push({
        id: "agenda-aba",
        rotulo: "Agenda",
        secoes: [
          {
            id: "agenda",
            titulo: "Agenda de compromissos",
            conteudo: agendaR?.ok ? (
              <AgendaSecao dados={agendaR.dados} candidaturaId={painel.candidatura_id} tipo={agendaTipo} ano={agendaAno} />
            ) : (
              <BlocoIndisponivel
                titulo="Agenda de compromissos"
                bloco={painel.agenda.disponivel ? { ...painel.agenda, motivo: "Não deu para buscar a agenda agora." } : painel.agenda}
                painel={painel}
              />
            ),
          },
        ],
      });
    }
  }
  abas.push(
    {
      id: "dinheiro",
      rotulo: "Dinheiro",
      secoes: [
        {
          id: "candidatura",
          titulo: "Candidatura e bens",
          conteudo: (
            <>
              <CandidaturaSecao dados={e} />
              {!e.bens && !e.campanha && !recente?.bens && !recente?.campanha && (
                <p className="text-muted-foreground">
                  O TSE não tem bens nem contas de campanha registrados para esta candidatura.
                </p>
              )}
            </>
          ),
        },
        {
          id: "candidatura-recente",
          titulo: recente ? `Candidatura e bens de ${recente.ano_eleicao}` : "Candidatura e bens",
          conteudo: recente && (
            <CandidaturaSecao
              dados={recente}
              idTitulo="tse-recente-titulo"
              titulo={`Eleição de ${recente.ano_eleicao}`}
              posse={posseRecente}
            />
          ),
        },
        {
          id: "contratos-socio",
          titulo: "Contratos de empresas de que é sócio",
          conteudo: pessoaId !== null && <ContratosSocioSecao pessoaId={pessoaId} />,
        },
      ],
    },
    {
      id: "ficha",
      rotulo: "Ficha",
      secoes: [
        {
          id: "quem-e",
          titulo: "Quem é",
          conteudo: (
            <QuemESecao pessoais={recente?.pessoais ?? e.pessoais} votos={e.votos != null ? { ano: e.ano_eleicao, total: e.votos } : null} />
          ),
        },
        {
          id: "carreira",
          titulo: "Eleições disputadas",
          conteudo: pessoaId !== null && <CarreiraSecao pessoaId={pessoaId} />,
        },
        {
          id: "linha-do-tempo",
          titulo: "Linha do tempo",
          conteudo: linha.ok && <LinhaDoTempoSecao dados={linha.dados} />,
        },
        {
          id: "servico-federal",
          titulo: "Trabalho no governo federal",
          conteudo: pessoaId !== null && <ServicoFederalSecao pessoaId={pessoaId} />,
        },
      ],
    },
    {
      id: "justica",
      rotulo: "Justiça",
      secoes: [
        {
          id: "sancoes",
          titulo: "Punições e contas reprovadas",
          conteudo: pessoaId !== null && <SancoesSecao pessoaId={pessoaId} explicacao="#entender-registro" />,
        },
      ],
    },
  );

  return (
    <article data-largura="larga" className="pagina-secoes">
      <header className="flex items-start gap-4">
        <FotoOuIniciais eleito={e} tamanho={72} legenda />
        <div className="flex min-w-0 flex-col gap-1">
          <p className="sobretitulo">Eleito</p>
          <h1 className="titulo-pagina">{e.nome_urna}</h1>
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

      {e.eleito_2026 && <SeloEleitoFuturo eleito={e.eleito_2026} atualizadoEm={e.atualizado_em} />}

      {e.depois && e.depois.id !== e.eleito_2026?.id && (
        <p className="text-sm">
          Eleito depois para{" "}
          <Link href={`/eleito/${e.depois.id}`} className="font-medium underline underline-offset-2">
            {e.depois.cargo.toLowerCase()} de {e.depois.unidade}
          </Link>{" "}
          em {e.depois.ano}.
        </p>
      )}

      {painel && <AvisoDoGoverno painel={painel} />}

      <GradeCartoes rotulo="Números principais">
        {painel?.contas.disponivel && painel.ente.tipo !== "uniao" && (
          <CartaoNumero
            destino="gov-contas"
            rotulo={`${painel.ente.nome}: gasto por habitante em ${num(painel.contas.dados, "ano")}`}
            valor={
              num(painel.contas.dados, "despesa_por_habitante") != null
                ? formatarReais(num(painel.contas.dados, "despesa_por_habitante")!, true)
                : "Não informado pela fonte"
            }
            apoio={painel.titular ? `Contas de ${nomeDoGoverno(painel)}` : `Número do governo, não do vice`}
            largo
            comparacao={comparacaoContas(painel).comparacao}
          />
        )}
        {painel?.emendas.disponivel && num(painel.emendas.dados, "total_geral") != null && (
          <CartaoNumero
            destino="gov-emendas"
            rotulo={`Emendas recebidas pela cidade ${rotuloPeriodo(painel.emendas.dados)}`}
            valor={formatarReaisCompacto(num(painel.emendas.dados, "total_geral")!)}
            apoio="Todos os tipos de emenda"
          />
        )}
        {comAtos && painel.medidas_provisorias.disponivel && num(painel.medidas_provisorias.dados, "total") != null && (
          <CartaoNumero
            destino="gov-mpv"
            rotulo="Medidas provisórias editadas desde a posse (2023)"
            valor={String(num(painel.medidas_provisorias.dados, "total"))}
            apoio="Mandato atual, sem média"
          />
        )}
        {comAtos && painel.vetos.disponivel && num(painel.vetos.dados, "total") != null && (
          <CartaoNumero
            destino="gov-vetos"
            rotulo="Vetos desde a posse (2023)"
            valor={String(num(painel.vetos.dados, "total"))}
            apoio="Mandato atual, sem média"
          />
        )}
        {e.votos != null && (
          <CartaoNumero
            destino="quem-e"
            rotulo={`Votos recebidos em ${e.ano_eleicao}`}
            valor={formatarNumero(e.votos, "inteiro")}
            apoio="Número informado pelo TSE"
          />
        )}
        {e.bens && (
          <CartaoNumero
            destino="candidatura"
            rotulo={`Bens declarados em ${e.bens.candidatura.ano}`}
            valor={formatarReaisCompacto(e.bens.total)}
            apoio={
              e.bens.anterior
                ? `Em ${e.bens.anterior.candidatura.ano}: ${formatarReaisCompacto(e.bens.anterior.total)}`
                : "Valor informado ao TSE"
            }
          />
        )}
        {recente?.bens && (
          <CartaoNumero
            destino="candidatura-recente"
            rotulo={`Bens declarados em ${recente.bens.candidatura.ano}`}
            valor={formatarReaisCompacto(recente.bens.total)}
            apoio={
              recente.bens.anterior
                ? `Em ${recente.bens.anterior.candidatura.ano}: ${formatarReaisCompacto(recente.bens.anterior.total)}`
                : "Valor informado ao TSE"
            }
          />
        )}
        {recente?.campanha && (
          <CartaoNumero
            destino="candidatura-recente"
            rotulo={`Dinheiro arrecadado na campanha de ${recente.campanha.candidatura.ano}`}
            valor={formatarReaisCompacto(recente.campanha.receitas_total)}
            apoio={`Gasto declarado: ${formatarReaisCompacto(recente.campanha.despesas_total)}`}
          />
        )}
        {e.campanha && (
          <CartaoNumero
            destino="candidatura"
            rotulo={`Dinheiro arrecadado na campanha de ${e.campanha.candidatura.ano}`}
            valor={formatarReaisCompacto(e.campanha.receitas_total)}
            apoio={`Gasto declarado: ${formatarReaisCompacto(e.campanha.despesas_total)}`}
          />
        )}
        {disputadas > 0 && (
          <CartaoNumero destino="carreira" rotulo="Eleições que disputou" valor={String(disputadas)} apoio="Candidaturas no TSE" />
        )}
        {sancoes?.ok && (
          <CartaoNumero
            destino="sancoes"
            rotulo="Registros na CGU e no TCU"
            valor={sancoes.dados.itens.length === 0 ? "Nenhum" : String(sancoes.dados.itens.length)}
            apoio={sancoes.dados.atualizado_em ? `Consulta de ${formatarData(sancoes.dados.atualizado_em)}` : undefined}
          />
        )}
      </GradeCartoes>
      <p className="text-sm text-muted-foreground">Toque ou clique num número para ver o detalhe, com a fonte e a data.</p>

      <CompartilharWhatsApp caminho={`/eleito/${e.id}`} texto={textoWhatsApp(e)} />

      <ListaPerguntas titulo="Para entender os números">
        {!emCargoFuturo && (
          <Pergunta
            id="entender-cargo"
            pergunta="Por que não aparecem os gastos e os votos no cargo?"
            resposta="Aqui aparece o que o TSE publica sobre a eleição"
          >
            <p>
              {e.cargo !== "Vereador"
                ? painel
                  ? `Os votos e as decisões do cargo ainda não estão no site. Aparece o que o TSE publica sobre a eleição e, em "Dinheiro do governo", os números de ${nomeDoGoverno(painel)}, que valem para o governo e não só para quem ocupa o cargo.`
                  : `${atividade(e.cargo)} ainda não estão no site. Por enquanto, aparece o que o TSE publica sobre a eleição.`
                : temSapl
                  ? `A câmara de ${e.unidade} publica quem está no cargo hoje, mas este nome não aparece na lista dela: a pessoa pode ter deixado o cargo ou usar lá outro nome. Veja a lista da câmara na página da cidade.`
                  : `A câmara de ${e.unidade} não publica votações e projetos num formato de dados abertos que o Panóptico consiga ler (o sistema SAPL, do Interlegis). Por isso, aqui aparece só o que o TSE publica sobre a eleição.`}{" "}
              Mudanças depois da eleição (suplente que assumiu, renúncia, cassação) também não aparecem aqui.
            </p>
            {canais?.ok && canais.dados.itens.length > 0 && (
              <div className="flex flex-col gap-1">
                <p>Os canais oficiais da cidade:</p>
                <ul className="flex flex-wrap gap-x-4 gap-y-1">
                  {canais.dados.itens.map((c) => (
                    <li key={c.tipo}>
                      <LinkExterno
                        href={c.url}
                        className="alvo-link underline underline-offset-2"
                      >
                        {NOME_CANAL[c.tipo] ?? c.tipo}
                      </LinkExterno>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Pergunta>
        )}
        {(e.bens || e.campanha || recente?.bens || recente?.campanha) && (
          <Pergunta
            id="entender-bens"
            pergunta="De onde vêm os bens e o dinheiro da campanha?"
            resposta="Do que a pessoa declarou ao TSE ao se candidatar"
          >
            <p>
              Os bens são os que a própria pessoa declarou ao registrar a candidatura, com o valor que ela informou. As
              receitas e despesas vêm da prestação de contas da campanha. O TSE não confere o valor de mercado dos bens.
            </p>
            <FonteRodape fonte={e.fonte_nome} url={e.fonte_url} atualizadoEm={e.atualizado_em} />
          </Pergunta>
        )}
        {pessoaId !== null && (
          <Pergunta
            id="entender-registro"
            pergunta="O que é um registro na CGU e no TCU?"
            resposta="Uma punição ou decisão que um órgão público registrou"
          >
            <p>
              A Controladoria-Geral da União (CGU) mantém os cadastros de quem foi punido por órgãos públicos{" "}
              <span className="text-muted-foreground">(CEIS, CNEP e CEAF)</span>. O Tribunal de Contas da União (TCU)
              publica quem teve as contas julgadas irregulares ou foi proibido de exercer cargo público.
            </p>
            <p>{TEXTO_REGISTRO}</p>
            <p>
              <a href="#ver-sancoes" className="alvo-link underline underline-offset-2">
                Ver os registros desta pessoa
              </a>
            </p>
          </Pergunta>
        )}
      </ListaPerguntas>

      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />

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
  if (cargo.includes("Prefeito")) return "As decisões da prefeitura";
  if (cargo.includes("Governador")) return "As decisões do governo do estado";
  return "As decisões do governo federal";
}

function textoWhatsApp(e: EleitoDetalhe): string {
  const votos = e.votos != null ? `${e.votos.toLocaleString("pt-BR")} votos` : null;
  if (e.bens && votos) {
    return `${e.nome_urna} declarou ${formatarReais(e.bens.total, true)} em bens ao TSE em ${e.bens.candidatura.ano} e recebeu ${votos}. Veja o perfil com dados oficiais:`;
  }
  if (e.bens) {
    return `${e.nome_urna} declarou ${formatarReais(e.bens.total, true)} em bens ao TSE em ${e.bens.candidatura.ano}. Veja o perfil com dados oficiais:`;
  }
  if (votos) return `${e.nome_urna} recebeu ${votos} em ${e.ano_eleicao}, segundo o TSE. Veja o perfil com dados oficiais:`;
  return `Veja os bens e a campanha de ${e.nome_urna} (${e.cargo.toLowerCase()}, ${e.unidade}), com dados oficiais do TSE:`;
}
