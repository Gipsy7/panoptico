import { describe, expect, it, vi } from "vitest";

import type { Resultado } from "@/lib/api";

import { type ApiArgos, conversar } from "./conversar";
import type { Contexto } from "./tipos";

const ok = <T>(dados: T): Resultado<T> => ({ ok: true, dados });
const falha = (status: number, mensagem: string): Resultado<never> => ({ ok: false, status, mensagem });

const FONTE = { fonte_nome: "Fonte", fonte_url: "https://f.example", atualizado_em: "2026-10-29T06:00:00Z" };

function item(nome: string, caminho: string, cargo = "Deputado federal") {
  return { nome, nome_completo: null, cargo, partido: "XX", lugar: "SC", caminho };
}

export const MUNICIPIOS = [
  { ibge: "4205902", nome: "Gaspar", uf: "SC" },
  { ibge: "4202404", nome: "Blumenau", uf: "SC" },
  { ibge: "3550308", nome: "São Paulo", uf: "SP" },
  { ibge: "3106408", nome: "Bom Jesus do Amparo", uf: "MG" },
  { ibge: "2901809", nome: "Bom Jesus da Lapa", uf: "BA" },
  { ibge: "4301000", nome: "Bom Jesus", uf: "RS" },
  { ibge: "4301001", nome: "Bom Jesus", uf: "SC" },
];

function api(extra: Partial<ApiArgos> = {}): ApiArgos {
  return {
    busca: vi.fn(async () => ok({ itens: [item("Fulano", "/parlamentar/10")], partidos: [], pessoas: [], eleitos_2026: [] })),
    representantes: vi.fn(async () =>
      ok({
        localizacao: { cep: "88340-000", uf: "SC", estado: "Santa Catarina", municipio: "Camboriú", codigo_ibge: "4203204" },
        deputados: [],
        senadores: [],
        atualizado_em: "2026-10-29T06:00:00Z",
      }),
    ),
    parlamentar: vi.fn(async () => ok({ casa: "camara" } as never)),
    gastos: vi.fn(async () => ok({ ano: 2026, ultimo_mes: 10, total: 1000, media_casa: 2000, ...FONTE } as never)),
    presenca: vi.fn(async () =>
      ok({
        ano: 2026, total_votacoes: 59, votou: 31, percentual: 52.5, media_casa_percentual: 80,
        justificada: 0, ausencia_detalhada: false, ...FONTE,
      } as never),
    ),
    municipios: vi.fn(async (uf: string) => ok(MUNICIPIOS.filter((m) => m.uf === uf))),
    projetos: vi.fn(async () =>
      ok({ desde: "2023-02-01", primeiro_autor: 3, coautor: 1, viraram_norma: 0, media_casa_primeiro_autor: 20, ...FONTE } as never),
    ),
    ...extra,
  };
}

const VAZIO: Contexto = {};

