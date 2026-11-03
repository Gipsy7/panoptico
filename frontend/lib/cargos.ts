/**
 * Cargos eleitos: o que cada um faz, o que pode, o que não pode e quanto ganha.
 *
 * Fonte única dos textos (a página /representantes, o "Sobre o cargo" do perfil, a gaveta dos
 * prédios e o Argos leem daqui). Cada frase de "pode" e "não pode" traz o artigo da Constituição
 * Federal conferido no texto oficial consolidado (planalto.gov.br, conferido em CF_CONFERIDA_EM).
 * Onde a Constituição manda a Constituição do estado ou a lei orgânica da cidade detalhar, o
 * artigo da CF citado é o que dá essa remissão e o texto diz isso.
 *
 * Linguagem factual: descreve a regra, sem avaliar quem ocupa o cargo. Salário só onde há fonte;
 * onde a regra só diz quem fixa o valor (presidente, governador, prefeito), o texto diz isso e
 * não inventa número.
 */

import { formatarReais } from "@/lib/formato";

export type CargoId =
  | "presidente"
  | "vice-presidente"
  | "senador"
  | "deputado-federal"
  | "governador"
  | "vice-governador"
  | "deputado-estadual"
  | "prefeito"
  | "vice-prefeito"
  | "vereador";

/** Uma frase do dia a dia com o artigo que a sustenta, em letra menor na tela. */
export type ItemComArtigo = { texto: string; artigo: string };

export type FonteCargo = { nome: string; url: string };

export type GanhaCargo = {
  /** Frase do dia a dia, já com o número quando há fonte para ele. */
  texto: string;
  /** Valor mensal bruto em reais, só quando a fonte dá um número fixo para o país. */
  valor?: number;
  /** Artigo da Constituição que define quem fixa o valor. */
  artigo: string;
  fonte: FonteCargo;
};

export type Cargo = {
  id: CargoId;
  /** "Vereador". */
  nome: string;
  /** "um vereador", para frases ("o que faz um vereador?"). */
  um: string;
  /** Poder e esfera, em letra menor ("Poder Legislativo municipal"). */
  oficial: string;
  /** O que faz, no dia a dia (texto da página /representantes). */
  faz: string;
  /** O termo oficial do cargo (letra menor). */
  fazOficial: string;
  /** Variante do Distrito Federal, quando o texto muda. */
  df?: { nome: string; faz: string; fazOficial: string };
  pode: ItemComArtigo[];
  naoPode: ItemComArtigo[];
  ganha: GanhaCargo;
};

/** Texto consolidado da Constituição, de onde os artigos foram conferidos. */
export const CF_URL = "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm";
export const CF_NOME = "Constituição Federal de 1988 (texto consolidado)";
/** Data em que os artigos foram conferidos no texto do Planalto. */
export const CF_CONFERIDA_EM = "2026-11-03";

/**
 * Subsídio mensal bruto de deputado federal e de senador (igual para os dois, CF art. 49, VII).
 * Mesmo valor de `SUBSIDIOS` em `backend/app/services/remuneracao.py` (o teste confere).
 */
export const SUBSIDIO_FEDERAL = 46366.19;
export const SUBSIDIO_FEDERAL_DESDE = "02/2025";
export const FONTE_SUBSIDIO_FEDERAL: FonteCargo = {
  nome: "Decreto Legislativo nº 172, de 21 de dezembro de 2022",
  url: "https://www2.camara.leg.br/legin/fed/decleg/2022/decretolegislativo-172-21-dezembro-2022-793529-publicacaooriginal-166604-pl.html",
};

/** Teto do deputado estadual: 75% do deputado federal (CF art. 27, § 2º), em centavos exatos. */
export const TETO_DEPUTADO_ESTADUAL = Math.round(SUBSIDIO_FEDERAL * 0.75 * 100) / 100;

const FONTE_CF: FonteCargo = { nome: CF_NOME, url: CF_URL };

