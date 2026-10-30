/**
 * Corpus de frases realistas (celular, WhatsApp: minúsculas, sem acento, erros, gírias leves) com o
 * assunto e as entidades que o Argos tem de entender. Cada linha é [frase, esperado]; o esperado é
 * conferido com `toMatchObject` (só os campos listados). A data de "agora" é fixa: 30/10/2026.
 */
import { describe, expect, it } from "vitest";

import { interpretar } from "./interpretar";
import type { Interpretacao } from "./tipos";

const AGORA = new Date(2026, 9, 30);

type Caso = [string, Partial<Interpretacao>];

const GRUPOS: Record<string, Caso[]> = {
  "representantes (CEP, estado, cidade)": [
    ["88340-000", { assunto: "representantes", cep: "88340-000" }],
    ["meu cep é 01310-100", { assunto: "representantes", cep: "01310-100" }],
    ["01310100", { assunto: "representantes", cep: "01310-100" }],
    ["quem me representa", { assunto: "representantes" }],
    ["quem me representa?", { assunto: "representantes" }],
    ["quem são meus deputados", { assunto: "representantes" }],
    ["quem e meu deputado", { assunto: "representantes" }],
    ["meus senadores", { assunto: "representantes" }],
    ["quem sao meus representantes", { assunto: "representantes" }],
    ["moro em gaspar", { assunto: "representantes", nome: "gaspar" }],
    ["moro em Gaspar SC", { assunto: "representantes", nome: "gaspar", uf: "SC" }],
    ["quem representa sc", { assunto: "representantes", uf: "SC" }],
    ["quem representa santa catarina", { assunto: "representantes", uf: "SC" }],
  ],
  "lista de parlamentares": [
    ["deputados de SC", { assunto: "lista", uf: "SC", casa: "camara" }],
    ["deputados de sc", { assunto: "lista", uf: "SC", casa: "camara" }],
    ["senadores do paraná", { assunto: "lista", uf: "PR", casa: "senado" }],
    ["senadores do parana", { assunto: "lista", uf: "PR", casa: "senado" }],
    ["lista de deputados", { assunto: "lista", casa: "camara" }],
    ["todos os senadores", { assunto: "lista", casa: "senado" }],
    ["deputados do PT", { assunto: "lista", partido: "PT", casa: "camara" }],
    ["quantos deputados tem santa catarina", { assunto: "lista", uf: "SC" }],
    ["deputados de minas gerais", { assunto: "lista", uf: "MG" }],
    ["senadores do rio grande do sul", { assunto: "lista", uf: "RS", casa: "senado" }],
    ["senadores do mato grosso do sul", { assunto: "lista", uf: "MS" }],
    ["bancada de SP", { assunto: "lista", uf: "SP" }],
    ["deputados do estado do pará", { assunto: "lista", uf: "PA" }],
    ["lista de parlamentares", { assunto: "lista" }],
    ["deputados federais do rio de janeiro", { assunto: "lista", uf: "RJ" }],
  ],
  "gastos de uma pessoa": [
    ["quanto o fulano gastou", { assunto: "gastos", nome: "fulano" }],
    ["quanto o Fulano gastou?", { assunto: "gastos", nome: "fulano" }],
    ["gastos da Tabata Amaral", { assunto: "gastos", nome: "tabata amaral" }],
    ["gasto do gabinete do Eduardo Gomes", { assunto: "gastos", nome: "eduardo gomes" }],
    ["cota do deputado fulano", { assunto: "gastos", nome: "fulano" }],
    ["reembolso do senador Fulano", { assunto: "gastos", nome: "fulano" }],
    ["quanto custa o fulano", { assunto: "gastos", nome: "fulano" }],
    ["dinheiro que o fulano gastou", { assunto: "gastos", nome: "fulano" }],
    ["quanto gastou em 2025", { assunto: "gastos", ano: 2025 }],
    ["gastos em março do Fulano", { assunto: "gastos", mes: 3, nome: "fulano" }],
    ["gastos em março do Marco Feliciano", { assunto: "gastos", mes: 3, nome: "marco feliciano" }],
    ["quanto ele gastou esse mês", { assunto: "gastos", mes: 10, ano: 2026, relativo: true }],
    ["quanto o deputado Fulano gastou este ano", { assunto: "gastos", ano: 2026, nome: "fulano" }],
    ["quanto gastou ano passado", { assunto: "gastos", ano: 2025 }],
    ["quanto gastou o fulano em outubro", { assunto: "gastos", mes: 10, nome: "fulano" }],
    ["quanto gastou no mês passado", { assunto: "gastos", mes: 9, ano: 2026 }],
    ["quanto gastou?", { assunto: "gastos", nome: undefined }],
    ["gastos", { assunto: "gastos" }],
    ["dinheiro que Gaspar recebeu", { assunto: "gastos", nome: "gaspar" }],
  ],
  "gasto do governo (o que o site tem e o que não tem)": [
    ["Quanto o governo gastou esse mês", { assunto: "governo_gasto", instituicao: "federal", mes: 10, ano: 2026 }],
    ["quanto o governo gastou", { assunto: "governo_gasto", instituicao: "federal" }],
    ["quanto o governo federal gastou", { assunto: "governo_gasto", instituicao: "federal" }],
    ["quanto o governo gastou em 2025", { assunto: "governo_gasto", ano: 2025 }],
    ["dinheiro do governo", { assunto: "governo_gasto", instituicao: "federal" }],
    ["quanto o presidente gastou", { assunto: "governo_gasto", instituicao: "federal" }],
    ["quanto a união gastou", { assunto: "governo_gasto", instituicao: "federal" }],
    ["quanto a prefeitura gastou", { assunto: "governo_gasto", instituicao: "municipal" }],
    ["quanto a prefeitura de gaspar gastou", { assunto: "governo_gasto", instituicao: "municipal", nome: "gaspar" }],
    ["quanto o governador gastou", { assunto: "governo_gasto", instituicao: "estadual" }],
    ["gastos do governo de SC", { assunto: "governo_gasto", uf: "SC" }],
  ],
  "presença": [
    ["e a presença dele?", { assunto: "presenca", nome: undefined }],
    ["e a presenca dela", { assunto: "presenca", nome: undefined }],
    ["quantas votações o fulano faltou", { assunto: "presenca", nome: "fulano" }],
    ["o fulano falta muito?", { assunto: "presenca", nome: "fulano" }],
    ["presença da Maria do Rosário", { assunto: "presenca", nome: "maria do rosario" }],
    ["compareceu às votações?", { assunto: "presenca" }],
    ["votou quantas vezes em 2025", { assunto: "presenca", ano: 2025 }],
    ["o fulano é ausente?", { assunto: "presenca", nome: "fulano" }],
  ],
  "projetos de uma pessoa": [
    ["projetos de lei do Fulano", { assunto: "projetos", nome: "fulano" }],
    ["o que ele propôs?", { assunto: "projetos", nome: undefined }],
    ["quantos projetos a Tabata apresentou", { assunto: "projetos", nome: "tabata" }],
    ["pl do fulano", { assunto: "projetos", nome: "fulano" }],
    ["leis que o fulano propôs", { assunto: "projetos", nome: "fulano" }],
    ["emendas do fulano", { assunto: "emendas", nome: "fulano" }],
    ["verba que o fulano mandou", { assunto: "emendas", nome: "fulano" }],
  ],
  "busca de projetos por tema e votações": [
    ["projetos sobre saúde", { assunto: "projetos_busca", tema: "saude" }],
    ["lei sobre educação em 2025", { assunto: "projetos_busca", tema: "educacao", ano: 2025 }],
    ["projetos de lei sobre maconha", { assunto: "projetos_busca", tema: "maconha" }],
    ["quais projetos falam de aborto", { assunto: "projetos_busca", tema: "aborto" }],
    ["projeto sobre armas", { assunto: "projetos_busca", tema: "armas" }],
    ["o que está sendo votado", { assunto: "pagina", secao: "projetos" }],
    ["votações recentes", { assunto: "pagina", secao: "projetos" }],
    ["pauta da semana", { assunto: "pagina", secao: "projetos" }],
    ["o que foi votado ontem", { assunto: "pagina", secao: "projetos" }],
  ],
  "comparar": [
    ["comparar deputados", { assunto: "comparar", nomes: [] }],
    ["comparar deputados de SC", { assunto: "comparar", uf: "SC" }],
    ["quero comparar parlamentares", { assunto: "comparar" }],
    ["compare Fulano e Beltrano", { assunto: "comparar", nomes: ["fulano", "beltrano"] }],
    ["Fulano x Beltrano", { assunto: "comparar", nomes: ["fulano", "beltrano"] }],
    ["tabata amaral vs nikolas ferreira", { assunto: "comparar", nomes: ["tabata amaral", "nikolas ferreira"] }],
    ["comparar a Tabata com o Nikolas", { assunto: "comparar", nomes: ["tabata", "nikolas"] }],
    ["comparação entre Lula e Bolsonaro", { assunto: "comparar", nomes: ["lula", "bolsonaro"] }],
    ["gastos do Fulano e do Beltrano", { assunto: "comparar", nomes: ["fulano", "beltrano"] }],
    ["diferença entre Fulano e Beltrano", { assunto: "comparar", nomes: ["fulano", "beltrano"] }],
    ["qual a diferença entre dois deputados", { assunto: "comparar", nomes: [] }],
    ["lado a lado Fulano e Beltrano", { assunto: "comparar", nomes: ["fulano", "beltrano"] }],
    ["comparar Fulano, Beltrano e Ciclano", { assunto: "comparar", nomes: ["fulano", "beltrano", "ciclano"] }],
    ["quanto o joão e o pedro gastaram", { assunto: "comparar", nomes: ["joao", "pedro"] }],
  ],
  "impostos e repasses (dinheiro federal)": [
    ["impostos e repasses", { assunto: "dinheiro_federal" }],
    ["quanto a união repassou para SC", { assunto: "dinheiro_federal", uf: "SC" }],
    ["dinheiro federal de santa catarina", { assunto: "dinheiro_federal", uf: "SC" }],
    ["repasses para Gaspar", { assunto: "dinheiro_federal", nome: "gaspar" }],
    ["quanto de imposto o brasil arrecada", { assunto: "dinheiro_federal" }],
    ["arrecadação em 2024", { assunto: "dinheiro_federal", ano: 2024 }],
    ["fpm de gaspar", { assunto: "dinheiro_federal", nome: "gaspar" }],
    ["transferências para o Paraná", { assunto: "dinheiro_federal", uf: "PR" }],
    ["verba federal para minha cidade", { assunto: "dinheiro_federal" }],
    ["quanto o governo mandou pra SC", { assunto: "dinheiro_federal", uf: "SC" }],
    ["imposto", { assunto: "dinheiro_federal" }],
    ["repasses federais para Blumenau SC", { assunto: "dinheiro_federal", uf: "SC", nome: "blumenau" }],
  ],
  "executivo (presidente, governador, prefeito)": [
    ["quem é o presidente", { assunto: "executivo", cargo: "presidente" }],
    ["quem é o prefeito de Gaspar", { assunto: "executivo", cargo: "prefeito", nome: "gaspar" }],
    ["quem é o governador de SC", { assunto: "executivo", cargo: "governador", uf: "SC" }],
    ["quem é o governador do paraná", { assunto: "executivo", cargo: "governador", uf: "PR" }],
    ["quem governa o brasil", { assunto: "executivo" }],
    ["presidente Lula", { assunto: "executivo", nome: "lula" }],
    ["prefeito", { assunto: "executivo", cargo: "prefeito" }],
    ["quem é a governadora", { assunto: "executivo", cargo: "governador" }],
  ],
  "partidos": [
    ["dinheiro dos partidos", { assunto: "partidos" }],
    ["contas do PT", { assunto: "partidos", partido: "PT" }],
    ["fundo partidário", { assunto: "partidos" }],
    ["quanto o PL recebeu do fundo eleitoral", { assunto: "partidos", partido: "PL" }],
    ["gastos do partido novo", { assunto: "partidos", partido: "NOVO" }],
    ["partidos", { assunto: "partidos" }],
    ["partido dos trabalhadores", { assunto: "partidos", partido: "PT" }],
    ["MDB", { assunto: "partidos", partido: "MDB" }],
    ["quanto o psol arrecadou", { assunto: "partidos", partido: "PSOL" }],
    ["quanto o PT gastou", { assunto: "partidos", partido: "PT" }],
    ["partido união brasil", { assunto: "partidos", partido: "UNIÃO" }],
  ],
  "cidades": [
    ["vereadores de Gaspar", { assunto: "cidade", nome: "gaspar" }],
    ["câmara municipal de blumenau", { assunto: "cidade", nome: "blumenau" }],
    ["contas da prefeitura de Gaspar SC", { assunto: "cidade", nome: "gaspar", uf: "SC" }],
    ["fornecedores da prefeitura de São Paulo", { assunto: "cidade", uf: "SP" }],
    ["licitações em Gaspar", { assunto: "cidade", nome: "gaspar" }],
    ["vereadores", { assunto: "cidade" }],
  ],
  "eleições": [
    ["segundo turno", { assunto: "eleicao" }],
    ["quem ganhou a eleição", { assunto: "eleicao" }],
    ["candidatos de SC", { assunto: "eleicao", uf: "SC" }],
    ["quando é a eleição", { assunto: "eleicao" }],
    ["quem foi eleito em sp", { assunto: "eleicao", uf: "SP" }],
    ["eleitos 2026", { assunto: "eleicao", ano: 2026 }],
  ],
  "salário": [
    ["quanto ganha um deputado", { assunto: "salario" }],
    ["salário do Fulano", { assunto: "salario", nome: "fulano" }],
    ["quanto o senador Fulano recebe", { assunto: "salario", nome: "fulano" }],
    ["remuneração do deputado", { assunto: "salario" }],
  ],
  "seções do perfil": [
    ["como votou o Fulano", { assunto: "secao", secao: "votos", nome: "fulano" }],
    ["como o fulano votou", { assunto: "secao", secao: "votos", nome: "fulano" }],
    ["como a tabata votou ontem", { assunto: "secao", secao: "votos", nome: "tabata" }],
    ["bens do Fulano", { assunto: "secao", secao: "candidatura", nome: "fulano" }],
    ["patrimônio do deputado fulano", { assunto: "secao", secao: "candidatura", nome: "fulano" }],
    ["telefone do gabinete do fulano", { assunto: "secao", secao: "contato", nome: "fulano" }],
    ["como falo com a Tabata", { assunto: "secao", secao: "contato", nome: "tabata" }],
    ["email do deputado fulano", { assunto: "secao", secao: "contato", nome: "fulano" }],
    ["comissões do fulano", { assunto: "secao", secao: "comissoes", nome: "fulano" }],
    ["o fulano foi condenado?", { assunto: "secao", secao: "sancoes", nome: "fulano" }],
  ],
  "páginas do site": [
    ["como apoiar o projeto", { assunto: "pagina", secao: "apoie" }],
    ["quero doar", { assunto: "pagina", secao: "apoie" }],
    ["tem pix?", { assunto: "pagina", secao: "apoie" }],
    ["acessibilidade", { assunto: "pagina", secao: "acessibilidade" }],
    ["o site tem libras", { assunto: "pagina", secao: "acessibilidade" }],
    ["o site caiu", { assunto: "pagina", secao: "status" }],
    ["quais cidades vocês cobrem", { assunto: "pagina", secao: "cobertura" }],
    ["metodologia", { assunto: "pagina", secao: "fontes" }],
    ["código aberto", { assunto: "pagina", secao: "codigo" }],
    ["apoiadores", { assunto: "pagina", secao: "apoiadores" }],
  ],
  "dúvidas sobre o site": [
    ["o que é a média da casa", { assunto: "site", perguntaId: "media-casa" }],
    ["de onde vêm os dados?", { assunto: "site", perguntaId: "fonte" }],
    ["o site guarda meu cep", { assunto: "site", perguntaId: "cep" }],
    ["vocês dão nota?", { assunto: "site", perguntaId: "nota" }],
    ["quem paga isso", { assunto: "site", perguntaId: "quem-paga" }],
    ["posso baixar os dados", { assunto: "site", perguntaId: "dados" }],
    ["como funciona", { assunto: "site", perguntaId: "sobre" }],
    ["os dados são atualizados todo dia?", { assunto: "site", perguntaId: "frequencia" }],
    ["achei um número errado", { assunto: "site", perguntaId: "erro" }],
    ["a câmara da minha cidade não aparece", { assunto: "site", perguntaId: "cobertura" }],
    ["o que é o panóptico", { assunto: "site", perguntaId: "sobre" }],
  ],
  "opinião (o Argos não opina)": [
    ["em quem votar", { assunto: "opiniao" }],
    ["votar em quem?", { assunto: "opiniao" }],
    ["o fulano é corrupto", { assunto: "opiniao" }],
    ["qual o melhor deputado", { assunto: "opiniao" }],
    ["esse deputado presta?", { assunto: "opiniao" }],
    ["vale a pena votar no fulano", { assunto: "opiniao" }],
    ["o fulano trabalha bem?", { assunto: "opiniao" }],
    ["o governo é bom", { assunto: "opiniao" }],
    ["quem é o pior senador", { assunto: "opiniao" }],
  ],
  "ranking (o site não faz; aponta a lista ordenável)": [
    ["quem gastou mais", { assunto: "ranking", ordem: { criterio: "gastos", desc: true } }],
    ["quem gastou menos", { assunto: "ranking", ordem: { criterio: "gastos", desc: false } }],
    ["quem faltou mais", { assunto: "ranking", ordem: { criterio: "presenca", desc: false } }],
    ["quem faltou menos", { assunto: "ranking", ordem: { criterio: "presenca", desc: true } }],
    ["qual deputado propôs mais projetos", { assunto: "ranking", ordem: { criterio: "projetos", desc: true } }],
    ["qual o maior gasto", { assunto: "ranking", ordem: { criterio: "gastos", desc: true } }],
    ["gastos dos deputados de SC", { assunto: "ranking", uf: "SC", casa: "camara", ordem: { criterio: "gastos", desc: true } }],
    ["quanto gastam os senadores", { assunto: "ranking", casa: "senado" }],
  ],
  "sobre o Argos (é IA? quem fez? como funciona?)": [
    ["você é uma IA?", { assunto: "sobre_argos" }],
    ["voce e um robo", { assunto: "sobre_argos" }],
    ["vc é o chatgpt?", { assunto: "sobre_argos" }],
    ["isso é inteligência artificial?", { assunto: "sobre_argos" }],
    ["você é humano?", { assunto: "sobre_argos" }],
    ["tem uma pessoa de verdade aí?", { assunto: "sobre_argos" }],
    ["quem te fez", { assunto: "sobre_argos" }],
    ["quem te criou?", { assunto: "sobre_argos" }],
    ["como você funciona", { assunto: "sobre_argos" }],
    ["quem é você", { assunto: "sobre_argos" }],
    ["o que é o argos", { assunto: "sobre_argos" }],
  ],
  "saudação e ajuda": [
    ["oi", { assunto: "saudacao" }],
    ["bom dia", { assunto: "saudacao" }],
    ["ajuda", { assunto: "saudacao" }],
    ["o que você faz", { assunto: "saudacao" }],
    ["olá, tudo bem?", { assunto: "saudacao" }],
    ["opa", { assunto: "saudacao" }],
    ["help", { assunto: "saudacao" }],
    ["o que posso perguntar", { assunto: "saudacao" }],
  ],
  "nomes de pessoas (inclusive palavras comuns) e frases soltas": [
    ["Lula", { assunto: "pessoa", nome: "lula" }],
    ["Bolsonaro", { assunto: "pessoa", nome: "bolsonaro" }],
    ["Tabata Amaral", { assunto: "pessoa", nome: "tabata amaral" }],
    ["Marco Feliciano", { assunto: "pessoa", nome: "marco feliciano" }],
    ["Nikolas Ferreira", { assunto: "pessoa", nome: "nikolas ferreira" }],
    ["dino", { assunto: "pessoa", nome: "dino" }],
    ["Eduardo Gomes", { assunto: "pessoa", nome: "eduardo gomes" }],
    ["Damares de Sales", { assunto: "pessoa", nome: "damares de sales" }],
    ["governo", { assunto: "nenhum" }],
    ["Governo", { assunto: "nenhum" }],
    ["câmara", { assunto: "nenhum" }],
    ["prefeitura", { assunto: "cidade" }],
    ["???", { assunto: "nenhum" }],
    ["oi, Fulano", { assunto: "pessoa", nome: "fulano" }],
    ["a o e", { assunto: "nenhum" }],
  ],
};

