/**
 * Transforma os dados da API em mensagens do Argos. Funções puras (testadas no Vitest): não
 * chamam a rede nem sabem de tela. Toda resposta com número leva fonte e data; a média da Casa
 * vem ao lado do número. Linguagem factual: sem adjetivo, sem juízo.
 */
import type { Casa, Gastos, Municipio, ParlamentarDetalhe, Presenca, Projetos, Representantes, RespostaBusca, ResultadoBusca } from "@/lib/api";
import { CASA_DA, FONTE_CASA, MESES, formatarData, formatarReais } from "@/lib/formato";
import { PERGUNTAS_FREQUENTES } from "@/lib/perguntas";

import { nomeDaUf } from "./entidades";
import { normalizar } from "./texto";
import type { AssuntoPessoa, Botao, CriterioLista, Interpretacao, Mensagem, PessoaLembrada } from "./tipos";
import { EXEMPLOS, PAGINAS, PALAVRAS_GENERICAS, SECOES, TEXTOS } from "./vocabulario";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const NUM = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

const SEM_BOTOES: Botao[] = [];

const MESES_EXTENSO = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
  "novembro", "dezembro",
];
export const nomeDoMes = (m: number) => MESES_EXTENSO[m - 1] ?? String(m);

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

export function sobreArgos(): Mensagem {
  return {
    texto: TEXTOS.sobreArgos,
    detalhes: [
      "Os dados vêm de fontes oficiais (Câmara, Senado, TSE, IBGE, Portal da Transparência e outras), listadas em Sobre as fontes. As frases que não entendo ficam guardadas, sem identificar você, para eu aprender.",
    ],
    links: [
      { rotulo: "Sobre as fontes", href: "/sobre-as-fontes" },
      { rotulo: "O que é guardado (privacidade)", href: "/privacidade#argos" },
      { rotulo: "O que é o Panóptico", href: "/o-panoptico" },
    ],
    botoes: SEM_BOTOES,
  };
}

export function opiniao(): Mensagem {
  return { texto: TEXTOS.opiniao, links: [], botoes: botoesExemplo() };
}

export function naoEntendi(sugestoes?: Botao[]): Mensagem {
  return {
    texto: TEXTOS.naoEntendi,
    links: [{ rotulo: "Busca por nome no site", href: "/parlamentares" }],
    botoes: sugestoes && sugestoes.length > 0 ? sugestoes : botoesExemplo().slice(0, 3),
  };
}

export function pedirCep(): Mensagem {
  return { texto: TEXTOS.pedirCep, links: [], botoes: SEM_BOTOES };
}

const NOME_CRITERIO: Record<CriterioLista, string> = {
  gastos: "gastos do gabinete",
  presenca: "presença em votações",
  projetos: "projetos como autor principal",
  emendas: "emendas pagas",
};

export function semRanking(ordem?: { criterio: CriterioLista; desc: boolean }, filtros: { uf?: string; casa?: Casa } = {}): Mensagem {
  const params = new URLSearchParams();
  if (filtros.casa) params.set("casa", filtros.casa);
  if (filtros.uf) params.set("uf", filtros.uf);
  if (ordem) {
    params.set("ordenar", ordem.criterio);
    params.set("ordem", ordem.desc ? "desc" : "asc");
  }
  const href = params.size ? `/parlamentares?${params}` : "/parlamentares";
  return {
    texto:
      "O site não faz ranking nem aponta quem é melhor ou pior. Na lista de parlamentares dá para ordenar por gastos, presença, projetos e emendas; cada número vem de fonte oficial, com a média da Casa ao lado, e não é nota.",
    links: [
      {
        rotulo: ordem
          ? `Lista de parlamentares ordenada por ${NOME_CRITERIO[ordem.criterio]} (${ordem.desc ? "do maior para o menor" : "do menor para o maior"})`
          : "Lista de parlamentares, com ordenação",
        href,
      },
    ],
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
    botoes: [b("Gastos", "gastos"), b("Presença nas votações", "presenca"), b("Projetos de lei", "projetos"), b("Emendas", "emendas"), b("Salário", "salario")],
  };
}

// ---------- Dados de deputados federais e senadores ----------

