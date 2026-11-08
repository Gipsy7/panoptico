/**
 * Dicionário do site: as palavras oficiais da política em linguagem do dia a dia.
 *
 * O mesmo texto aparece em três lugares: na gaveta do <TermoOficial> (perfil, projetos, votações,
 * gastos...), no índice /dicionario e na resposta do Argos a "o que é X?". Cada termo traz a fonte
 * oficial (artigo da Constituição, do Regimento Interno da Câmara ou da lei), conferida no texto
 * consolidado em DICIONARIO_CONFERIDO_EM. Exemplos apontam para listagens reais do site, nunca para
 * número inventado. Funções puras (testadas no Vitest).
 */
import { CF_URL } from "@/lib/cargos";

export type FonteTermo = { rotulo: string; url: string };

export type Termo = {
  /** Âncora em /dicionario e chave do <TermoOficial id="...">. */
  id: string;
  /** Como a gente fala no dia a dia (título da explicação). */
  termo: string;
  /** Nome oficial, em letra menor. */
  oficial: string;
  /** Uma frase, para o índice. */
  resumo: string;
  /** Explicação completa, em linguagem simples. */
  explicacao: string;
  /** Onde ver isso no site (rota real; listagem filtrada quando depende de dado). */
  exemplo?: { rotulo: string; href: string };
  fonte: FonteTermo;
  /** Outras formas de escrever, para a busca e o Argos (sem acento, minúsculas). */
  sinonimos?: string[];
};

/** Data em que as explicações foram conferidas nos textos oficiais. */
export const DICIONARIO_CONFERIDO_EM = "2026-11-03";

const CF = "Constituição Federal de 1988";
const RICD = "Regimento Interno da Câmara dos Deputados";
const RICD_URL =
  "https://www2.camara.leg.br/legin/fed/rescad/1989/resolucaodacamaradosdeputados-17-21-setembro-1989-320110-normaatualizada-pl.html";
const L4320_URL = "https://www.planalto.gov.br/ccivil_03/leis/l4320.htm";
const LRF_URL = "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp101.htm";
const L9096_URL = "https://www.planalto.gov.br/ccivil_03/leis/l9096.htm";
const L9504_URL = "https://www.planalto.gov.br/ccivil_03/leis/l9504.htm";
const L8443_URL = "https://www.planalto.gov.br/ccivil_03/leis/l8443.htm";
const L12846_URL =
  "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm";
const L14133_URL =
  "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm";
const LC95_URL = "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp95.htm";
const ATO_CEAP_URL =
  "https://www2.camara.leg.br/legin/int/atomes/2009/atodamesa-43-21-maio-2009-588364-norma-cd-mesa.html";
const ATO_VERBA_GABINETE_URL =
  "https://www2.camara.leg.br/legin/int/atomes/2026/atodamesa-243-20-fevereiro-2026-798719-publicacaooriginal-178156-cd-mesa.html";
const ATO_MORADIA_URL =
  "https://www2.camara.leg.br/legin/int/atomes/2015/atodamesa-3-25-fevereiro-2015-780187-publicacaooriginal-146196-cd-mesa.html";
const STF_ADPF854_URL =
  "https://portal.stf.jus.br/processos/detalhe.asp?incidente=6199750";
const GLOSSARIO_ORCAMENTO_URL =
  "https://www.congressonacional.leg.br/legislacao-e-publicacoes/glossario-orcamentario";

const cf = (artigo: string): FonteTermo => ({
  rotulo: `${CF}, ${artigo}`,
  url: CF_URL,
});
const ricd = (artigo: string): FonteTermo => ({
  rotulo: `${RICD}, ${artigo}`,
  url: RICD_URL,
});

