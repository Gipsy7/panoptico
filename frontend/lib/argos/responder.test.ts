import { describe, expect, it } from "vitest";

import type { Gastos, Presenca, Projetos, Representantes, RespostaBusca, ResultadoBusca } from "@/lib/api";

import {
  erroDaApi,
  escolherCandidatos,
  idFederal,
  mensagemEscolha,
  respostaEmendas,
  respostaGastos,
  respostaPresenca,
  respostaProjetos,
  respostaRepresentantes,
  respostaSite,
} from "./responder";

const FULANO = { nome: "Fulano", caminho: "/parlamentar/10" };

function gastos(extra: Partial<Gastos> = {}): Gastos {
  return {
    ano: 2026,
    anos_disponiveis: [2026],
    ultimo_mes: 10,
    total: 123456.78,
    media_casa: 100000,
    por_categoria: [],
    por_mes: [],
    maiores_despesas: [],
    fonte_nome: "Dados Abertos da Câmara dos Deputados",
    fonte_url: "https://dadosabertos.camara.leg.br",
    atualizado_em: "2026-10-29T06:00:00Z",
    ...extra,
  };
}

function presenca(extra: Partial<Presenca> = {}): Presenca {
  return {
    ano: 2026,
    anos_disponiveis: [2026],
    periodo_inicio: "2026-01-01",
    total_votacoes: 59,
    votou: 31,
    presente_sem_voto: 0,
    justificada: 4,
    nao_compareceu: 24,
    justificativas: [],
    percentual: 52.5,
    media_casa_percentual: 80.25,
    ausencia_detalhada: true,
    fonte_nome: "Dados Abertos da Câmara dos Deputados",
    fonte_url: "https://dadosabertos.camara.leg.br",
    atualizado_em: "2026-10-29T06:00:00Z",
    ...extra,
  };
}

function item(nome: string, caminho: string): ResultadoBusca {
  return { nome, nome_completo: null, cargo: "Deputado federal", partido: "XX", lugar: "SC", caminho };
}

function busca(parcial: Partial<RespostaBusca>): RespostaBusca {
  return { itens: [], partidos: [], pessoas: [], eleitos_2026: [], ...parcial };
}

describe("respostaGastos", () => {
  it("traz o valor, a média da Casa, a fonte e a data", () => {
    const m = respostaGastos(FULANO, "camara", gastos());
    expect(m.texto).toContain("Fulano usou");
    expect(m.texto).toContain("2026");
    expect(m.texto).toContain("123.456,78");
    expect(m.texto).toContain("de janeiro a out");
    expect(m.detalhes?.join(" ")).toContain("Média da Câmara: ");
    expect(m.detalhes?.join(" ")).toContain("100.000,00");
    expect(m.fonte).toMatchObject({ nome: "Dados Abertos da Câmara dos Deputados", atualizadoEm: "2026-10-29T06:00:00Z" });
    expect(m.links[0].href).toBe("/parlamentar/10#gastos");
  });

  it("zero é dito como ausência de reembolso, não como valor", () => {
    const m = respostaGastos(FULANO, "senado", gastos({ total: 0, ultimo_mes: 12 }));
    expect(m.texto).toContain("não tem reembolso");
    expect(m.texto).not.toContain("R$");
    expect(m.detalhes?.join(" ")).toContain("Média do Senado");
  });

  it("sem a Casa conhecida, fala em 'Média da Casa'", () => {
    expect(respostaGastos(FULANO, null, gastos()).detalhes?.[0]).toMatch(/^Média da Casa:/);
  });
});

describe("respostaPresenca", () => {
  it("diz 'votou em X de Y', o percentual e a média", () => {
    const m = respostaPresenca(FULANO, "camara", presenca());
    expect(m.texto).toContain("votou em 31 de 59");
    expect(m.texto).toContain("52,5%");
    expect(m.detalhes?.[0]).toBe("Média por parlamentar da Câmara: 80,3%.");
    expect(m.detalhes).toContain("Ausências justificadas: 4.");
    expect(m.fonte?.url).toBeTruthy();
  });

  it("inclui 'presente, sem registrar voto' quando houver", () => {
    const m = respostaPresenca(FULANO, "senado", presenca({ presente_sem_voto: 22 }));
    expect(m.detalhes).toContain("Presente, sem registrar voto: 22.");
    expect(respostaPresenca(FULANO, "senado", presenca()).detalhes?.join(" ")).not.toContain("sem registrar");
  });

  it("sem votações no período", () => {
    const m = respostaPresenca(FULANO, "camara", presenca({ total_votacoes: 0, votou: 0, percentual: null }));
    expect(m.texto).toContain("Não há votação nominal");
    expect(m.fonte).toBeDefined();
  });

  it("média ausente vira 'sem dado'", () => {
    const m = respostaPresenca(FULANO, "senado", presenca({ media_casa_percentual: null, ausencia_detalhada: false }));
    expect(m.detalhes).toEqual(["Média por parlamentar do Senado: sem dado."]);
  });
});

describe("respostaProjetos", () => {
  const pj: Projetos = {
    desde: "2023-02-01",
    primeiro_autor: 1,
    coautor: 12,
    viraram_norma: 0,
    media_casa_primeiro_autor: 22.46,
    por_tipo: [],
    recentes: [],
    viraram_norma_lista: [],
    fonte_nome: "Dados Abertos da Câmara dos Deputados",
    fonte_url: "https://dadosabertos.camara.leg.br",
    atualizado_em: "2026-10-29T06:00:00Z",
  };

  it("usa singular, plural e a média da Casa", () => {
    const m = respostaProjetos(FULANO, "camara", pj);
    expect(m.texto).toContain("1 projeto como autor principal");
    expect(m.texto).toContain("12 projetos como coautor");
    expect(m.texto).toContain("fevereiro de 2023");
    expect(m.detalhes?.[0]).toBe("Média por parlamentar da Câmara (autor principal): 22,5.");
    expect(m.fonte?.atualizadoEm).toBeTruthy();
  });
});