/** Faixas do teto do vereador (CF art. 29, VI): até este número de habitantes, este percentual. */
export const FAIXAS_VEREADOR: { ate: number; percentual: number; rotulo: string }[] = [
  { ate: 10_000, percentual: 20, rotulo: "até 10 mil habitantes" },
  { ate: 50_000, percentual: 30, rotulo: "de 10.001 a 50 mil habitantes" },
  { ate: 100_000, percentual: 40, rotulo: "de 50.001 a 100 mil habitantes" },
  { ate: 300_000, percentual: 50, rotulo: "de 100.001 a 300 mil habitantes" },
  { ate: 500_000, percentual: 60, rotulo: "de 300.001 a 500 mil habitantes" },
  { ate: Infinity, percentual: 75, rotulo: "mais de 500 mil habitantes" },
];

/** Percentual máximo do subsídio de deputado estadual que o vereador pode receber, pela população. */
export function tetoVereadorPercentual(habitantes: number): number {
  const faixa = FAIXAS_VEREADOR.find((f) => habitantes <= f.ate);
  return faixa ? faixa.percentual : 75;
}

const CF = (art: string) => `CF art. ${art}`;

const PRESIDENTE: Cargo = {
  id: "presidente",
  nome: "Presidente",
  um: "o presidente da República",
  oficial: "Poder Executivo federal",
  faz: "O presidente comanda o governo do país: dirige os ministérios e cuida do dinheiro e dos serviços nacionais, como o INSS.",
  fazOficial: "Chefia do Poder Executivo da União",
  pode: [
    { texto: "Sancionar ou vetar as leis que o Congresso aprova", artigo: CF("66 e 84, IV e V") },
    { texto: "Nomear e demitir os ministros e dirigir a administração do governo federal", artigo: CF("84, I e II") },
    { texto: "Propor leis e mudanças na Constituição ao Congresso", artigo: CF("60, II e 61") },
    { texto: "Editar medidas provisórias, que valem como lei enquanto o Congresso as analisa", artigo: CF("62") },
    { texto: "Comandar as Forças Armadas e manter relações com outros países", artigo: CF("84, VII e XIII") },
  ],
  naoPode: [
    { texto: "Aprovar leis sozinho: quem as vota é o Congresso, e o presidente sanciona ou veta", artigo: CF("48 e 66") },
    { texto: "Declarar guerra sem o Congresso: ele autoriza ou confirma depois", artigo: CF("49, II e 84, XIX") },
    { texto: "Ficar mais de 15 dias fora do país sem autorização do Congresso", artigo: CF("49, III") },
    { texto: "Disputar um terceiro mandato seguido: a reeleição vale para um único período", artigo: CF("14, § 5º") },
  ],
  ganha: {
    texto:
      "O Congresso Nacional fixa o valor por decreto. A Constituição diz quem define e que o valor não passa do teto do serviço público; o Panóptico não traz o número porque ele não vem de fonte carregada.",
    artigo: CF("49, VIII e 37, XI"),
    fonte: FONTE_CF,
  },
};

const VICE_PRESIDENTE: Cargo = {
  id: "vice-presidente",
  nome: "Vice-presidente",
  um: "o vice-presidente da República",
  oficial: "Poder Executivo federal",
  faz: "O vice-presidente substitui o presidente quando ele está impedido e assume se o cargo ficar vago. Também ajuda o presidente em missões especiais.",
  fazOficial: "Substituição e sucessão do Presidente da República",
  pode: [
    { texto: "Substituir o presidente quando ele está impedido e assumir se o cargo ficar vago", artigo: CF("79") },
    { texto: "Ajudar o presidente em missões especiais, quando ele pede", artigo: CF("79, parágrafo único") },
  ],
  naoPode: [
    { texto: "Dirigir o governo enquanto o presidente está no cargo: o Poder Executivo é exercido pelo presidente", artigo: CF("76") },
    { texto: "Ficar mais de 15 dias fora do país sem autorização do Congresso", artigo: CF("49, III") },
  ],
  ganha: {
    texto: "O Congresso Nacional fixa o valor por decreto. O Panóptico não traz o número porque ele não vem de fonte carregada.",
    artigo: CF("49, VIII"),
    fonte: FONTE_CF,
  },
};