export const TERMOS: Termo[] = [
  // ---------- Propostas e leis ----------
  {
    id: "proposicao",
    termo: "Proposta",
    oficial: "Proposição legislativa",
    resumo: "Tudo o que é apresentado para a Casa votar.",
    explicacao:
      "Nome oficial de tudo o que é apresentado para a Câmara (ou outra Casa) decidir: projetos de lei, propostas de emenda à Constituição, medidas provisórias, requerimentos, emendas e pareceres.",
    exemplo: { rotulo: "Lista de projetos e votações", href: "/projetos" },
    fonte: ricd("art. 100"),
    sinonimos: [
      "proposicoes",
      "proposicao legislativa",
      "proposicoes legislativas",
    ],
  },
  {
    id: "pl",
    termo: "Projeto de lei",
    oficial: "Projeto de Lei (PL)",
    resumo: "Proposta de lei nova ou de mudança numa lei.",
    explicacao:
      "Proposta de uma lei nova ou de mudança numa lei que já existe. Passa pela Câmara e pelo Senado; depois o presidente da República aprova (sanciona) ou recusa (veta), no todo ou em parte. O Congresso pode derrubar o veto.",
    exemplo: { rotulo: "Lista de projetos e votações", href: "/projetos" },
    fonte: cf("arts. 61, 65 e 66"),
    sinonimos: ["pl", "projeto de lei", "projetos de lei", "lei ordinaria"],
  },
  {
    id: "plp",
    termo: "Projeto de lei complementar",
    oficial: "Projeto de Lei Complementar (PLP)",
    resumo: "Lei que detalha um ponto da Constituição; precisa de mais votos.",
    explicacao:
      "Lei para assuntos que a própria Constituição manda tratar em lei complementar, como regras de impostos e das finanças públicas. Para ser aprovada precisa da maioria absoluta: mais da metade de todos os deputados (257 de 513) e de todos os senadores (41 de 81).",
    fonte: cf("art. 69"),
    exemplo: {
      rotulo:
        "PLP 68/2024, que virou a Lei Complementar 214/2025 (reforma tributária)",
      href: "/projeto/camara/2430143",
    },
    sinonimos: ["plp", "lei complementar", "projeto de lei complementar"],
  },
  {
    id: "pec",
    termo: "PEC",
    oficial: "Proposta de Emenda à Constituição",
    resumo: "Proposta para mudar a Constituição.",
    explicacao:
      "Proposta para mudar a Constituição, a lei mais importante do país. É mais difícil de aprovar que uma lei comum: precisa de 3 em cada 5 votos (308 deputados e 49 senadores), em duas votações na Câmara e duas no Senado. Não passa pelo presidente da República: aprovada, o próprio Congresso a publica (promulga).",
    fonte: cf("art. 60"),
    exemplo: {
      rotulo: "PEC 66/2023, sobre o pagamento de precatórios pelos municípios",
      href: "/projeto/camara/2454495",
    },
    sinonimos: [
      "pec",
      "pecs",
      "emenda constitucional",
      "emenda a constituicao",
      "proposta de emenda a constituicao",
    ],
  },
  {
    id: "mp",
    termo: "Medida provisória",
    oficial: "Medida Provisória (MP ou MPV)",
    resumo: "Norma do presidente que vale na hora e o Congresso precisa votar.",
    explicacao:
      "Norma que o presidente da República publica sozinho, em caso de relevância e urgência, e que vale como lei desde o primeiro dia. O Congresso tem até 120 dias (60 mais 60) para votar; se não votar, ela perde a validade. Depois de 45 dias sem votação, ela trava boa parte das outras votações da Casa onde estiver, até ser votada.",
    fonte: cf("art. 62"),
    exemplo: {
      rotulo: "MP 1.343/2026, votada e transformada em lei",
      href: "/projeto/camara/2610975",
    },
    sinonimos: ["mp", "mpv", "mps", "medida provisoria", "medidas provisorias"],
  },
  {
    id: "pdl",
    termo: "Projeto de decreto legislativo",
    oficial: "Projeto de Decreto Legislativo (PDL)",
    resumo: "Decisão só do Congresso, sem passar pelo presidente.",
    explicacao:
      "Forma de o Congresso decidir sozinho os assuntos que a Constituição dá só a ele: aprovar tratados internacionais, suspender um decreto do presidente que passou do limite da lei, fixar o salário dos parlamentares e do presidente. Não vai para sanção.",
    fonte: cf("arts. 49 e 59, VI"),
    exemplo: {
      rotulo:
        "PDL 41/2026, que aprova o acordo de comércio entre o Mercosul e a União Europeia",
      href: "/projeto/senado/172821",
    },
    sinonimos: ["pdl", "decreto legislativo", "projeto de decreto legislativo"],
  },
  {
    id: "ementa",
    termo: "Resumo do projeto",
    oficial: "Ementa",
    resumo: "A frase oficial que diz do que trata a lei.",
    explicacao:
      "A frase curta, logo no começo de uma lei ou projeto, que diz de forma resumida do que ele trata. É escrita por quem apresenta o projeto; para saber o que muda de verdade, vale ler o texto inteiro.",
    exemplo: { rotulo: "Projetos com a ementa de cada um", href: "/projetos" },
    fonte: { rotulo: "Lei Complementar nº 95/1998, art. 5º", url: LC95_URL },
    sinonimos: ["ementa", "ementas"],
  },
  {
    id: "sancao",
    termo: "Sanção",
    oficial: "Sanção presidencial",
    resumo: "O presidente aprova a lei votada pelo Congresso.",
    explicacao:
      "Quando o presidente da República (ou o governador, ou o prefeito) concorda com o projeto aprovado e ele vira lei. O presidente tem 15 dias úteis para decidir; se não disser nada nesse prazo, o projeto é considerado sancionado.",
    fonte: cf("art. 66"),
    sinonimos: ["sancao", "sancionar", "sancionou", "sancionada", "sancionado"],
  },
  {
    id: "veto",
    termo: "Veto",
    oficial: "Veto",
    resumo: "O presidente recusa a lei, toda ou uma parte.",
    explicacao:
      "Quando o presidente da República recusa um projeto aprovado pelo Congresso, inteiro (veto total) ou só alguns trechos (veto parcial), por achá-lo contra a Constituição ou contra o interesse público. O Congresso analisa o veto em sessão conjunta e pode derrubá-lo com a maioria absoluta dos deputados (257) e dos senadores (41).",
    fonte: cf("art. 66, §§ 1º a 6º"),
    sinonimos: [
      "veto",
      "vetos",
      "vetou",
      "veto parcial",
      "veto total",
      "derrubada de veto",
    ],
  },
  {
    id: "promulgacao",
    termo: "Promulgação",
    oficial: "Promulgação",
    resumo: "O ato que declara que a lei existe e pode ser publicada.",
    explicacao:
      "Ato que declara que uma lei ou emenda à Constituição passou a existir e manda publicá-la. A lei é promulgada pelo presidente da República; as emendas à Constituição, pelas Mesas da Câmara e do Senado.",
    fonte: cf("arts. 60, § 3º, e 66, §§ 5º e 7º"),
    sinonimos: ["promulgacao", "promulgada", "promulgou", "promulgar"],
  },
  {
    id: "decreto",
    termo: "Decreto",
    oficial: "Decreto do Poder Executivo",
    resumo: "Norma do presidente para pôr uma lei em prática.",
    explicacao:
      "Norma assinada pelo presidente da República (ou governador, ou prefeito) para explicar como uma lei vai ser aplicada. O decreto não pode criar obrigação que a lei não criou; se passar do limite, o Congresso pode suspendê-lo.",
    fonte: cf("arts. 84, IV, e 49, V"),
    sinonimos: ["decreto", "decretos", "decreto presidencial"],
  },
  {
    id: "arquivamento",
    termo: "Arquivado",
    oficial: "Arquivamento de proposição",
    resumo: "O projeto para de andar; pode ser desarquivado.",
    explicacao:
      "Quando um projeto deixa de tramitar. Na Câmara, ao fim de cada legislatura (a cada 4 anos) os projetos que não foram votados são arquivados, com algumas exceções; o autor reeleito pode pedir o desarquivamento.",
    fonte: ricd("art. 105"),
    sinonimos: ["arquivado", "arquivada", "arquivamento", "arquivar"],
  },
  {
    id: "urgencia",
    termo: "Urgência",
    oficial: "Regime de urgência",
    resumo: "Atalho que faz o projeto pular etapas e ser votado antes.",
    explicacao:
      "Atalho que dispensa prazos e etapas do caminho normal, para o projeto ser votado mais cedo. O pedido de urgência é votado no Plenário. Há uma urgência mais forte, que põe o projeto na pauta do mesmo dia e precisa do apoio da maioria absoluta da Câmara (257 deputados).",
    fonte: ricd("arts. 152 a 155"),
    sinonimos: [
      "urgencia",
      "regime de urgencia",
      "requerimento de urgencia",
      "urgencia urgentissima",
    ],
  },
  {
    id: "destaque",
    termo: "Destaque",
    oficial: "Destaque para votação em separado",
    resumo: "Pedido para votar um trecho do projeto à parte.",
    explicacao:
      "Pedido para que um trecho do projeto (ou uma emenda) seja votado separado do resto. Assim, o Plenário aprova o texto principal e decide depois, em outra votação, se aquele trecho fica ou sai.",
    fonte: ricd("art. 161"),
    sinonimos: ["destaque", "destaques", "dvs", "votacao em separado"],
  },

  // ---------- Como se vota ----------
  {
    id: "plenario",
    termo: "Plenário",
    oficial: "Plenário da Câmara ou do Senado",
    resumo: "Reunião em que a Casa toda vota.",
    explicacao:
      "Reunião em que todos os deputados (ou todos os senadores) podem votar. Muitos projetos passam antes pelas comissões, grupos menores que estudam cada assunto.",
    exemplo: {
      rotulo: "Projetos com votação nominal",
      href: "/projetos?votacao=com",
    },
    fonte: { rotulo: RICD, url: RICD_URL },
    sinonimos: ["plenario"],
  },
  {
    id: "votacao-nominal",
    termo: "Votação nominal",
    oficial: "Processo nominal de votação",
    resumo: "Cada voto fica registrado com o nome.",
    explicacao:
      "Votação em que cada parlamentar registra o voto (Sim, Não ou Abstenção) no painel eletrônico, e a lista com o nome de cada um fica pública. É dela que vêm os números de presença e de votos do Panóptico.",
    exemplo: {
      rotulo: "Projetos com votação nominal",
      href: "/projetos?votacao=com",
    },
    fonte: ricd("arts. 184 e 186"),
    sinonimos: ["votacao nominal", "votacoes nominais", "voto nominal"],
  },
  {
    id: "votacao-simbolica",
    termo: "Votação simbólica",
    oficial: "Processo simbólico de votação",
    resumo: "Votação sem registro do voto de cada um.",
    explicacao:
      "Votação em que ninguém registra o voto no painel: quem preside pede que os favoráveis fiquem como estão e anuncia o resultado. Por isso não dá para saber como cada parlamentar votou, e ela não entra na conta de votos de ninguém. Os parlamentares podem pedir a verificação, que transforma a votação em nominal.",
    fonte: ricd("art. 185"),
    sinonimos: [
      "votacao simbolica",
      "votacoes simbolicas",
      "voto simbolico",
      "simbolica",
    ],
  },
  {
    id: "obstrucao",
    termo: "Obstrução",
    oficial: "Obstrução parlamentar",
    resumo: "Forma de atrasar ou impedir uma votação.",
    explicacao:
      'Forma de atrasar ou impedir uma votação: parlamentares de um partido deixam de registrar voto, para que não se alcance o número mínimo de presentes (quórum). Quando a obstrução é decidida pela liderança do partido e comunicada à Mesa, a lista de votos mostra "Obstrução" ao lado do nome e ela não conta como falta.',
    fonte: ricd("art. 82, § 6º"),
    sinonimos: [
      "obstrucao",
      "obstrucao parlamentar",
      "em obstrucao",
      "obstruir",
    ],
  },
  {
    id: "quorum",
    termo: "Quórum",
    oficial: "Quórum de deliberação",
    resumo: "Número mínimo de presentes para votar.",
    explicacao:
      "Número mínimo de parlamentares presentes para que uma votação valha. Pela regra geral, a decisão é tomada pela maioria dos votos, desde que esteja presente a maioria absoluta da Casa: 257 dos 513 deputados ou 41 dos 81 senadores.",
    fonte: cf("art. 47"),
    sinonimos: ["quorum", "quoruns"],
  },
  {
    id: "maioria-absoluta",
    termo: "Maioria absoluta",
    oficial: "Maioria absoluta dos membros",
    resumo: "Mais da metade de todos os membros, presentes ou não.",
    explicacao:
      "Mais da metade de todos os membros da Casa, contando quem faltou: 257 dos 513 deputados ou 41 dos 81 senadores. É diferente da maioria simples, que conta só quem votou. Leis complementares e a derrubada de veto pedem maioria absoluta; mudanças na Constituição pedem 3/5.",
    fonte: cf("arts. 47, 60 e 69"),
    sinonimos: [
      "maioria absoluta",
      "maioria simples",
      "maioria qualificada",
      "tres quintos",
    ],
  },
  {
    id: "orientacao",
    termo: "Orientação de voto",
    oficial: "Orientação de bancada",
    resumo: "Como o líder pede que o grupo vote.",
    explicacao:
      "Antes de cada votação, o líder de cada partido, bloco ou federação (e o líder do Governo) diz no microfone como recomenda que seu grupo vote: Sim, Não, Obstrução ou liberado. Cada parlamentar continua livre para votar diferente; o Panóptico mostra quantas vezes seguiu a orientação.",
    fonte: ricd("arts. 9º a 11"),
    sinonimos: [
      "orientacao",
      "orientacao de voto",
      "orientacao de bancada",
      "orientacao do governo",
      "orientou",
    ],
  },
  {
    id: "lider",
    termo: "Líder",
    oficial: "Líder de bancada (partido ou bloco)",
    resumo: "Quem fala em nome do partido ou bloco.",
    explicacao:
      "Deputado escolhido pelo partido ou bloco para falar em nome dele, orientar o voto da bancada e indicar quem ocupa as vagas nas comissões. O presidente da República pode indicar um Líder do Governo.",
    fonte: ricd("arts. 9º a 11"),
    sinonimos: [
      "lider",
      "lideres",
      "lideranca",
      "lider do governo",
      "lider da oposicao",
    ],
  },
  {
    id: "bancada",
    termo: "Bancada",
    oficial: "Representação partidária",
    resumo: "O grupo de parlamentares de um partido (ou de um estado).",
    explicacao:
      "O conjunto de parlamentares de um mesmo partido na Casa. A palavra também é usada para o grupo de um mesmo estado (bancada de Minas) ou de um mesmo interesse (bancada da saúde), mas só a do partido tem regras no Regimento.",
    exemplo: {
      rotulo: "Deputados e senadores por partido",
      href: "/parlamentares",
    },
    fonte: ricd("art. 9º"),
    sinonimos: ["bancada", "bancadas", "representacao partidaria"],
  },
  {
    id: "bloco-parlamentar",
    termo: "Bloco",
    oficial: "Bloco Parlamentar",
    resumo: "Partidos que se juntam sob um só líder.",
    explicacao:
      "Dois ou mais partidos que se juntam na Casa, sob uma liderança comum, para orientar votos e dividir vagas nas comissões. Vale só dentro da Casa e pode ser desfeito.",
    fonte: ricd("art. 12"),
    sinonimos: ["bloco", "blocos", "bloco parlamentar"],
  },
  {
    id: "mesa-diretora",
    termo: "Mesa Diretora",
    oficial: "Mesa da Câmara dos Deputados",
    resumo: "O grupo que dirige a Casa: presidente, vices e secretários.",
    explicacao:
      "Grupo que dirige os trabalhos e a administração da Casa. Na Câmara são sete deputados: o presidente, dois vice-presidentes e quatro secretários, eleitos pelos colegas para mandato de dois anos.",
    fonte: ricd("art. 14"),
    sinonimos: [
      "mesa",
      "mesa diretora",
      "mesa da camara",
      "presidente da camara",
    ],
  },
  {
    id: "comissao",
    termo: "Comissão",
    oficial: "Comissão permanente",
    resumo: "Grupo menor que estuda um assunto antes do Plenário.",
    explicacao:
      "Grupo de parlamentares que estuda os projetos de um assunto (saúde, educação, orçamento...) antes do Plenário. Em muitos casos a própria comissão aprova ou rejeita o projeto, sem ir ao Plenário (o chamado poder conclusivo).",
    fonte: { rotulo: `${CF}, art. 58, e ${RICD}, art. 24`, url: CF_URL },
    sinonimos: [
      "comissao",
      "comissoes",
      "comissao permanente",
      "poder conclusivo",
    ],
  },
  {
    id: "relator",
    termo: "Relator",
    oficial: "Relator da proposição",
    resumo: "Quem estuda o projeto e diz se deve ser aprovado.",
    explicacao:
      "Parlamentar escolhido para estudar um projeto numa comissão ou no Plenário e escrever o parecer: o texto que recomenda aprovar, rejeitar ou mudar o projeto. Muitas vezes o relator apresenta uma nova versão do texto.",
    fonte: ricd("art. 56"),
    sinonimos: ["relator", "relatora", "relatoria"],
  },
  {
    id: "parecer",
    termo: "Parecer",
    oficial: "Parecer de comissão",
    resumo: "A opinião oficial da comissão sobre um projeto.",
    explicacao:
      "Documento em que a comissão diz o que acha de um projeto: se deve ser aprovado, rejeitado ou mudado. É escrito pelo relator e votado pela comissão.",
    fonte: ricd("art. 126"),
    sinonimos: ["parecer", "pareceres"],
  },
  {
    id: "cpi",
    termo: "CPI",
    oficial: "Comissão Parlamentar de Inquérito",
    resumo: "Comissão que investiga um fato determinado.",
    explicacao:
      "Comissão criada para investigar um fato determinado, por prazo certo, a pedido de um terço dos deputados ou dos senadores (quando reúne as duas Casas, chama-se CPMI). Pode ouvir testemunhas e pedir documentos. No fim, o relatório vai ao Ministério Público, que decide se acusa alguém na Justiça.",
    fonte: cf("art. 58, § 3º"),
    sinonimos: [
      "cpi",
      "cpis",
      "cpmi",
      "cpmis",
      "comissao parlamentar de inquerito",
    ],
  },
  {
    id: "indiciamento",
    termo: "Pedido de indiciamento",
    oficial: "Indiciamento em relatório de CPI",
    resumo: "A CPI sugere que alguém seja investigado ou acusado.",
    explicacao:
      "No relatório final, a CPI pode pedir que uma pessoa seja indiciada, isto é, apontada como suspeita. É uma proposta da comissão: não é acusação formal nem condenação. Cabe ao Ministério Público decidir se denuncia a pessoa à Justiça.",
    fonte: cf("art. 58, § 3º"),
    sinonimos: ["indiciamento", "indiciado", "indiciada", "indiciar"],
  },
  {
    id: "legislatura",
    termo: "Legislatura",
    oficial: "Legislatura",
    resumo: "Os 4 anos de um mandato de deputado.",
    explicacao:
      "Período de 4 anos que corresponde ao mandato dos deputados. A legislatura atual começou em 1º de fevereiro de 2023 e vai até janeiro de 2027. Senadores têm mandato de 8 anos, ou seja, duas legislaturas.",
    fonte: cf("arts. 44 e 46"),
    sinonimos: ["legislatura", "legislaturas"],
  },
  {
    id: "sessao-legislativa",
    termo: "Ano de trabalho do Congresso",
    oficial: "Sessão legislativa",
    resumo: "De fevereiro a dezembro, com recesso em julho.",
    explicacao:
      "O ano de trabalho do Congresso: de 2 de fevereiro a 17 de julho e de 1º de agosto a 22 de dezembro. Fora desses períodos é o recesso, quando só há sessão se houver convocação extraordinária.",
    fonte: cf("art. 57"),
    sinonimos: ["sessao legislativa", "recesso", "recesso parlamentar"],
  },
  {
    id: "suplente",
    termo: "Suplente",
    oficial: "Suplente",
    resumo: "Quem assume quando o titular sai ou se licencia.",
    explicacao:
      "Pessoa que assume a cadeira quando o titular sai, se licencia por mais de 120 dias ou vira ministro ou secretário. Na Câmara, é o próximo mais votado da mesma lista partidária; no Senado, cada senador é eleito com dois suplentes.",
    fonte: cf("arts. 46, § 3º, e 56, § 1º"),
    sinonimos: ["suplente", "suplentes", "suplencia"],
  },
  {
    id: "segundo-turno",
    termo: "Segundo turno",
    oficial: "Segundo turno de votação",
    resumo: "Nova eleição entre os dois mais votados.",
    explicacao:
      "Nova votação entre os dois candidatos mais votados quando nenhum teve mais da metade dos votos válidos no primeiro turno. Vale para presidente, governador e prefeito de cidades com mais de 200 mil eleitores.",
    exemplo: { rotulo: "Página do segundo turno", href: "/segundo-turno" },
    fonte: cf("arts. 28, 29, II, e 77, § 3º"),
    sinonimos: ["segundo turno", "2o turno", "2 turno"],
  },

  // ---------- Dinheiro do mandato ----------
  {
    id: "subsidio",
    termo: "Salário",
    oficial: "Subsídio",
    resumo: "O salário do político eleito, em parcela única.",
    explicacao:
      "Nome oficial do salário de quem tem mandato. É pago em parcela única, sem gratificação somada. O dos deputados federais e senadores é fixado pelo próprio Congresso; o dos deputados estaduais, pela Assembleia, até 75% do federal; o dos vereadores, pela Câmara Municipal, com limite pelo tamanho da cidade.",
    fonte: cf("arts. 27, § 2º, 29, VI, 39, § 4º, e 49, VII"),
    sinonimos: [
      "subsidio",
      "subsidios",
      "salario",
      "salario de deputado",
      "salario de senador",
    ],
  },
  {
    id: "cota",
    termo: "Cota parlamentar",
    oficial: "Cota para o Exercício da Atividade Parlamentar (CEAP)",
    resumo: "Verba mensal para despesas do mandato. Não é salário.",
    explicacao:
      "Dinheiro que cada deputado pode usar todo mês em despesas do mandato: passagens, combustível, aluguel de escritório no estado, telefone, divulgação. Não é salário: é reembolso, só com nota fiscal, e o valor muda de estado para estado por causa do preço das passagens. No Senado se chama CEAPS.",
    exemplo: {
      rotulo: "Parlamentares por gasto da cota",
      href: "/parlamentares?ordenar=gastos",
    },
    fonte: {
      rotulo: "Câmara dos Deputados, Ato da Mesa nº 43/2009",
      url: ATO_CEAP_URL,
    },
    sinonimos: [
      "cota",
      "cota parlamentar",
      "ceap",
      "ceaps",
      "gastos do gabinete",
      "cota para o exercicio da atividade parlamentar",
    ],
  },
  {
    id: "verba-gabinete",
    termo: "Verba para pagar assessores",
    oficial: "Verba de gabinete",
    resumo:
      "Dinheiro por mês para pagar a equipe do gabinete. Não é salário nem cota.",
    explicacao:
      "Valor máximo que a Casa paga por mês em salários da equipe que o parlamentar escolhe para trabalhar com ele, em Brasília ou no estado. Na Câmara, paga de 5 a 25 secretários parlamentares, que são servidores comissionados e recebem da própria Câmara. É separada da cota parlamentar e do salário.",
    fonte: {
      rotulo: "Câmara dos Deputados, Ato da Mesa nº 243/2026",
      url: ATO_VERBA_GABINETE_URL,
    },
    sinonimos: [
      "verba de gabinete",
      "verba do gabinete",
      "assessores",
      "secretario parlamentar",
      "secretarios parlamentares",
    ],
  },
  {
    id: "auxilio-moradia",
    termo: "Moradia em Brasília",
    oficial: "Auxílio-moradia ou imóvel funcional",
    resumo:
      "Ajuda para morar em Brasília, para quem não usa apartamento da Casa.",
    explicacao:
      "Quem tem mandato no Congresso pode morar num apartamento funcional, que é da Câmara ou do Senado, ou receber o auxílio-moradia, um valor máximo por mês para aluguel ou hotel em Brasília. Não dá para ter os dois. Na Câmara o limite é fixado por ato da Mesa; no Senado, a página de transparência publica o valor.",
    fonte: {
      rotulo: "Câmara dos Deputados, Ato da Mesa nº 3/2015",
      url: ATO_MORADIA_URL,
    },
    sinonimos: ["auxilio moradia", "apartamento funcional", "imovel funcional"],
  },

  // ---------- Orçamento e emendas ----------
  {
    id: "ppa",
    termo: "Plano de 4 anos",
    oficial: "Plano Plurianual (PPA)",
    resumo: "Metas do governo para 4 anos.",
    explicacao:
      "Lei que define as metas e os programas do governo para 4 anos, por região. Os orçamentos de cada ano precisam seguir o que está no plano.",
    fonte: cf("art. 165, § 1º"),
    sinonimos: ["ppa", "plano plurianual"],
  },
  {
    id: "ldo",
    termo: "Regras do orçamento",
    oficial: "Lei de Diretrizes Orçamentárias (LDO)",
    resumo: "Lei que diz as prioridades e regras do orçamento do ano seguinte.",
    explicacao:
      "Lei votada todo ano que diz as metas, as prioridades e as regras para montar o orçamento do ano seguinte. Vem antes do orçamento propriamente dito.",
    fonte: cf("art. 165, § 2º"),
    sinonimos: [
      "ldo",
      "lei de diretrizes orcamentarias",
      "diretrizes orcamentarias",
    ],
  },
  {
    id: "loa",
    termo: "Orçamento",
    oficial: "Lei Orçamentária Anual (LOA)",
    resumo: "Lei que diz quanto o governo pode gastar em cada coisa no ano.",
    explicacao:
      "Lei votada todo ano que lista quanto o governo prevê arrecadar e quanto pode gastar em cada área no ano seguinte. O governo manda o projeto, e deputados e senadores podem mudá-lo com emendas.",
    exemplo: {
      rotulo: "Impostos e repasses por cidade e estado",
      href: "/impostos-e-repasses",
    },
    fonte: cf("arts. 165, § 5º, e 166"),
    sinonimos: [
      "loa",
      "orcamento",
      "lei orcamentaria",
      "lei orcamentaria anual",
      "orcamento da uniao",
    ],
  },
  {
    id: "emenda-parlamentar",
    termo: "Emenda parlamentar",
    oficial: "Emenda ao Orçamento da União",
    resumo: "Pedido de um parlamentar para usar parte do Orçamento.",
    explicacao:
      "Pedido de deputados e senadores para que parte do dinheiro do Orçamento da União vá para um fim: uma obra, um posto de saúde, um repasse para uma cidade. Pode ser individual, de bancada estadual, de comissão ou, até 2022, de relator. As individuais e as de bancada têm pagamento obrigatório, dentro dos limites da Constituição.",
    exemplo: {
      rotulo: "Emendas que chegaram à sua cidade (digite o CEP)",
      href: "/#cep",
    },
    fonte: cf("art. 166"),
    sinonimos: [
      "emenda",
      "emendas",
      "emenda parlamentar",
      "emendas parlamentares",
      "emenda ao orcamento",
    ],
  },
  {
    id: "emenda-individual",
    termo: "Emenda individual",
    oficial: "Emenda individual ao orçamento",
    resumo: "A parte do orçamento que cada parlamentar indica sozinho.",
    explicacao:
      "Emenda que cada deputado ou senador apresenta sozinho. Todas juntas podem somar até 2% da receita corrente líquida do ano anterior, e metade desse valor tem de ir para a saúde. O governo é obrigado a pagar, salvo impedimento técnico.",
    exemplo: {
      rotulo: "Parlamentares por valor de emendas",
      href: "/parlamentares?ordenar=emendas",
    },
    fonte: cf("art. 166, §§ 9º e 11"),
    sinonimos: [
      "emenda individual",
      "emendas individuais",
      "emenda impositiva",
      "emendas impositivas",
    ],
  },
  {
    id: "emenda-bancada",
    termo: "Emenda de bancada",
    oficial: "Emenda de bancada estadual",
    resumo: "Emenda apresentada em conjunto pelos parlamentares de um estado.",
    explicacao:
      "Emenda apresentada em conjunto pelos deputados e senadores de um mesmo estado, para obras e projetos do estado. Também tem pagamento obrigatório, até 1% da receita corrente líquida. Não aparece no nome de um parlamentar só.",
    fonte: cf("art. 166, § 12"),
    sinonimos: ["emenda de bancada", "emendas de bancada"],
  },
  {
    id: "emenda-comissao",
    termo: "Emenda de comissão",
    oficial: "Emenda de comissão (RP8)",
    resumo: "Emenda apresentada por uma comissão do Congresso.",
    explicacao:
      "Emenda ao orçamento apresentada por uma comissão da Câmara, do Senado ou mista, e não por um parlamentar. O pagamento não é obrigatório pela Constituição. Não aparece no nome de um parlamentar só.",
    fonte: {
      rotulo: "Congresso Nacional, Glossário de termos orçamentários",
      url: GLOSSARIO_ORCAMENTO_URL,
    },
    sinonimos: ["emenda de comissao", "emendas de comissao", "rp8"],
  },
  {
    id: "emenda-relator",
    termo: "Emenda de relator",
    oficial: "Emenda de relator-geral (RP9)",
    resumo: "Emendas do relator do orçamento, de 2020 a 2022.",
    explicacao:
      'Emendas que o relator-geral do orçamento incluía e que eram distribuídas por indicação de parlamentares, sem o nome deles aparecer no orçamento (o chamado "orçamento secreto"). Foram usadas de 2020 a 2022, até o Supremo Tribunal Federal julgá-las contra a Constituição, em dezembro de 2022.',
    fonte: {
      rotulo: "Supremo Tribunal Federal, ADPF 854",
      url: STF_ADPF854_URL,
    },
    sinonimos: [
      "emenda de relator",
      "emendas de relator",
      "rp9",
      "orcamento secreto",
      "relator geral",
    ],
  },
  {
    id: "transferencia-especial",
    termo: "Emenda Pix",
    oficial: "Transferência especial",
    resumo: "Emenda que cai direto no caixa da prefeitura ou do estado.",
    explicacao:
      'Forma de pagar emenda individual em que o dinheiro vai direto para o caixa da prefeitura ou do estado, sem convênio e sem dizer antes em qual obra ou serviço será usado. Por isso ficou conhecida como "emenda Pix". Ao ser transferido, o dinheiro passa a pertencer ao estado ou ao município.',
    exemplo: {
      rotulo: "Emendas que chegaram à sua cidade (digite o CEP)",
      href: "/#cep",
    },
    fonte: cf("art. 166-A"),
    sinonimos: [
      "emenda pix",
      "emendas pix",
      "transferencia especial",
      "transferencias especiais",
    ],
  },
  {
    id: "transferencia-voluntaria",
    termo: "Convênio",
    oficial: "Transferência voluntária",
    resumo:
      "Dinheiro que o governo federal manda por acordo, para um fim certo.",
    explicacao:
      "Dinheiro que a União manda a um estado ou cidade por acordo (convênio ou contrato de repasse), para um fim combinado, sem ser obrigada por lei. Quem recebe precisa cumprir regras e prestar contas do uso.",
    exemplo: {
      rotulo: "Repasses para cada cidade",
      href: "/impostos-e-repasses",
    },
    fonte: {
      rotulo: "Lei de Responsabilidade Fiscal (LC nº 101/2000), art. 25",
      url: LRF_URL,
    },
    sinonimos: [
      "convenio",
      "convenios",
      "transferencia voluntaria",
      "transferencias voluntarias",
      "contrato de repasse",
    ],
  },
  {
    id: "empenho",
    termo: "Valor reservado",
    oficial: "Empenho",
    resumo: "O governo reserva o dinheiro para uma despesa.",
    explicacao:
      "Primeiro passo de um gasto público: o governo reserva o dinheiro do orçamento para uma despesa. Empenhado ainda não é pago; o serviço precisa ser entregue e conferido (liquidação) antes do pagamento.",
    fonte: { rotulo: "Lei nº 4.320/1964, art. 58", url: L4320_URL },
    sinonimos: [
      "empenho",
      "empenhado",
      "empenhada",
      "empenhos",
      "valor empenhado",
    ],
  },
  {
    id: "liquidacao",
    termo: "Entrega conferida",
    oficial: "Liquidação da despesa",
    resumo: "O governo confere que recebeu o que comprou.",
    explicacao:
      "Segundo passo de um gasto público: o governo confere que a obra, o produto ou o serviço foi entregue como combinado. Só depois disso pode pagar.",
    fonte: { rotulo: "Lei nº 4.320/1964, art. 63", url: L4320_URL },
    sinonimos: ["liquidacao", "liquidado", "liquidada", "valor liquidado"],
  },
  {
    id: "pagamento",
    termo: "Valor pago",
    oficial: "Pagamento da despesa",
    resumo: "O dinheiro sai de fato do caixa.",
    explicacao:
      "Último passo de um gasto público: o dinheiro sai de fato do caixa do governo. Só pode acontecer depois da liquidação. Quando o Panóptico fala em valor pago, é este.",
    fonte: { rotulo: "Lei nº 4.320/1964, arts. 62 e 64", url: L4320_URL },
    sinonimos: ["pagamento", "valor pago", "pago", "pagos"],
  },
  {
    id: "restos-a-pagar",
    termo: "Contas que ficam para o ano seguinte",
    oficial: "Restos a pagar",
    resumo: "Despesa de um ano paga só no ano seguinte.",
    explicacao:
      "Despesas empenhadas num ano e não pagas até 31 de dezembro. Passam para os anos seguintes e são pagas depois, por isso o valor pago num ano pode incluir despesas de anos anteriores.",
    fonte: { rotulo: "Lei nº 4.320/1964, art. 36", url: L4320_URL },
    sinonimos: ["restos a pagar", "resto a pagar"],
  },
  {
    id: "fpm",
    termo: "Fundo das cidades",
    oficial: "Fundo de Participação dos Municípios (FPM)",
    resumo: "Parte do Imposto de Renda e do IPI que vai para as cidades.",
    explicacao:
      "Parte do Imposto de Renda e do IPI arrecadados pela União que a Constituição manda dividir entre todas as cidades, pelo tamanho da população e pela renda. É obrigatório: não depende de emenda nem de acordo.",
    exemplo: {
      rotulo: "Impostos e repasses por cidade",
      href: "/impostos-e-repasses",
    },
    fonte: cf("art. 159, I, b, d, e e f"),
    sinonimos: ["fpm", "fundo de participacao dos municipios"],
  },
  {
    id: "fpe",
    termo: "Fundo dos estados",
    oficial: "Fundo de Participação dos Estados e do Distrito Federal (FPE)",
    resumo: "Parte do Imposto de Renda e do IPI que vai para os estados.",
    explicacao:
      "Parte do Imposto de Renda e do IPI arrecadados pela União (21,5%) que a Constituição manda dividir entre os estados e o Distrito Federal. É obrigatório: não depende de emenda nem de acordo.",
    exemplo: {
      rotulo: "Impostos e repasses por estado",
      href: "/impostos-e-repasses",
    },
    fonte: cf("art. 159, I, a"),
    sinonimos: ["fpe", "fundo de participacao dos estados"],
  },
  {
    id: "fundeb",
    termo: "Fundo da educação básica",
    oficial: "Fundeb",
    resumo: "Fundo que divide dinheiro de impostos para as escolas públicas.",
    explicacao:
      "Fundo de cada estado que junta parte dos impostos do estado e das cidades e divide pelo número de alunos da rede pública, da creche ao ensino médio. A União completa o valor onde o dinheiro por aluno fica abaixo do mínimo.",
    exemplo: {
      rotulo: "Impostos e repasses por cidade",
      href: "/impostos-e-repasses",
    },
    fonte: cf("art. 212-A"),
    sinonimos: ["fundeb"],
  },

  // ---------- Fiscalização e punições ----------
  {
    id: "tcu",
    termo: "Tribunal de Contas da União",
    oficial: "Tribunal de Contas da União (TCU)",
    resumo: "Órgão que fiscaliza o uso do dinheiro federal.",
    explicacao:
      "Órgão que ajuda o Congresso a fiscalizar o dinheiro federal. Julga as contas de quem cuida de dinheiro público e pode aplicar multa, mandar devolver valores e proibir a pessoa de ocupar cargo de confiança. Não é parte do Judiciário: tem nove ministros.",
    fonte: cf("arts. 71 a 73"),
    sinonimos: ["tcu", "tribunal de contas da uniao"],
  },
  {
    id: "tce",
    termo: "Tribunal de Contas do Estado",
    oficial: "Tribunal de Contas do Estado (TCE)",
    resumo: "Órgão que fiscaliza o dinheiro do estado e das cidades.",
    explicacao:
      "Órgão que ajuda a Assembleia Legislativa a fiscalizar o dinheiro do estado e, na maioria dos estados, também o das prefeituras e câmaras municipais.",
    fonte: cf("arts. 31, § 1º, e 75"),
    sinonimos: ["tce", "tribunal de contas do estado", "tribunais de contas"],
  },
  {
    id: "tcm",
    termo: "Tribunal de Contas dos Municípios",
    oficial: "Tribunal de Contas do Município ou dos Municípios (TCM)",
    resumo: "Em alguns lugares, é quem fiscaliza as prefeituras.",
    explicacao:
      "Em alguns estados e nas cidades de São Paulo e do Rio de Janeiro, um tribunal próprio fiscaliza as prefeituras e câmaras municipais, no lugar do TCE. A Constituição proíbe criar novos tribunais de contas municipais.",
    fonte: cf("art. 31, §§ 1º e 4º"),
    sinonimos: [
      "tcm",
      "tribunal de contas do municipio",
      "tribunal de contas dos municipios",
    ],
  },
  {
    id: "contas-irregulares",
    termo: "Contas reprovadas",
    oficial: "Contas julgadas irregulares (TCU)",
    resumo: "O TCU concluiu que houve problema no uso do dinheiro.",
    explicacao:
      "Decisão do Tribunal de Contas da União de que quem cuidou de dinheiro público não prestou contas, causou prejuízo ou desrespeitou a lei. Pode vir com multa e ordem de devolver valores. O TCU também pode proibir a pessoa de ocupar cargo de confiança no governo federal por 5 a 8 anos (inabilitação). Não é condenação criminal.",
    fonte: {
      rotulo: "Lei nº 8.443/1992 (Lei Orgânica do TCU), arts. 16, III, e 60",
      url: L8443_URL,
    },
    sinonimos: [
      "contas irregulares",
      "contas julgadas irregulares",
      "inabilitacao",
      "contas reprovadas",
    ],
  },
  {
    id: "cadastros-cgu",
    termo: "Cadastros de punições da CGU",
    oficial: "CEIS, CNEP e CEAF",
    resumo: "Listas públicas de empresas e pessoas punidas pelo governo.",
    explicacao:
      "Listas públicas mantidas pela Controladoria-Geral da União: o CEIS reúne empresas e pessoas proibidas de contratar com o governo; o CNEP, empresas punidas pela Lei Anticorrupção; o CEAF, servidores federais expulsos. Estar na lista mostra uma punição administrativa, não uma condenação criminal.",
    fonte: {
      rotulo: "Lei nº 12.846/2013 (Lei Anticorrupção), arts. 22 e 23",
      url: L12846_URL,
    },
    sinonimos: [
      "ceis",
      "cnep",
      "ceaf",
      "cgu",
      "cadastro da cgu",
      "cadastros da cgu",
      "controladoria geral da uniao",
    ],
  },
  {
    id: "ministerio-publico",
    termo: "Ministério Público",
    oficial: "Ministério Público",
    resumo: "Órgão que defende a lei e pode acusar na Justiça.",
    explicacao:
      "Órgão independente que defende a lei e os interesses da sociedade. É o único que pode acusar alguém de crime na Justiça (ação penal pública) e também pode abrir investigações civis e processos para proteger o patrimônio público e o meio ambiente. Não faz parte de nenhum dos três Poderes.",
    fonte: cf("arts. 127 e 129"),
    sinonimos: [
      "ministerio publico",
      "mp federal",
      "mpf",
      "promotor",
      "promotoria",
      "procurador",
    ],
  },
  {
    id: "licitacao",
    termo: "Licitação",
    oficial: "Licitação",
    resumo: "Disputa pública para o governo escolher de quem comprar.",
    explicacao:
      "Disputa pública que o governo faz antes de comprar ou contratar, para escolher a proposta mais vantajosa e dar a todos a mesma chance. As compras são publicadas no Portal Nacional de Contratações Públicas (PNCP).",
    fonte: {
      rotulo: "Lei nº 14.133/2021 (Lei de Licitações), arts. 11 e 174",
      url: L14133_URL,
    },
    sinonimos: ["licitacao", "licitacoes", "pregao", "pncp"],
  },
  {
    id: "dispensa-licitacao",
    termo: "Compra sem licitação",
    oficial: "Dispensa ou inexigibilidade de licitação",
    resumo: "Casos em que a lei permite comprar sem disputa.",
    explicacao:
      "Casos em que a lei permite contratar sem licitação. Na dispensa, a disputa seria possível, mas a lei a dispensa (compras de valor baixo, emergências). Na inexigibilidade, não há como disputar (só um fornecedor, um artista exclusivo). Mesmo assim o contrato precisa ser publicado.",
    fonte: { rotulo: "Lei nº 14.133/2021, arts. 74 e 75", url: L14133_URL },
    sinonimos: [
      "dispensa",
      "dispensa de licitacao",
      "inexigibilidade",
      "sem licitacao",
    ],
  },

  // ---------- Partidos e eleições ----------
  {
    id: "fundo-partidario",
    termo: "Fundo Partidário",
    oficial: "Fundo Especial de Assistência Financeira aos Partidos Políticos",
    resumo: "Dinheiro público pago todo mês aos partidos.",
    explicacao:
      "Dinheiro público (e multas eleitorais) que o TSE divide todo mês entre os partidos, a maior parte de acordo com os votos que cada um teve na última eleição para a Câmara dos Deputados. Serve para manter o partido funcionando.",
    exemplo: { rotulo: "Dinheiro dos partidos", href: "/partidos" },
    fonte: {
      rotulo: "Lei nº 9.096/1995 (Lei dos Partidos), arts. 38 e 41-A",
      url: L9096_URL,
    },
    sinonimos: [
      "fundo partidario",
      "fundo especial de assistencia financeira aos partidos politicos",
    ],
  },
  {
    id: "fundo-eleitoral",
    termo: "Fundo eleitoral",
    oficial: "Fundo Especial de Financiamento de Campanha (FEFC)",
    resumo: "Dinheiro público para as campanhas, só em ano de eleição.",
    explicacao:
      "Dinheiro público repassado aos partidos em ano de eleição, para pagar as campanhas. O valor é definido no orçamento, e a divisão entre os partidos segue, em maior parte, o número de deputados e senadores de cada um e os votos para a Câmara.",
    exemplo: { rotulo: "Dinheiro dos partidos", href: "/partidos" },
    fonte: {
      rotulo: "Lei nº 9.504/1997 (Lei das Eleições), arts. 16-C e 16-D",
      url: L9504_URL,
    },
    sinonimos: [
      "fundo eleitoral",
      "fefc",
      "fundao",
      "fundo especial de financiamento de campanha",
    ],
  },
  {
    id: "federacao",
    termo: "Federação de partidos",
    oficial: "Federação partidária",
    resumo: "Partidos que se unem por pelo menos 4 anos.",
    explicacao:
      "União de dois ou mais partidos, que passam a atuar como se fossem um só por pelo menos 4 anos, nas eleições e no trabalho no Congresso. Diferente da coligação, que só valia na eleição.",
    exemplo: { rotulo: "Partidos", href: "/partidos" },
    fonte: {
      rotulo: "Lei nº 9.096/1995 (Lei dos Partidos), art. 11-A",
      url: L9096_URL,
    },
    sinonimos: ["federacao", "federacoes", "federacao partidaria"],
  },
  {
    id: "declaracao-de-bens",
    termo: "Bens declarados",
    oficial: "Declaração de bens do candidato",
    resumo: "Lista do que o candidato diz ter, entregue ao TSE.",
    explicacao:
      "Lista de bens (imóveis, carros, dinheiro aplicado...) que todo candidato entrega à Justiça Eleitoral no pedido de registro. Os bens e os valores são informados pelo próprio candidato.",
    fonte: {
      rotulo: "Lei nº 9.504/1997 (Lei das Eleições), art. 11, § 1º, IV",
      url: L9504_URL,
    },
    sinonimos: ["bens", "bens declarados", "declaracao de bens", "patrimonio"],
  },
  {
    id: "prestacao-de-contas",
    termo: "Contas de campanha",
    oficial: "Prestação de contas eleitoral",
    resumo: "Quanto a campanha recebeu e gastou, informado ao TSE.",
    explicacao:
      "Relatório que cada candidato e partido entrega à Justiça Eleitoral com todo o dinheiro que a campanha recebeu (de quem) e gastou (com quem). A Justiça Eleitoral analisa e pode aprovar, aprovar com ressalvas ou desaprovar as contas.",
    fonte: {
      rotulo: "Lei nº 9.504/1997 (Lei das Eleições), art. 28",
      url: L9504_URL,
    },
    sinonimos: [
      "prestacao de contas",
      "contas de campanha",
      "doacoes de campanha",
      "gastos de campanha",
    ],
  },
];