export function respostaGastos(pessoa: PessoaLembrada, casa: Casa | null, g: Gastos, mes?: number): Mensagem {
  const periodo = g.ultimo_mes && g.ultimo_mes < 12 ? `, de janeiro a ${MESES[g.ultimo_mes - 1]}` : "";
  const media = casa ? `Média ${CASA_DA[casa]}` : "Média da Casa";
  const texto =
    g.total === 0
      ? `${pessoa.nome} não tem reembolso da cota do gabinete registrado na fonte em ${g.ano}${periodo}.`
      : `${pessoa.nome} usou ${formatarReais(g.total)} da cota do gabinete em ${g.ano}${periodo}.`;
  const detalhes = [`${media}: ${formatarReais(g.media_casa)}.`];
  if (mes) {
    const doMes = g.por_mes.find((m) => m.mes === mes);
    detalhes.unshift(
      doMes
        ? `Em ${nomeDoMes(mes)} de ${g.ano}: ${formatarReais(doMes.total)}. A média da Casa abaixo é do ano todo; o detalhe por mês está no perfil.`
        : `Não há lançamento em ${nomeDoMes(mes)} de ${g.ano} na fonte (o último mês com dados é ${g.ultimo_mes ? nomeDoMes(g.ultimo_mes) : "desconhecido"}).`,
    );
  }
  detalhes.push("Cota para o Exercício da Atividade Parlamentar (CEAP).");
  return {
    texto,
    detalhes,
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

// ---------- Representantes por CEP, estado ou cidade ----------

const LIMITE_DEPUTADOS = 8;

/** Quem consultou: CEP, estado ou cidade (código do IBGE). */
export type Consulta = { uf?: string; municipio?: string };

export function respostaRepresentantes(cep: string | null, r: Representantes, casa?: Casa, consulta?: Consulta): Mensagem {
  const { localizacao: l, deputados, senadores } = r;
  const lugar = l.municipio ? `${l.municipio}-${l.uf}` : (l.estado ?? l.uf);
  const href = cep
    ? `/representantes?cep=${encodeURIComponent(cep)}`
    : consulta?.municipio
      ? `/representantes?municipio=${encodeURIComponent(consulta.municipio)}`
      : `/representantes?uf=${encodeURIComponent(l.uf)}`;
  const mostraSenadores = casa !== "camara";
  const mostraDeputados = casa !== "senado";
  const links = [
    ...(mostraSenadores
      ? senadores.map((s) => ({ rotulo: `${s.nome_parlamentar} (${s.partido ?? "sem partido"}), senador(a)`, href: `/parlamentar/${s.id}` }))
      : []),
    ...(mostraDeputados
      ? deputados
          .slice(0, LIMITE_DEPUTADOS)
          .map((d) => ({ rotulo: `${d.nome_parlamentar} (${d.partido ?? "sem partido"}), deputado(a) federal`, href: `/parlamentar/${d.id}` }))
      : []),
    { rotulo: "Ver todos, com prefeito, vereadores e governador", href },
  ];
  if (l.codigo_ibge) links.push({ rotulo: `Dinheiro e contas de ${l.municipio ?? "sua cidade"}`, href: `/cidade/${l.codigo_ibge}` });
  const detalhes =
    mostraDeputados
      ? [
          deputados.length > LIMITE_DEPUTADOS
            ? `${l.estado} tem ${deputados.length} deputados federais; mostro ${LIMITE_DEPUTADOS} aqui. A lista completa está em "Ver todos".`
            : `${l.estado} tem ${deputados.length} deputados federais.`,
        ]
      : undefined;
  const quem = cep ? `O CEP ${cep} é de ${lugar}. ` : l.municipio ? `${lugar}. ` : "";
  const resumo =
    casa === "camara"
      ? `${l.estado} tem ${deputados.length} deputados federais.`
      : casa === "senado"
        ? `${l.estado} tem ${senadores.length} senadores.`
        : `No Congresso, ${l.estado} é representado por ${senadores.length} senadores e ${deputados.length} deputados federais.`;
  return {
    texto: `${quem}${resumo}`,
    detalhes,
    links,
    botoes: SEM_BOTOES,
    fonte: { nome: `${FONTE_CASA.camara} e ${FONTE_CASA.senado}`, atualizadoEm: r.atualizado_em },
  };
}

// ---------- Salário ----------

export function respostaSalario(pessoa: PessoaLembrada, p: ParlamentarDetalhe): Mensagem {
  const r = p.remuneracao;
  return {
    texto: `O subsídio mensal de ${pessoa.nome} é de ${formatarReais(r.subsidio_mensal)}, em vigor desde ${formatarData(r.vigente_desde)}.`,
    detalhes: ["Subsídio é o salário fixado em lei; não inclui a cota para o gabinete nem outros benefícios."],
    links: [{ rotulo: "Ver salário no perfil", href: `${pessoa.caminho}#remuneracao` }],
    botoes: SEM_BOTOES,
    fonte: { nome: r.fonte_nome, url: r.fonte_url, atualizadoEm: p.atualizado_em },
  };
}

// ---------- Seções do perfil e páginas do site ----------

export function respostaSecao(pessoa: PessoaLembrada, secao: string): Mensagem {
  const s = SECOES[secao];
  if (!s) return mensagemAssuntos(pessoa);
  return { texto: s.texto(pessoa.nome), links: [{ rotulo: s.rotulo, href: `${pessoa.caminho}#${s.ancora}` }], botoes: SEM_BOTOES };
}

export function respostaPagina(id: string): Mensagem {
  const p = PAGINAS[id];
  if (!p) return naoEntendi();
  return { texto: p.texto, links: [{ rotulo: p.rotulo, href: p.href }], botoes: SEM_BOTOES };
}

// ---------- Comparar ----------

const MAX_COMPARAR = 4;

export function linkComparar(pessoas: PessoaLembrada[], ano?: number): string {
  const ids = pessoas.map((p) => idFederal(p.caminho)).filter((x): x is string => !!x).slice(0, MAX_COMPARAR);
  return `/comparar?ids=${ids.join(",")}${ano ? `&ano=${ano}` : ""}`;
}

export function respostaComparar(pessoas: PessoaLembrada[], ano?: number): Mensagem {
  const nomes = pessoas.map((p) => p.nome);
  const lista = nomes.length > 2 ? `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}` : nomes.join(" e ");
  return {
    texto: `Comparação de ${lista}: gastos, presença, projetos e votos lado a lado, cada número com a média da Casa, a fonte e a data.`,
    links: [{ rotulo: `Abrir a comparação de ${lista}`, href: linkComparar(pessoas, ano) }],
    botoes: SEM_BOTOES,
  };
}

export function compararSemNomes(unica?: PessoaLembrada): Mensagem {
  if (unica && idFederal(unica.caminho)) {
    return {
      texto: `Para comparar ${unica.nome} com outra pessoa, diga o nome dela: "compare ${unica.nome} e Fulano". Dá para comparar de 2 a 4 deputados federais ou senadores.`,
      links: [{ rotulo: `Escolher com quem comparar ${unica.nome}`, href: `/comparar?ids=${idFederal(unica.caminho)}&adicionar=1` }],
      botoes: SEM_BOTOES,
    };
  }
  return {
    texto:
      "Dá para comparar de 2 a 4 deputados federais ou senadores, lado a lado. Escreva os nomes, por exemplo: compare Fulano e Beltrano. Ou escolha na página de comparação.",
    links: [{ rotulo: "Comparar parlamentares", href: "/comparar" }],
    botoes: SEM_BOTOES,
  };
}

export function compararNaoAchou(faltou: string[], achados: PessoaLembrada[]): Mensagem {
  const quem = faltou.map((n) => `"${n}"`).join(" e ");
  return {
    texto: `Não achei ${quem} entre os deputados federais e senadores em exercício. Escreva o nome como aparece no site (pelo menos 3 letras); só dá para comparar parlamentares do Congresso.`,
    links:
      achados.length === 1
        ? [{ rotulo: `Escolher com quem comparar ${achados[0].nome}`, href: `/comparar?ids=${idFederal(achados[0].caminho)}&adicionar=1` }]
        : [{ rotulo: "Comparar parlamentares", href: "/comparar" }],
    botoes: SEM_BOTOES,
  };
}

// ---------- Dinheiro federal, governo, partidos, listas, cidades, eleições ----------

export type Lugar = { uf?: string; municipio?: Municipio };

export function linkDinheiro(lugar: Lugar, ano?: number): string {
  const base = lugar.municipio
    ? `/impostos-e-repasses/${lugar.municipio.uf}/${lugar.municipio.ibge}`
    : lugar.uf
      ? `/impostos-e-repasses/${lugar.uf}`
      : "/impostos-e-repasses";
  return ano ? `${base}?ano=${ano}` : base;
}

const nomeLugar = (l: Lugar) => (l.municipio ? `${l.municipio.nome}-${l.municipio.uf}` : l.uf ? nomeDaUf(l.uf) : "o Brasil");

export function respostaDinheiroFederal(lugar: Lugar, ano?: number): Mensagem {
  return {
    texto: `Impostos e repasses: quanto a União arrecada e quanto repassa, ${lugar.municipio ? "para a cidade e o peso dos repasses na receita da prefeitura" : "por estado e por cidade"}. Abra o painel de ${nomeLugar(lugar)}${ano ? ` em ${ano}` : ""}.`,
    detalhes: ["Os números são anuais, com a fonte e a data de atualização no próprio painel."],
    links: [{ rotulo: `Impostos e repasses: ${nomeLugar(lugar)}`, href: linkDinheiro(lugar, ano) }],
    botoes: SEM_BOTOES,
  };
}

const PORTAL = "https://portaldatransparencia.gov.br";

export function respostaGovernoGasto(i: Pick<Interpretacao, "instituicao" | "mes" | "ano" | "relativo">, lugar: Lugar): Mensagem {
  const periodo = i.mes ? `${nomeDoMes(i.mes)}${i.ano ? ` de ${i.ano}` : ""}` : i.ano ? String(i.ano) : null;
  const detalhes: string[] = [];
  if (periodo) detalhes.push(`Período pedido: ${periodo}. Os painéis do Panóptico sobre esse assunto são anuais, não mensais.`);
  if (i.instituicao === "municipal") {
    if (lugar.municipio) {
      return {
        texto: `O Panóptico não mostra o gasto da prefeitura mês a mês. O que tem de ${lugar.municipio.nome}-${lugar.municipio.uf} são as contas anuais da prefeitura (receita e despesa por área, enviadas ao Tesouro), o dinheiro federal repassado e as emendas recebidas.`,
        detalhes,
        links: [
          { rotulo: `Contas e dinheiro de ${lugar.municipio.nome}`, href: `/cidade/${lugar.municipio.ibge}` },
          { rotulo: "Impostos e repasses da cidade", href: linkDinheiro(lugar) },
        ],
        botoes: SEM_BOTOES,
      };
    }
    return {
      texto:
        "O Panóptico mostra as contas anuais de cada prefeitura (receita e despesa por área), não o gasto mês a mês. Diga a cidade e o estado (por exemplo: contas da prefeitura de Gaspar SC) ou digite o CEP.",
      detalhes,
      links: [{ rotulo: "Escolher pelo CEP", href: "/#cep" }],
      botoes: SEM_BOTOES,
    };
  }
  if (i.instituicao === "estadual" && lugar.uf) {
    return {
      texto: `O gasto total do governo de ${nomeDaUf(lugar.uf)} não está no Panóptico. O que tem é o dinheiro que a União arrecada e repassa a ${nomeDaUf(lugar.uf)} e às cidades do estado, por ano.`,
      detalhes,
      links: [
        { rotulo: `Impostos e repasses: ${nomeDaUf(lugar.uf)}`, href: linkDinheiro(lugar, i.relativo ? undefined : i.ano) },
        { rotulo: `Quem representa ${nomeDaUf(lugar.uf)}`, href: `/representantes?uf=${lugar.uf}` },
      ],
      botoes: SEM_BOTOES,
    };
  }
  return {
    texto:
      "O gasto total do governo federal, mês a mês, não está no Panóptico. O que temos é quanto a União arrecada e repassa a cada estado e cidade, por ano, e os gastos do gabinete de cada deputado e senador. O gasto geral do governo está no Portal da Transparência, na fonte oficial.",
    detalhes,
    links: [
      { rotulo: "Impostos e repasses, por estado e cidade", href: linkDinheiro({}, i.relativo ? undefined : i.ano) },
      { rotulo: "Gastos do governo federal no Portal da Transparência", href: PORTAL },
    ],
    botoes: SEM_BOTOES,
  };
}

export function respostaExecutivo(cargo: Interpretacao["cargo"], lugar: Lugar): Mensagem {
  const quem =
    cargo === "presidente" ? "o presidente" : cargo === "governador" ? "o governador" : cargo === "prefeito" ? "o prefeito" : "o presidente, o governador e o prefeito";
  const inicio = `${quem[0].toUpperCase()}${quem.slice(1)}`;
  const href = lugar.municipio ? `/representantes?municipio=${lugar.municipio.ibge}` : lugar.uf ? `/representantes?uf=${lugar.uf}` : null;
  if (!href) {
    return {
      texto: `${inicio} aparece na página Seus representantes, com o que faz, gasta e recebe. Digite o seu CEP ou diga o estado ou a cidade.`,
      links: [{ rotulo: "Digitar o CEP", href: "/#cep" }],
      botoes: SEM_BOTOES,
    };
  }
  return {
    texto: `${inicio} de ${nomeLugar(lugar)} aparece em Seus representantes, com o que faz, gasta e recebe e a fonte de cada dado.`,
    links: [{ rotulo: `Quem representa ${nomeLugar(lugar)}`, href }],
    botoes: SEM_BOTOES,
  };
}

export function respostaPartidos(sigla?: string, ano?: number): Mensagem {
  const q = ano ? `?ano=${ano}` : "";
  if (sigla) {
    return {
      texto: `As contas do ${sigla}: de onde veio o dinheiro, em que gastou e quanto repassou, em cada prestação de contas anual.`,
      links: [
        { rotulo: `Contas do ${sigla}`, href: `/partidos/${encodeURIComponent(sigla)}${q}` },
        { rotulo: `Deputados e senadores do ${sigla}`, href: `/parlamentares?partido=${encodeURIComponent(sigla)}` },
      ],
      botoes: SEM_BOTOES,
    };
  }
  return {
    texto: "A página de partidos mostra, por ano, cotas, receita, gastos e repasses de cada partido, com a fonte.",
    links: [{ rotulo: "Dinheiro dos partidos", href: `/partidos${q}` }],
    botoes: SEM_BOTOES,
  };
}

export function respostaLista(f: { casa?: Casa; uf?: string; partido?: string }): Mensagem {
  const params = new URLSearchParams();
  if (f.casa) params.set("casa", f.casa);
  if (f.uf) params.set("uf", f.uf);
  if (f.partido) params.set("partido", f.partido);
  const q = params.toString();
  return {
    texto:
      "A lista tem os deputados federais e senadores em exercício. Dá para filtrar por estado, Casa e partido e ordenar por gastos, presença e projetos; cada número vem de fonte oficial e não é nota.",
    links: [{ rotulo: "Lista de parlamentares", href: `/parlamentares${q ? `?${q}` : ""}` }],
    botoes: SEM_BOTOES,
  };
}

export function respostaCidade(m: Municipio): Mensagem {
  return {
    texto: `${m.nome}-${m.uf}: vereadores e câmara, contas da prefeitura, dinheiro federal recebido, emendas e fornecedores, o que houver de dado oficial.`,
    links: [
      { rotulo: `Página de ${m.nome}`, href: `/cidade/${m.ibge}` },
      { rotulo: `Quem representa ${m.nome}`, href: `/representantes?municipio=${m.ibge}` },
      { rotulo: "Impostos e repasses da cidade", href: `/impostos-e-repasses/${m.uf}/${m.ibge}` },
    ],
    botoes: SEM_BOTOES,
  };
}

export function pedirCidade(): Mensagem {
  return {
    texto: "De qual cidade? Escreva o nome e o estado (por exemplo: Gaspar SC) ou digite o CEP.",
    links: [{ rotulo: "Digitar o CEP", href: "/#cep" }],
    botoes: SEM_BOTOES,
  };
}

export function escolherCidade(itens: Municipio[], fraseOriginal: string): Mensagem {
  return {
    texto: `Achei ${itens.length} cidades com esse nome. Qual delas?`,
    links: [],
    botoes: itens.slice(0, 6).map((m) => ({ rotulo: `${m.nome}-${m.uf}`, frase: `${fraseOriginal} ${m.uf}` })),
  };
}

export function respostaEleicao(uf?: string): Mensagem {
  return {
    texto:
      "O segundo turno de 2026 tem página própria, com os candidatos de cada disputa, a agenda e a fonte (TSE). Os eleitos de 2026 por estado aparecem em Seus representantes.",
    links: [
      { rotulo: "Segundo turno", href: uf ? `/segundo-turno?uf=${uf}` : "/segundo-turno" },
      ...(uf ? [{ rotulo: `Quem representa ${nomeDaUf(uf)}`, href: `/representantes?uf=${uf}` }] : []),
    ],
    botoes: SEM_BOTOES,
  };
}

export function respostaProjetosBusca(tema: string, uf?: string, ano?: number): Mensagem {
  const params = new URLSearchParams({ q: tema });
  if (uf) params.set("uf", uf);
  if (ano) params.set("ano", String(ano));
  return {
    texto: `Busca de projetos de lei sobre "${tema}" no Congresso, nas assembleias e nas câmaras, com situação, autor e fonte.`,
    links: [{ rotulo: `Projetos sobre ${tema}`, href: `/projetos?${params}` }],
    botoes: SEM_BOTOES,
  };
}

/** Resultado da busca de pessoas que só casa com uma palavra genérica ("Governo", "Câmara") não conta. */
export function semGenericos(b: RespostaBusca, digitado: string): RespostaBusca {
  const alvo = new Set(normalizar(digitado).split(" "));
  const bom = (i: ResultadoBusca) => {
    const comuns = normalizar(`${i.nome} ${i.nome_completo ?? ""}`).split(" ").filter((p) => alvo.has(p));
    return comuns.some((p) => !PALAVRAS_GENERICAS.has(p));
  };
  return { ...b, itens: b.itens.filter(bom), eleitos_2026: b.eleitos_2026.filter(bom), pessoas: b.pessoas.filter(bom) };
}