const SENADOR: Cargo = {
  id: "senador",
  nome: "Senador",
  um: "um senador",
  oficial: "Casa legislativa da União",
  faz: "Os senadores votam as leis do país e analisam o que o governo faz. Cada estado tem 3.",
  fazOficial: "Senadores",
  pode: [
    { texto: "Votar as leis do país, junto com a Câmara dos Deputados", artigo: CF("44 e 48") },
    { texto: "Julgar o presidente e o vice-presidente nos crimes de responsabilidade", artigo: CF("52, I") },
    {
      texto: "Aprovar ou recusar certos nomes que o presidente indica, como o do Procurador-Geral da República e o do presidente do Banco Central",
      artigo: CF("52, III"),
    },
    { texto: "Fiscalizar os atos do governo federal", artigo: CF("49, X") },
    { texto: "Falar e votar sem responder na Justiça por suas opiniões, palavras e votos", artigo: CF("53") },
  ],
  naoPode: [
    { texto: "Decidir se o processo contra o presidente começa: isso cabe à Câmara dos Deputados, por dois terços", artigo: CF("51, I") },
    { texto: "Firmar contrato com órgão público nem ter cargo remunerado nele, desde a diplomação", artigo: CF("54, I") },
    { texto: "Faltar a um terço das sessões do ano sem licença ou missão autorizada, sob pena de perder o mandato", artigo: CF("55, III") },
  ],
  ganha: {
    texto: `${formatarReais(SUBSIDIO_FEDERAL)} por mês, valor bruto (subsídio), vigente desde ${SUBSIDIO_FEDERAL_DESDE}. É igual ao do deputado federal e fixado pelo Congresso.`,
    valor: SUBSIDIO_FEDERAL,
    artigo: CF("49, VII"),
    fonte: FONTE_SUBSIDIO_FEDERAL,
  },
};

const DEPUTADO_FEDERAL: Cargo = {
  id: "deputado-federal",
  nome: "Deputado federal",
  um: "um deputado federal",
  oficial: "Casa legislativa da União",
  faz: "Os deputados federais também votam as leis do país.",
  fazOficial: "Deputados federais",
  pode: [
    { texto: "Votar as leis do país, junto com o Senado", artigo: CF("44 e 48") },
    { texto: "Decidir, por dois terços, se o presidente, o vice e os ministros podem ser processados", artigo: CF("51, I") },
    { texto: "Fiscalizar os atos do governo federal e chamar ministros para dar explicações", artigo: CF("49, X e 50") },
    { texto: "Falar e votar sem responder na Justiça por suas opiniões, palavras e votos", artigo: CF("53") },
    { texto: "Representar o povo do estado: cada estado tem de 8 a 70 deputados, conforme a população", artigo: CF("45, § 1º") },
  ],
  naoPode: [
    { texto: "Julgar o presidente por crime de responsabilidade: quem julga é o Senado", artigo: CF("52, I") },
    { texto: "Firmar contrato com órgão público nem ter cargo remunerado nele, desde a diplomação", artigo: CF("54, I") },
    { texto: "Faltar a um terço das sessões do ano sem licença ou missão autorizada, sob pena de perder o mandato", artigo: CF("55, III") },
  ],
  ganha: {
    texto: `${formatarReais(SUBSIDIO_FEDERAL)} por mês, valor bruto (subsídio), vigente desde ${SUBSIDIO_FEDERAL_DESDE}. É igual ao do senador e fixado pelo Congresso.`,
    valor: SUBSIDIO_FEDERAL,
    artigo: CF("49, VII"),
    fonte: FONTE_SUBSIDIO_FEDERAL,
  },
};