describe("respostaEmendas", () => {
  it("manda para a seção do perfil e avisa que não há média", () => {
    const m = respostaEmendas(FULANO);
    expect(m.links[0].href).toBe("/parlamentar/10#destino-emendas");
    expect(m.detalhes?.join(" ")).toContain("média da Casa");
  });
});

describe("respostaRepresentantes", () => {
  const parl = (id: number, nome: string, casa: "camara" | "senado") => ({
    id,
    casa,
    nome_parlamentar: nome,
    partido: "XX",
    uf: "SC",
    foto_url: null,
  });
  const r: Representantes = {
    localizacao: { cep: "88340-000", uf: "SC", estado: "Santa Catarina", municipio: "Camboriú", codigo_ibge: "4203204" },
    deputados: Array.from({ length: 16 }, (_, i) => parl(i + 1, `Dep ${i + 1}`, "camara")),
    senadores: [parl(100, "Sen A", "senado"), parl(101, "Sen B", "senado"), parl(102, "Sen C", "senado")],
    atualizado_em: "2026-10-29T06:00:00Z",
  };

  it("lista senadores, parte dos deputados e os links da cidade", () => {
    const m = respostaRepresentantes("88340-000", r);
    expect(m.texto).toContain("Camboriú-SC");
    expect(m.texto).toContain("3 senadores e 16 deputados federais");
    const hrefs = m.links.map((l) => l.href);
    expect(hrefs).toContain("/parlamentar/100");
    expect(hrefs).toContain("/parlamentar/8");
    expect(hrefs).not.toContain("/parlamentar/9");
    expect(hrefs).toContain("/representantes?cep=88340-000");
    expect(hrefs).toContain("/cidade/4203204");
    expect(m.detalhes?.[0]).toContain("mostro 8");
    expect(m.fonte?.atualizadoEm).toBe("2026-10-29T06:00:00Z");
  });

  it("sem município, fala do estado", () => {
    const m = respostaRepresentantes("88340-000", { ...r, localizacao: { ...r.localizacao, municipio: null, codigo_ibge: null } });
    expect(m.texto).toContain("é de Santa Catarina");
  });
});

describe("escolherCandidatos", () => {
  it("nenhum, um e vários", () => {
    expect(escolherCandidatos(busca({}))).toEqual({ tipo: "nenhum" });
    expect(escolherCandidatos(busca({ itens: [item("A", "/parlamentar/1")] }))).toMatchObject({ tipo: "um" });
    const varios = escolherCandidatos(
      busca({ itens: Array.from({ length: 7 }, (_, i) => item(`P${i}`, `/parlamentar/${i}`)) }),
    );
    expect(varios).toMatchObject({ tipo: "varios", total: 7 });
    if (varios.tipo === "varios") expect(varios.itens).toHaveLength(5);
  });

  it("nome exato entre vários homônimos responde direto", () => {
    const b = busca({
      itens: [item("Alexandre Guimarães", "/parlamentar/1"), item("Alexandre Guimaraes Filho", "/parlamentar/2"), item("Alexandre Leite", "/parlamentar/3")],
    });
    expect(escolherCandidatos(b, "alexandre guimaraes")).toMatchObject({ tipo: "um", item: { caminho: "/parlamentar/1" } });
    expect(escolherCandidatos(b, "alexandre")).toMatchObject({ tipo: "varios" });
    const dois = busca({ itens: [item("Ana", "/parlamentar/1"), item("Ana", "/parlamentar/2")] });
    expect(escolherCandidatos(dois, "ana")).toMatchObject({ tipo: "varios" });
  });

  it("quem está no cargo vem antes de eleições passadas", () => {
    const c = escolherCandidatos(
      busca({ itens: [item("Atual", "/parlamentar/1")], pessoas: [item("Antigo", "/eleito/2"), item("Outro", "/eleito/3")] }),
    );
    expect(c).toMatchObject({ tipo: "um", item: { nome: "Atual" } });
  });
});

describe("mensagemEscolha", () => {
  it("cria um botão por pessoa, já com a ação", () => {
    const m = mensagemEscolha([item("A", "/parlamentar/1"), item("B", "/vereador/2")], 2, "gastos");
    expect(m.botoes).toHaveLength(2);
    expect(m.botoes[0].acao).toEqual({ assunto: "gastos", pessoa: { nome: "A", caminho: "/parlamentar/1" } });
  });
});

describe("idFederal", () => {
  it("só reconhece /parlamentar/{id}", () => {
    expect(idFederal("/parlamentar/123")).toBe("123");
    expect(idFederal("/vereador/123")).toBeNull();
    expect(idFederal("/deputado-estadual/9")).toBeNull();
    expect(idFederal("/eleito/9")).toBeNull();
  });
});

describe("erros e dúvidas do site", () => {
  it("404 e 422 mostram a mensagem da API; o resto, o aviso geral", () => {
    expect(erroDaApi(404, "CEP não encontrado.").texto).toBe("CEP não encontrado.");
    expect(erroDaApi(500, "x").texto).toContain("Não consegui buscar");
    expect(erroDaApi(503, "x").erro).toBe(true);
  });

  it("usa o texto de /perguntas", () => {
    const m = respostaSite("media-casa");
    expect(m.texto).toContain("média entre os parlamentares em exercício");
    expect(m.links[0].href).toBe("/perguntas#media-casa");
  });

  it("id desconhecido cai na apresentação do site", () => {
    expect(respostaSite("sobre").links.map((l) => l.href)).toContain("/o-panoptico");
  });
});