/** Minúsculas, sem acento e sem pontuação (mesma regra do Argos). */
export function normalizarTermo(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const POR_ID = new Map(TERMOS.map((t) => [t.id, t]));

export function termoPorId(id: string): Termo | undefined {
  return POR_ID.get(id);
}

/** Ordem do índice: pelo nome do dia a dia, sem acento. */
export function termosEmOrdem(): Termo[] {
  return [...TERMOS].sort((a, b) =>
    normalizarTermo(a.termo).localeCompare(normalizarTermo(b.termo), "pt-BR"),
  );
}

/** Letra do índice A–Z (sem acento). */
export function letraDoTermo(t: Termo): string {
  return normalizarTermo(t.termo).charAt(0).toUpperCase();
}

function textoDeBusca(t: Termo): string {
  return normalizarTermo(
    [t.termo, t.oficial, t.resumo, ...(t.sinonimos ?? [])].join(" "),
  );
}

/** Busca do índice: todas as palavras digitadas precisam aparecer (sem acento, sem maiúscula). */
export function buscarTermos(
  consulta: string,
  termos: Termo[] = termosEmOrdem(),
): Termo[] {
  const palavras = normalizarTermo(consulta).split(" ").filter(Boolean);
  if (!palavras.length) return termos;
  return termos.filter((t) => {
    const alvo = ` ${textoDeBusca(t)} `;
    return palavras.every((p) => alvo.includes(` ${p}`));
  });
}

/**
 * O termo de que se fala num trecho de frase ("a pec", "cota parlamentar", "quorum"): compara com
 * o nome, o nome oficial e os sinônimos; a forma mais longa encontrada vence. Devolve também a
 * forma achada (normalizada), para quem quer saber o que sobrou da frase.
 */
export function acharTermoComForma(
  trecho: string,
): { termo: Termo; forma: string } | undefined {
  const alvo = ` ${normalizarTermo(trecho)} `;
  let melhor: { termo: Termo; forma: string } | undefined;
  for (const t of TERMOS) {
    const formas = [t.termo, t.oficial, ...(t.sinonimos ?? [])].map(
      normalizarTermo,
    );
    for (const f of formas) {
      if (
        f &&
        alvo.includes(` ${f} `) &&
        (!melhor || f.length > melhor.forma.length)
      )
        melhor = { termo: t, forma: f };
    }
  }
  return melhor;
}

export function acharTermo(trecho: string): Termo | undefined {
  return acharTermoComForma(trecho)?.termo;
}