const GOVERNADOR: Cargo = {
  id: "governador",
  nome: "Governador",
  um: "um governador",
  oficial: "Poder Executivo estadual",
  faz: "O governador comanda o estado: dirige a segurança, os hospitais e as escolas estaduais.",
  fazOficial: "Chefia do Poder Executivo estadual",
  df: {
    nome: "Governador do Distrito Federal",
    faz: "O governador comanda o Distrito Federal, que reúne tarefas de estado e de cidade: segurança, hospitais e escolas.",
    fazOficial: "Chefia do Poder Executivo distrital",
  },
  pode: [
    { texto: "Comandar as polícias militar e civil e os bombeiros do estado", artigo: CF("144, § 6º") },
    { texto: "Dirigir os serviços do estado, como a saúde e as escolas de ensino fundamental e médio", artigo: CF("198, I e 211, § 3º") },
    { texto: "Cuidar de tudo o que a Constituição não reserva à União nem aos municípios", artigo: CF("25, § 1º") },
  ],
  naoPode: [
    { texto: "Criar leis penais, civis, eleitorais ou trabalhistas: isso é só da União", artigo: CF("22, I") },
    { texto: "Assumir outro cargo na administração pública sem perder o mandato, salvo por concurso", artigo: CF("28, § 1º") },
    { texto: "Disputar um terceiro mandato seguido: a reeleição vale para um único período", artigo: CF("14, § 5º") },
    { texto: "Concorrer a outro cargo sem deixar o governo até seis meses antes da eleição", artigo: CF("14, § 6º") },
  ],
  ganha: {
    texto:
      "A Assembleia Legislativa do estado fixa o valor por lei. A Constituição diz quem define e que o valor não passa do teto do serviço público; o Panóptico não traz o número porque ele não vem de fonte carregada.",
    artigo: CF("28, § 2º e 37, XI"),
    fonte: FONTE_CF,
  },
};

const VICE_GOVERNADOR: Cargo = {
  id: "vice-governador",
  nome: "Vice-governador",
  um: "um vice-governador",
  oficial: "Poder Executivo estadual",
  faz: "O vice-governador substitui o governador quando ele está impedido e assume se o cargo ficar vago, como a Constituição de cada estado detalha.",
  fazOficial: "Substituição e sucessão do Governador",
  df: {
    nome: "Vice-governador do Distrito Federal",
    faz: "O vice-governador substitui o governador do Distrito Federal quando ele está impedido e assume se o cargo ficar vago, como a lei orgânica do DF detalha.",
    fazOficial: "Substituição e sucessão do Governador do Distrito Federal",
  },
  pode: [
    {
      texto: "Substituir o governador quando ele está impedido e assumir se o cargo ficar vago, como a Constituição do estado detalha",
      artigo: CF("25, caput e 28"),
    },
  ],
  naoPode: [
    { texto: "Criar leis penais, civis, eleitorais ou trabalhistas: isso é só da União", artigo: CF("22, I") },
    { texto: "Ser eleito com menos de 30 anos: é a idade mínima do cargo", artigo: CF("14, § 3º, VI, b") },
  ],
  ganha: {
    texto:
      "A Assembleia Legislativa do estado fixa o valor por lei. O Panóptico não traz o número porque ele não vem de fonte carregada.",
    artigo: CF("28, § 2º"),
    fonte: FONTE_CF,
  },
};

const DEPUTADO_ESTADUAL: Cargo = {
  id: "deputado-estadual",
  nome: "Deputado estadual",
  um: "um deputado estadual",
  oficial: "Assembleia Legislativa",
  faz: "Os deputados estaduais votam as leis do estado e acompanham o que o governador faz.",
  fazOficial: "Deputados estaduais",
  df: {
    nome: "Deputado distrital",
    faz: "Os deputados distritais votam as leis do Distrito Federal e acompanham o que o governador faz.",
    fazOficial: "Deputados distritais",
  },
  pode: [
    { texto: "Votar as leis do estado, no que a Constituição deixa aos estados", artigo: CF("24 e 25, § 1º") },
    { texto: "Fiscalizar o governador e as contas do estado, com o Tribunal de Contas do Estado, como a Constituição do estado detalha", artigo: CF("25, caput e 75") },
    { texto: "Falar e votar sem responder na Justiça por suas opiniões, palavras e votos, como os deputados federais", artigo: CF("27, § 1º") },
    { texto: "Decidir o regimento interno e organizar a administração da própria Assembleia", artigo: CF("27, § 3º") },
  ],
  naoPode: [
    { texto: "Criar leis do país sobre direito penal, civil ou eleitoral, por exemplo: isso é só da União", artigo: CF("22, I") },
    { texto: "Firmar contrato com o governo do estado nem ter cargo de confiança nele, como os deputados federais", artigo: CF("27, § 1º") },
    { texto: "Fixar o salário acima de 75% do que ganha um deputado federal", artigo: CF("27, § 2º") },
  ],
  ganha: {
    texto: `A Assembleia fixa o valor por lei estadual, com teto de 75% do que ganha um deputado federal, ou seja, no máximo ${formatarReais(TETO_DEPUTADO_ESTADUAL)} por mês. O valor de cada Assembleia aparece no perfil quando há fonte.`,
    artigo: CF("27, § 2º"),
    fonte: FONTE_CF,
  },
};