for (const [grupo, casos] of Object.entries(GRUPOS)) {
  describe(grupo, () => {
    it.each(casos)("%s", (frase, esperado) => {
      expect(interpretar(frase, AGORA)).toMatchObject(esperado);
    });
  });
}

describe("o corpus", () => {
  it("tem ao menos 150 frases", () => {
    const total = Object.values(GRUPOS).reduce((n, l) => n + l.length, 0);
    expect(total).toBeGreaterThanOrEqual(150);
  });

  it("cobre todos os assuntos do Argos", () => {
    const vistos = new Set(Object.values(GRUPOS).flatMap((l) => l.map(([, e]) => e.assunto)));
    for (const a of [
      "gastos", "presenca", "projetos", "emendas", "representantes", "comparar", "dinheiro_federal", "partidos",
      "lista", "cidade", "eleicao", "salario", "executivo", "projetos_busca", "governo_gasto", "secao", "pagina",
      "pessoa", "ranking", "site", "sobre_argos", "opiniao", "saudacao", "nenhum",
    ]) {
      expect(vistos.has(a as Interpretacao["assunto"]), a).toBe(true);
    }
  });
});

describe("'não entendi' sugere botões ligados ao que foi reconhecido", () => {
  it("governo sozinho sugere impostos e repasses", () => {
    const i = interpretar("governo", AGORA);
    expect(i.sugestoes?.map((b) => b.rotulo)).toContain("Impostos e repasses");
    expect(i.sugestoes).toHaveLength(3);
  });

  it("sem pista, sugere os exemplos", () => {
    expect(interpretar("???", AGORA).sugestoes).toHaveLength(3);
  });
});
