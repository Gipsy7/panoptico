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
    expect(a.gastos).toHaveBeenCalledWith("10");
    expect(v.mensagens[0].texto).toContain("Fulano usou");
    expect(v.mensagens[0].fonte).toBeDefined();
    expect(v.contexto.pessoa).toEqual({ nome: "Fulano", caminho: "/parlamentar/10" });
  });

  it("lembra da pessoa: 'e a presença dele?' não busca de novo", async () => {
    const a = api();
    const primeira = await conversar({ frase: "quanto o fulano gastou" }, VAZIO, a);
    const segunda = await conversar({ frase: "e a presença dele?" }, primeira.contexto, a);
    expect(a.busca).toHaveBeenCalledTimes(1);
    expect(a.presenca).toHaveBeenCalledWith("10");
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
    expect(a.representantes).toHaveBeenCalledWith("88340-000");
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
    expect(a.presenca).toHaveBeenCalledWith("2");
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
    expect(v.mensagens[0].botoes.map((b) => b.rotulo)).toEqual(["Gastos", "Presença nas votações", "Projetos de lei", "Emendas"]);
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
    expect(v.mensagens[0].links[0].href).toBe("/parlamentares");
    expect(a.gastos).not.toHaveBeenCalled();
  });

  it("nome exato resolve homônimos parciais", async () => {
    const a = api({
      busca: vi.fn(async () =>
        ok({ itens: [item("Eduardo Gomes", "/parlamentar/535"), item("Eduardo Gomes Filho", "/parlamentar/9")], partidos: [], pessoas: [], eleitos_2026: [] }),
      ),
    });
    const v = await conversar({ frase: "gastos Eduardo Gomes" }, VAZIO, a);
    expect(a.gastos).toHaveBeenCalledWith("535");
    expect(v.mensagens[0].botoes).toHaveLength(0);
  });
});