const PREFEITO: Cargo = {
  id: "prefeito",
  nome: "Prefeito",
  um: "um prefeito",
  oficial: "Poder Executivo municipal",
  faz: "O prefeito cuida do dia a dia da cidade: ruas, postos de saúde, escolas municipais e coleta de lixo.",
  fazOficial: "Chefia do Poder Executivo municipal",
  pode: [
    { texto: "Cuidar dos serviços da cidade, como o transporte coletivo", artigo: CF("30, I e V") },
    { texto: "Manter, com apoio da União e do estado, as escolas de educação infantil e ensino fundamental e os serviços de saúde", artigo: CF("30, VI e VII") },
    { texto: "Cobrar os tributos da cidade e decidir como aplicar o dinheiro, prestando contas", artigo: CF("30, III") },
  ],
  naoPode: [
    { texto: "Fazer leis sobre o que não é assunto da cidade, a não ser para completar a lei federal e a estadual", artigo: CF("30, I e II") },
    { texto: "Fixar o próprio salário: a lei é de iniciativa da Câmara de Vereadores", artigo: CF("29, V") },
    { texto: "Disputar um terceiro mandato seguido: a reeleição vale para um único período", artigo: CF("14, § 5º") },
    { texto: "Assumir outro cargo na administração pública sem perder o mandato, salvo por concurso", artigo: CF("29, XIV e 28, § 1º") },
    { texto: "Concorrer a outro cargo sem deixar a prefeitura até seis meses antes da eleição", artigo: CF("14, § 6º") },
  ],
  ganha: {
    texto:
      "A Câmara de Vereadores fixa o valor por lei. A Constituição diz quem define e que o valor não passa do teto do serviço público; o Panóptico não traz o número porque ele não vem de fonte carregada.",
    artigo: CF("29, V e 37, XI"),
    fonte: FONTE_CF,
  },
};

const VICE_PREFEITO: Cargo = {
  id: "vice-prefeito",
  nome: "Vice-prefeito",
  um: "um vice-prefeito",
  oficial: "Poder Executivo municipal",
  faz: "O vice-prefeito substitui o prefeito quando ele está impedido e assume se o cargo ficar vago, como a lei orgânica de cada cidade detalha.",
  fazOficial: "Substituição e sucessão do Prefeito",
  pode: [
    {
      texto: "Substituir o prefeito quando ele está impedido e assumir se o cargo ficar vago, como a lei orgânica da cidade detalha",
      artigo: CF("29, caput"),
    },
  ],
  naoPode: [
    { texto: "Fixar o próprio salário: a lei é de iniciativa da Câmara de Vereadores", artigo: CF("29, V") },
    { texto: "Ser eleito com menos de 21 anos: é a idade mínima do cargo", artigo: CF("14, § 3º, VI, c") },
  ],
  ganha: {
    texto: "A Câmara de Vereadores fixa o valor por lei. O Panóptico não traz o número porque ele não vem de fonte carregada.",
    artigo: CF("29, V"),
    fonte: FONTE_CF,
  },
};

const VEREADOR: Cargo = {
  id: "vereador",
  nome: "Vereador",
  um: "um vereador",
  oficial: "Câmara Municipal",
  faz: "Os vereadores votam as leis da cidade e fiscalizam o prefeito.",
  fazOficial: "Vereadores",
  pode: [
    { texto: "Propor e votar as leis da cidade, sobre assuntos de interesse local", artigo: CF("29, XI e 30, I") },
    { texto: "Fiscalizar o prefeito e as contas da cidade, com o Tribunal de Contas", artigo: CF("31") },
    { texto: "Derrubar, por dois terços, o parecer do Tribunal de Contas sobre as contas do prefeito", artigo: CF("31, § 2º") },
    { texto: "Aprovar, por dois terços, a lei orgânica da cidade, que funciona como a constituição local", artigo: CF("29, caput") },
    { texto: "Falar e votar sem responder na Justiça por suas opiniões, palavras e votos, dentro da cidade", artigo: CF("29, VIII") },
  ],
  naoPode: [
    { texto: "Criar leis do estado ou do país: elas cabem à Assembleia e ao Congresso", artigo: CF("22, 24 e 30, I") },
    { texto: "Firmar contrato com a prefeitura nem ter cargo de confiança nela, nas regras parecidas com as do Congresso", artigo: CF("29, IX") },
    { texto: "Receber mais do que o teto da faixa de população da cidade (veja “Quanto ganha”)", artigo: CF("29, VI") },
    { texto: "Ter salários que, somados, passem de 5% da receita da cidade", artigo: CF("29, VII") },
  ],
  ganha: {
    texto:
      "A câmara da cidade define o valor, em uma legislatura para a seguinte. O teto depende da população: de 20% (cidades de até 10 mil habitantes) a 75% (mais de 500 mil) do que ganha um deputado estadual.",
    artigo: CF("29, VI"),
    fonte: FONTE_CF,
  },
};

