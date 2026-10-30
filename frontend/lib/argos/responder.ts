/**
 * Transforma os dados da API em mensagens do Argos. Funções puras (testadas no Vitest): não
 * chamam a rede nem sabem de tela. Toda resposta com número leva fonte e data; a média da Casa
 * vem ao lado do número. Linguagem factual: sem adjetivo, sem juízo.
 */
import type { Casa, Gastos, Presenca, Projetos, Representantes, RespostaBusca, ResultadoBusca } from "@/lib/api";
import { CASA_DA, FONTE_CASA, MESES, formatarReais } from "@/lib/formato";
import { PERGUNTAS_FREQUENTES } from "@/lib/perguntas";

import { normalizar } from "./interpretar";
import type { AssuntoPessoa, Botao, Mensagem, PessoaLembrada } from "./tipos";
import { EXEMPLOS, TEXTOS } from "./vocabulario";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const NUM = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

const SEM_BOTOES: Botao[] = [];

function botoesExemplo(): Botao[] {
  return EXEMPLOS.map((e) => ({ rotulo: e, frase: e }));
}

// ---------- Fixas ----------

export function saudacao(): Mensagem {
  return {
    texto: TEXTOS.apresentacao,
    links: [{ rotulo: "Como o site funciona", href: "/o-panoptico" }],
    botoes: botoesExemplo(),
  };
}

export function opiniao(): Mensagem {
  return { texto: TEXTOS.opiniao, links: [], botoes: botoesExemplo() };
}

export function naoEntendi(): Mensagem {
  return {
    texto: TEXTOS.naoEntendi,
    links: [{ rotulo: "Busca por nome no site", href: "/parlamentares" }],
    botoes: botoesExemplo(),
  };
}

export function pedirCep(): Mensagem {
  return { texto: TEXTOS.pedirCep, links: [], botoes: SEM_BOTOES };
}

export function semRanking(): Mensagem {
  return {
    texto:
      "O site não faz ranking nem compara quem gastou mais ou menos. Na lista de parlamentares dá para ordenar por gastos, presença e projetos, sempre com a fonte e a média da Casa ao lado.",
    links: [{ rotulo: "Lista de parlamentares, com ordenação", href: "/parlamentares" }],
    botoes: SEM_BOTOES,
  };
}

export function pedirNome(): Mensagem {
  return { texto: TEXTOS.pedirNome, links: [], botoes: SEM_BOTOES };
}

export function erroDeRede(): Mensagem {
  return { texto: TEXTOS.erroRede, links: [], botoes: SEM_BOTOES, erro: true };
}

/** Erro da API: 404 e 422 trazem uma mensagem pensada para o cidadão; o resto vira o aviso geral. */
export function erroDaApi(status: number, mensagem: string): Mensagem {
  if (status === 404 || status === 422) {
    return { texto: mensagem, links: [], botoes: SEM_BOTOES, erro: true };
  }
  return erroDeRede();
}

// ---------- Dúvidas sobre o site ----------

export function respostaSite(perguntaId: string | undefined): Mensagem {
  const p = PERGUNTAS_FREQUENTES.find((x) => x.id === perguntaId);
  if (!p) {
    return {
      texto:
        "O Panóptico mostra quem te representa, de presidente a vereador, e o que cada um faz, gasta e vota, com dado oficial, link da fonte e data. Não dá nota nem ranking.",
      links: [
        { rotulo: "O que é o Panóptico", href: "/o-panoptico" },
        { rotulo: "Perguntas frequentes", href: "/perguntas" },
      ],
      botoes: SEM_BOTOES,
    };
  }
  return {
    texto: p.texto,
    links: [{ rotulo: "Ver em Perguntas frequentes", href: `/perguntas#${p.id}` }],
    botoes: SEM_BOTOES,
  };
}

// ---------- Busca por nome ----------

export type Candidatos =
  | { tipo: "nenhum" }
  | { tipo: "um"; item: ResultadoBusca }
  | { tipo: "varios"; itens: ResultadoBusca[]; total: number };

const MAX_BOTOES_PESSOA = 5;

/**
 * Entre quem está no cargo hoje, eleitos sem posse e eleições passadas, vale a primeira lista que
 * tiver alguém: quem está no cargo vem antes.
 */
export function escolherCandidatos(b: RespostaBusca, digitado?: string): Candidatos {
  const lista = [b.itens, b.eleitos_2026, b.pessoas].find((l) => l.length > 0) ?? [];
  if (lista.length === 0) return { tipo: "nenhum" };
  if (lista.length === 1) return { tipo: "um", item: lista[0] };
  // Se só um tem exatamente o nome digitado, é essa pessoa (sem acento nem caixa).
  const alvo = digitado ? normalizar(digitado) : "";
  if (alvo) {
    const iguais = lista.filter((i) => normalizar(i.nome) === alvo || (i.nome_completo && normalizar(i.nome_completo) === alvo));
    if (iguais.length === 1) return { tipo: "um", item: iguais[0] };
  }
  return { tipo: "varios", itens: lista.slice(0, MAX_BOTOES_PESSOA), total: lista.length };
}