describe("conversar", () => {
  it("'quanto o fulano gastou' busca o nome e responde com a média", async () => {
    const a = api();
    const v = await conversar({ frase: "quanto o fulano gastou" }, VAZIO, a);
    expect(a.busca).toHaveBeenCalledWith("fulano");
    expect(a.gastos).toHaveBeenCalledWith("10", undefined);
    expect(v.mensagens[0].texto).toContain("Fulano usou");
    expect(v.mensagens[0].fonte).toBeDefined();
    expect(v.contexto.pessoa).toEqual({ nome: "Fulano", caminho: "/parlamentar/10" });
  });

  it("lembra da pessoa: 'e a presença dele?' não busca de novo", async () => {
    const a = api();
    const primeira = await conversar({ frase: "quanto o fulano gastou" }, VAZIO, a);
    const segunda = await conversar({ frase: "e a presença dele?" }, primeira.contexto, a);
    expect(a.busca).toHaveBeenCalledTimes(1);
    expect(a.presenca).toHaveBeenCalledWith("10", undefined);
    expect(segunda.mensagens[0].texto).toContain("votou em 31 de 59");
    expect(segunda.mensagens[0].detalhes?.[0]).toContain("Média por parlamentar da Câmara: 80%");
  });

  it("sem pessoa lembrada, pede o nome", async () => {
    const a = api();
    const v = await conversar({ frase: "quanto gastou?" }, VAZIO, a);
    expect(v.mensagens[0].texto).toContain("De quem?");
    expect(a.busca).not.toHaveBeenCalled();
  });

  it("CEP chama representantes", async () => {
    const a = api();
    const v = await conversar({ frase: "88340-000" }, VAZIO, a);
    expect(a.representantes).toHaveBeenCalledWith({ cep: "88340-000" });
    expect(v.mensagens[0].texto).toContain("Camboriú-SC");
  });

  it("CEP que a API recusa mostra a mensagem dela", async () => {
    const a = api({ representantes: vi.fn(async () => falha(404, "Não encontramos esse CEP.")) });
    const v = await conversar({ frase: "00000-000" }, VAZIO, a);
    expect(v.mensagens[0].texto).toBe("Não encontramos esse CEP.");
  });

  it("'meus deputados' sem CEP pede o CEP", async () => {
    const v = await conversar({ frase: "quem são meus deputados" }, VAZIO, api());
    expect(v.mensagens[0].texto).toContain("digite o seu CEP");
  });

  it("homônimos viram botões e o clique vai direto ao assunto", async () => {
    const a = api({
      busca: vi.fn(async () =>
        ok({ itens: [item("João Silva", "/parlamentar/1"), item("João Souza", "/parlamentar/2")], partidos: [], pessoas: [], eleitos_2026: [] }),
      ),
    });
    const v = await conversar({ frase: "presença do joão" }, VAZIO, a);
    expect(v.mensagens[0].botoes).toHaveLength(2);
    expect(a.presenca).not.toHaveBeenCalled();
    const clique = await conversar({ frase: "João Souza", acao: v.mensagens[0].botoes[1].acao }, VAZIO, a);
    expect(a.presenca).toHaveBeenCalledWith("2", undefined);
    expect(clique.contexto.pessoa?.nome).toBe("João Souza");
  });

  it("vereador e outros cargos recebem só o link do perfil", async () => {
    const a = api({
      busca: vi.fn(async () => ok({ itens: [item("Ana Vereadora", "/vereador/77", "Vereadora")], partidos: [], pessoas: [], eleitos_2026: [] })),
    });
    const v = await conversar({ frase: "quanto a ana vereadora gastou", }, VAZIO, a);
    expect(v.mensagens[0].links[0].href).toBe("/vereador/77");
    expect(a.gastos).not.toHaveBeenCalled();
  });

  it("só o nome mostra os botões de assunto", async () => {
    const v = await conversar({ frase: "Fulano" }, VAZIO, api());
    expect(v.mensagens[0].botoes.map((b) => b.rotulo)).toEqual(["Gastos", "Presença nas votações", "Projetos de lei", "Emendas", "Salário"]);
    expect(v.mensagens[0].botoes[0].acao?.assunto).toBe("gastos");
  });

  it("emendas mandam para o perfil", async () => {
    const v = await conversar({ frase: "emendas do fulano" }, VAZIO, api());
    expect(v.mensagens[0].links[0].href).toBe("/parlamentar/10#destino-emendas");
  });

  it("nome que não existe", async () => {
    const a = api({ busca: vi.fn(async () => ok({ itens: [], partidos: [], pessoas: [], eleitos_2026: [] })) });
    const v = await conversar({ frase: "gastos do xyzzy" }, VAZIO, a);
    expect(v.mensagens[0].texto).toBe("Não achei ninguém com esse nome.");
  });

  it("opinião, saudação, dúvida e frase sem sentido não chamam a API", async () => {
    const a = api();
    const frases = ["em quem votar?", "oi", "o que é a média da casa", "???"];
    const textos = [];
    for (const frase of frases) textos.push((await conversar({ frase }, VAZIO, a)).mensagens[0].texto);
    expect(textos[0]).toContain("não dou opinião nem nota");
    expect(textos[1]).toContain("Não sou uma inteligência artificial");
    expect(textos[2]).toContain("média entre os parlamentares em exercício");
    expect(textos[3]).toBe("Não entendi. Tente assim:");
    expect(a.busca).not.toHaveBeenCalled();
    expect(a.representantes).not.toHaveBeenCalled();
  });

  it("erro de rede vira mensagem amigável", async () => {
    const a = api({ gastos: vi.fn(async () => falha(503, "Não foi possível falar com o servidor agora.")) });
    const v = await conversar({ frase: "quanto o fulano gastou" }, VAZIO, a);
    expect(v.mensagens[0].erro).toBe(true);
    expect(v.mensagens[0].texto).toContain("Tente de novo");
  });

  it("falha na busca também é tratada", async () => {
    const a = api({ busca: vi.fn(async () => falha(500, "x")) });
    const v = await conversar({ frase: "gastos do fulano" }, VAZIO, a);
    expect(v.mensagens[0].erro).toBe(true);
  });

  it("ranking não usa a pessoa lembrada e aponta a lista", async () => {
    const a = api();
    const v = await conversar({ frase: "quem gastou mais" }, { pessoa: { nome: "Fulano", caminho: "/parlamentar/10" } }, a);
    expect(v.mensagens[0].texto).toContain("não faz ranking");
    expect(v.mensagens[0].links[0].href).toBe("/parlamentares?ordenar=gastos&ordem=desc");
    expect(a.gastos).not.toHaveBeenCalled();
  });

  it("nome exato resolve homônimos parciais", async () => {
    const a = api({
      busca: vi.fn(async () =>
        ok({ itens: [item("Eduardo Gomes", "/parlamentar/535"), item("Eduardo Gomes Filho", "/parlamentar/9")], partidos: [], pessoas: [], eleitos_2026: [] }),
      ),
    });
    const v = await conversar({ frase: "gastos Eduardo Gomes" }, VAZIO, a);
    expect(a.gastos).toHaveBeenCalledWith("535", undefined);
    expect(v.mensagens[0].botoes).toHaveLength(0);
  });

  it("'quanto o governo gastou esse mês' não busca pessoa e diz o que não tem", async () => {
    const a = api();
    const v = await conversar({ frase: "Quanto o governo gastou esse mês" }, VAZIO, a, new Date(2026, 9, 30));
    expect(a.busca).not.toHaveBeenCalled();
    const m = v.mensagens[0];
    expect(m.texto).toContain("não está no Panóptico");
    expect(m.detalhes?.join(" ")).toContain("outubro de 2026");
    expect(m.links.map((l) => l.href)).toEqual(["/impostos-e-repasses", "https://portaldatransparencia.gov.br"]);
  });

  it("'comparar deputados' explica e aponta /comparar", async () => {
    const v = await conversar({ frase: "comparar deputados" }, VAZIO, api());
    expect(v.mensagens[0].links[0].href).toBe("/comparar");
  });

  it("'compare Fulano e Beltrano' resolve os dois e monta /comparar?ids=", async () => {
    const a = api({
      busca: vi.fn(async (q: string) =>
        ok({ itens: [item(q === "fulano" ? "Fulano" : "Beltrano", q === "fulano" ? "/parlamentar/10" : "/parlamentar/20")], partidos: [], pessoas: [], eleitos_2026: [] }),
      ),
    });
    const v = await conversar({ frase: "compare Fulano e Beltrano" }, VAZIO, a);
    expect(v.mensagens[0].links[0].href).toBe("/comparar?ids=10,20");
  });

  it("comparar com um nome que não existe avisa quem faltou", async () => {
    const a = api({
      busca: vi.fn(async (q: string) =>
        ok(q === "fulano" ? { itens: [item("Fulano", "/parlamentar/10")], partidos: [], pessoas: [], eleitos_2026: [] } : { itens: [], partidos: [], pessoas: [], eleitos_2026: [] }),
      ),
    });
    const v = await conversar({ frase: "fulano x xyzzy" }, VAZIO, a);
    expect(v.mensagens[0].texto).toContain('"xyzzy"');
  });

  it("resultado que só casa com palavra genérica é descartado", async () => {
    const a = api({
      busca: vi.fn(async () => ok({ itens: [], partidos: [], pessoas: [item("Governo da Silva", "/vereador/9", "Vereador")], eleitos_2026: [] })),
    });
    const v = await conversar({ frase: "Governo Federal gastos" }, VAZIO, a);
    expect(a.busca).not.toHaveBeenCalled();
    expect(v.mensagens[0].texto).toContain("não está no Panóptico");
  });

  it("'deputados de SC' responde direto pela UF", async () => {
    const a = api();
    const v = await conversar({ frase: "deputados de SC" }, VAZIO, a);
    expect(a.representantes).toHaveBeenCalledWith({ uf: "SC" });
    expect(v.mensagens[0].texto).toContain("deputados federais");
  });

  it("'moro em Gaspar' acha a cidade e consulta pelo município", async () => {
    const a = api();
    await conversar({ frase: "moro em gaspar" }, VAZIO, a);
    expect(a.representantes).toHaveBeenCalledWith({ municipio: "4205902" });
  });

  it("'dinheiro que Gaspar recebeu' cai na cidade quando não é pessoa", async () => {
    const a = api({ busca: vi.fn(async () => ok({ itens: [], partidos: [], pessoas: [], eleitos_2026: [] })) });
    const v = await conversar({ frase: "dinheiro que Gaspar recebeu" }, VAZIO, a);
    const hrefs = v.mensagens[0].links.map((l) => l.href);
    expect(hrefs).toContain("/impostos-e-repasses/SC/4205902");
    expect(hrefs).toContain("/cidade/4205902");
  });

  it("repasses para uma cidade vão ao painel dela", async () => {
    const v = await conversar({ frase: "repasses para Gaspar" }, VAZIO, api());
    expect(v.mensagens[0].links[0].href).toBe("/impostos-e-repasses/SC/4205902");
  });

  it("repasses para um estado, com ano", async () => {
    const v = await conversar({ frase: "dinheiro federal de santa catarina em 2024" }, VAZIO, api());
    expect(v.mensagens[0].links[0].href).toBe("/impostos-e-repasses/SC?ano=2024");
  });

  it("cidade com o mesmo nome em vários estados pede para escolher", async () => {
    const v = await conversar({ frase: "vereadores de bom jesus" }, VAZIO, api());
    expect(v.mensagens[0].botoes.map((b) => b.rotulo).sort()).toEqual(["Bom Jesus-RS", "Bom Jesus-SC"]);
    expect(v.mensagens[0].botoes[0].frase).toMatch(/vereadores de bom jesus (RS|SC)$/);
  });

  it("'quem é o prefeito de Gaspar' leva a Seus representantes da cidade", async () => {
    const a = api();
    const v = await conversar({ frase: "quem é o prefeito de Gaspar" }, VAZIO, a);
    expect(v.mensagens[0].links[0].href).toBe("/representantes?municipio=4205902");
    expect(a.busca).not.toHaveBeenCalled();
  });

  it("'presidente Lula' é pessoa: busca o nome", async () => {
    const a = api();
    await conversar({ frase: "presidente Lula" }, VAZIO, a);
    expect(a.busca).toHaveBeenCalledWith("lula");
  });

  it("salário traz o subsídio, a fonte e a data", async () => {
    const a = api({
      parlamentar: vi.fn(async () =>
        ok({ casa: "camara", atualizado_em: "2026-10-29T06:00:00Z", remuneracao: { subsidio_mensal: 46366.19, vigente_desde: "2025-02-01", fonte_nome: "Câmara", fonte_url: "https://f.example" } } as never),
      ),
    });
    const v = await conversar({ frase: "salário do Fulano" }, VAZIO, a);
    expect(v.mensagens[0].texto).toContain("46.366,19");
    expect(v.mensagens[0].fonte).toMatchObject({ nome: "Câmara" });
  });

  it("gastos em um mês pedido mostram o mês", async () => {
    const a = api({
      gastos: vi.fn(async () => ok({ ano: 2026, ultimo_mes: 10, total: 1000, media_casa: 2000, por_mes: [{ mes: 3, total: 123 }], ...FONTE } as never)),
    });
    const v = await conversar({ frase: "gastos em março do fulano" }, VAZIO, a, new Date(2026, 9, 30));
    expect(v.mensagens[0].detalhes?.[0]).toContain("Em março de 2026: R$");
  });

  it("projetos por tema e partido viram links com parâmetros", async () => {
    const v1 = await conversar({ frase: "projetos sobre saúde em 2025" }, VAZIO, api());
    expect(v1.mensagens[0].links[0].href).toBe("/projetos?q=saude&ano=2025");
    const v2 = await conversar({ frase: "contas do PT" }, VAZIO, api());
    expect(v2.mensagens[0].links[0].href).toBe("/partidos/PT");
  });

  it("ranking aponta a lista ordenada, sem ranking próprio", async () => {
    const v = await conversar({ frase: "gastos dos deputados de SC" }, VAZIO, api());
    expect(v.mensagens[0].links[0].href).toBe("/parlamentares?casa=camara&uf=SC&ordenar=gastos&ordem=desc");
  });

  it("'não entendi' traz 3 botões ligados ao que reconheceu", async () => {
    const v = await conversar({ frase: "governo" }, VAZIO, api());
    expect(v.mensagens[0].botoes).toHaveLength(3);
    expect(v.mensagens[0].botoes.map((b) => b.rotulo)).toContain("Impostos e repasses");
  });

  it("nome de cidade com vários homônimos pessoas também oferece a cidade", async () => {
    const a = api({
      busca: vi.fn(async () =>
        ok({ itens: [item("Alfredo Gaspar", "/parlamentar/1"), item("Larissa Gaspar", "/parlamentar/2")], partidos: [], pessoas: [], eleitos_2026: [] }),
      ),
    });
    const v = await conversar({ frase: "dinheiro que Gaspar recebeu" }, VAZIO, a);
    expect(v.mensagens[0].botoes).toHaveLength(2);
    expect(v.mensagens[0].links.map((l) => l.href)).toContain("/cidade/4205902");
  });
});