export const CARGOS: Record<CargoId, Cargo> = {
  presidente: PRESIDENTE,
  "vice-presidente": VICE_PRESIDENTE,
  senador: SENADOR,
  "deputado-federal": DEPUTADO_FEDERAL,
  governador: GOVERNADOR,
  "vice-governador": VICE_GOVERNADOR,
  "deputado-estadual": DEPUTADO_ESTADUAL,
  prefeito: PREFEITO,
  "vice-prefeito": VICE_PREFEITO,
  vereador: VEREADOR,
};

/** Na ordem em que a página de representantes lista os cargos, de cima para baixo. */
export const CARGOS_LISTA: Cargo[] = [
  PRESIDENTE,
  VICE_PRESIDENTE,
  SENADOR,
  DEPUTADO_FEDERAL,
  GOVERNADOR,
  VICE_GOVERNADOR,
  DEPUTADO_ESTADUAL,
  PREFEITO,
  VICE_PREFEITO,
  VEREADOR,
];

/** Texto do cargo, na variante do Distrito Federal quando existe e `df` é verdadeiro. */
export function textoDoCargo(cargo: Cargo, df = false): { nome: string; faz: string; fazOficial: string } {
  return df && cargo.df ? cargo.df : { nome: cargo.nome, faz: cargo.faz, fazOficial: cargo.fazOficial };
}

/**
 * Frase do salário do vereador para uma cidade de `habitantes` pessoas: o teto em percentual do
 * que ganha um deputado estadual, e a faixa. Não calcula valor em reais: o deputado estadual
 * ganha um valor diferente em cada estado.
 */
export function ganhaVereador(habitantes: number): { percentual: number; faixa: string; texto: string } {
  const faixa = FAIXAS_VEREADOR.find((f) => habitantes <= f.ate) ?? FAIXAS_VEREADOR[FAIXAS_VEREADOR.length - 1];
  return {
    percentual: faixa.percentual,
    faixa: faixa.rotulo,
    texto: `Numa cidade ${faixa.rotulo}, o teto do salário de vereador é ${faixa.percentual}% do que ganha um deputado estadual. A câmara da cidade define o valor.`,
  };
}

function simplificar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Cargo a partir do rótulo que a fonte usa ("Deputado Federal", "Vice-prefeito", "Vereadora").
 * Devolve `null` para o que não é um dos cargos (suplente, por exemplo).
 */
export function cargoDoRotulo(rotulo: string | null | undefined): CargoId | null {
  if (!rotulo) return null;
  const t = simplificar(rotulo);
  const vice = /\bvice\b/.test(t);
  if (/\bsuplente\b/.test(t)) return null;
  if (/\bpresidente\b|\bpresidenta\b/.test(t)) return vice ? "vice-presidente" : "presidente";
  if (/\bgovernador(a)?\b/.test(t)) return vice ? "vice-governador" : "governador";
  if (/\bprefeit[oa]\b/.test(t)) return vice ? "vice-prefeito" : "prefeito";
  if (/\bvereador(a)?\b/.test(t)) return "vereador";
  if (/\bsenador(a)?\b/.test(t)) return "senador";
  if (/\bdeputad[oa]\b/.test(t)) {
    if (/\bfederal\b/.test(t)) return "deputado-federal";
    if (/\b(estadual|distrital)\b/.test(t)) return "deputado-estadual";
  }
  return null;
}