/** `/parlamentar/123` -> "123"; qualquer outro perfil (vereador, estadual, eleito) -> null. */
export function idFederal(caminho: string): string | null {
  const m = /^\/parlamentar\/(\d+)\/?$/.exec(caminho);
  return m ? m[1] : null;
}

export function pessoaDe(item: ResultadoBusca): PessoaLembrada {
  return { nome: item.nome, caminho: item.caminho };
}

function descricao(item: ResultadoBusca): string {
  return [item.cargo, item.partido, item.lugar].filter(Boolean).join(", ");
}

export function mensagemSemNome(partidos: RespostaBusca["partidos"]): Mensagem {
  if (partidos.length > 0) {
    return {
      texto: "Não achei ninguém com esse nome, mas achei um partido:",
      links: partidos.slice(0, 3).map((p) => ({ rotulo: `${p.sigla}, ${p.nome}`, href: p.caminho })),
      botoes: SEM_BOTOES,
    };
  }
  return {
    texto: TEXTOS.semNome,
    detalhes: ["Escreva o nome como aparece no site, com pelo menos 3 letras. Ou tente assim:"],
    links: [],
    botoes: botoesExemplo(),
  };
}

/** Vários com o mesmo nome: um botão por pessoa, que leva ao assunto pedido. */
export function mensagemEscolha(itens: ResultadoBusca[], total: number, assunto: AssuntoPessoa): Mensagem {
  const fraseDe = (i: ResultadoBusca) => `${i.nome} (${descricao(i)})`;
  return {
    texto:
      total > itens.length
        ? `Achei ${total} pessoas com esse nome. Mostro ${itens.length}; escreva o nome completo para filtrar. Qual delas?`
        : `Achei ${total} pessoas com esse nome. Qual delas?`,
    links: [],
    botoes: itens.map((i) => ({
      rotulo: fraseDe(i),
      frase: fraseDe(i),
      acao: { assunto, pessoa: pessoaDe(i) },
    })),
  };
}

/** Perfil que não é de deputado federal nem de senador: só o link. */
export function mensagemSoPerfil(pessoa: PessoaLembrada, cargo?: string): Mensagem {
  return {
    texto: `${pessoa.nome}${cargo ? ` (${cargo})` : ""}. ${TEXTOS.semResumo}`,
    links: [{ rotulo: `Perfil de ${pessoa.nome}`, href: pessoa.caminho }],
    botoes: SEM_BOTOES,
  };
}

/** Pessoa sem assunto: botões com o que dá para perguntar. */
export function mensagemAssuntos(pessoa: PessoaLembrada): Mensagem {
  const b = (rotulo: string, assunto: AssuntoPessoa): Botao => ({
    rotulo,
    frase: `${rotulo} de ${pessoa.nome}`,
    acao: { assunto, pessoa },
  });
  return {
    texto: `O que você quer saber sobre ${pessoa.nome}?`,
    links: [{ rotulo: `Perfil de ${pessoa.nome}`, href: pessoa.caminho }],
    botoes: [b("Gastos", "gastos"), b("Presença nas votações", "presenca"), b("Projetos de lei", "projetos"), b("Emendas", "emendas")],
  };
}

// ---------- Dados de deputados federais e senadores ----------

export function respostaGastos(pessoa: PessoaLembrada, casa: Casa | null, g: Gastos): Mensagem {
  const periodo = g.ultimo_mes && g.ultimo_mes < 12 ? `, de janeiro a ${MESES[g.ultimo_mes - 1]}` : "";
  const media = casa ? `Média ${CASA_DA[casa]}` : "Média da Casa";
  const texto =
    g.total === 0
      ? `${pessoa.nome} não tem reembolso da cota do gabinete registrado na fonte em ${g.ano}${periodo}.`
      : `${pessoa.nome} usou ${formatarReais(g.total)} da cota do gabinete em ${g.ano}${periodo}.`;
  return {
    texto,
    detalhes: [`${media}: ${formatarReais(g.media_casa)}.`, "Cota para o Exercício da Atividade Parlamentar (CEAP)."],
    links: [{ rotulo: "Ver gastos no perfil", href: `${pessoa.caminho}#gastos` }],
    botoes: SEM_BOTOES,
    fonte: { nome: g.fonte_nome, url: g.fonte_url, atualizadoEm: g.atualizado_em },
  };
}

export function respostaPresenca(pessoa: PessoaLembrada, casa: Casa | null, p: Presenca): Mensagem {
  const fonte = { nome: p.fonte_nome, url: p.fonte_url, atualizadoEm: p.atualizado_em };
  const links = [{ rotulo: "Ver presença no perfil", href: `${pessoa.caminho}#presenca` }];
  if (p.total_votacoes === 0) {
    return {
      texto: `Não há votação nominal no Plenário registrada para ${pessoa.nome} em ${p.ano}.`,
      links,
      botoes: SEM_BOTOES,
      fonte,
    };
  }
  const media = casa ? `Média por parlamentar ${CASA_DA[casa]}` : "Média da Casa";
  const detalhes = [
    p.media_casa_percentual === null ? `${media}: sem dado.` : `${media}: ${PCT.format(p.media_casa_percentual)}%.`,
  ];
  if (p.presente_sem_voto > 0) detalhes.push(`Presente, sem registrar voto: ${p.presente_sem_voto}.`);
  if (p.ausencia_detalhada && p.justificada > 0) {
    detalhes.push(`Ausências justificadas: ${p.justificada}.`);
  }
  return {
    texto: `${pessoa.nome} votou em ${p.votou} de ${p.total_votacoes} votações nominais em ${p.ano} (${PCT.format(p.percentual ?? 0)}%).`,
    detalhes,
    links,
    botoes: SEM_BOTOES,
    fonte,
  };
}

export function respostaProjetos(pessoa: PessoaLembrada, casa: Casa | null, pj: Projetos): Mensagem {
  const desde = new Date(pj.desde).getUTCFullYear();
  const media = casa ? `Média por parlamentar ${CASA_DA[casa]}` : "Média da Casa";
  const projetos = (n: number) => (n === 1 ? "1 projeto" : `${n} projetos`);
  return {
    texto: `${pessoa.nome} apresentou ${projetos(pj.primeiro_autor)} como autor principal desde fevereiro de ${desde} e assinou ${projetos(pj.coautor)} como coautor.`,
    detalhes: [
      `${media} (autor principal): ${NUM.format(pj.media_casa_primeiro_autor)}.`,
      `Viraram lei ou norma: ${pj.viraram_norma}.`,
    ],
    links: [{ rotulo: "Ver projetos no perfil", href: `${pessoa.caminho}#projetos` }],
    botoes: SEM_BOTOES,
    fonte: { nome: pj.fonte_nome, url: pj.fonte_url, atualizadoEm: pj.atualizado_em },
  };
}

export function respostaEmendas(pessoa: PessoaLembrada): Mensagem {
  return {
    texto: `As emendas de ${pessoa.nome}, o dinheiro do orçamento que a pessoa indicou para cidades e entidades, estão no perfil, com valor, destino, situação e fonte.`,
    detalhes: ["Ainda não tenho um resumo com média da Casa para as emendas."],
    links: [{ rotulo: "Ver emendas no perfil", href: `${pessoa.caminho}#destino-emendas` }],
    botoes: SEM_BOTOES,
  };
}

// ---------- Representantes por CEP ----------

const LIMITE_DEPUTADOS = 8;

export function respostaRepresentantes(cep: string, r: Representantes): Mensagem {
  const { localizacao: l, deputados, senadores } = r;
  const lugar = l.municipio ? `${l.municipio}-${l.uf}` : (l.estado ?? l.uf);
  const links = [
    ...senadores.map((s) => ({ rotulo: `${s.nome_parlamentar} (${s.partido ?? "sem partido"}), senador(a)`, href: `/parlamentar/${s.id}` })),
    ...deputados
      .slice(0, LIMITE_DEPUTADOS)
      .map((d) => ({ rotulo: `${d.nome_parlamentar} (${d.partido ?? "sem partido"}), deputado(a) federal`, href: `/parlamentar/${d.id}` })),
    { rotulo: "Ver todos, com prefeito, vereadores e governador", href: `/representantes?cep=${encodeURIComponent(cep)}` },
  ];
  if (l.codigo_ibge) links.push({ rotulo: `Dinheiro e contas de ${l.municipio ?? "sua cidade"}`, href: `/cidade/${l.codigo_ibge}` });
  const detalhes = [
    deputados.length > LIMITE_DEPUTADOS
      ? `${l.estado} tem ${deputados.length} deputados federais; mostro ${LIMITE_DEPUTADOS} aqui. A lista completa está em "Ver todos".`
      : `${l.estado} tem ${deputados.length} deputados federais.`,
  ];
  return {
    texto: `O CEP ${cep} é de ${lugar}. No Congresso, ${l.estado} é representado por ${senadores.length} senadores e ${deputados.length} deputados federais.`,
    detalhes,
    links,
    botoes: SEM_BOTOES,
    fonte: { nome: `${FONTE_CASA.camara} e ${FONTE_CASA.senado}`, atualizadoEm: r.atualizado_em },
  };
}
