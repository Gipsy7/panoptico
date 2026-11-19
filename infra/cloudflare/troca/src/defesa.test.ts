import { describe, expect, it } from "vitest";
import {
  DURACAO_MS,
  LIMITE_PEDIDOS_HORA,
  RENOVAR_ANTES_MS,
  aspas,
  defesaVazia,
  expressaoBrasilPrimeiro,
  expressaoPaises,
  expressaoRobos,
  roboLiberado,
  vigiar,
} from "./defesa";

const T = Date.UTC(2026, 10, 19, 12);
const CHROME99 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36";

describe("vigiar", () => {
  it("põe no desafio o país e o robô que passam do limite e da fração (caso de 19/11)", () => {
    const r = vigiar(
      defesaVazia(),
      32500,
      [{ valor: "CN", pedidos: 28698 }, { valor: "US", pedidos: 3721 }, { valor: "BR", pedidos: 78 }],
      [{ valor: CHROME99, pedidos: 20200 }, { valor: "Mozilla/5.0 (compatible; Baiduspider/2.0)", pedidos: 3613 }],
      T,
    );
    expect(r.novos.map((i) => `${i.tipo}:${i.valor}`)).toEqual(["pais:CN", `robo:${CHROME99}`]);
    expect(r.novos[0].expira).toBe(T + DURACAO_MS);
    expect(r.regravarRegras).toBe(true);
  });

  it("nunca o Brasil, nem buscadores, prévias de link e o servidor do site", () => {
    const r = vigiar(
      defesaVazia(),
      10000,
      [{ valor: "BR", pedidos: 9000 }],
      [
        { valor: "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", pedidos: 9000 },
        { valor: "WhatsApp/2.23.20.0", pedidos: 9000 },
        { valor: "facebookexternalhit/1.1", pedidos: 9000 },
        { valor: "node", pedidos: 9000 },
      ],
      T,
    );
    expect(r.novos).toEqual([]);
    expect(r.mudou).toBe(false);
  });

  it("abaixo do limite absoluto ou da fração não age", () => {
    const pouco = vigiar(defesaVazia(), 4000, [{ valor: "CN", pedidos: LIMITE_PEDIDOS_HORA - 1 }], [], T);
    expect(pouco.novos).toEqual([]);
    const fracao = vigiar(defesaVazia(), 100000, [{ valor: "US", pedidos: 20000 }], [], T);
    expect(fracao.novos).toEqual([]);
  });

  it("item ativo não volta a avisar; renova só perto de expirar", () => {
    const primeira = vigiar(defesaVazia(), 32500, [{ valor: "CN", pedidos: 28000 }], [], T);
    const logo = vigiar(primeira.defesa, 32500, [{ valor: "CN", pedidos: 28000 }], [], T + 10 * 60_000);
    expect(logo.novos).toEqual([]);
    expect(logo.mudou).toBe(false);
    const perto = T + DURACAO_MS - RENOVAR_ANTES_MS + 60_000;
    const renovada = vigiar(primeira.defesa, 32500, [{ valor: "CN", pedidos: 28000 }], [], perto);
    expect(renovada.novos).toEqual([]);
    expect(renovada.mudou).toBe(true);
    expect(renovada.regravarRegras).toBe(false);
    expect(renovada.defesa.itens[0].expira).toBe(perto + DURACAO_MS);
  });

  it("item vencido sai e as regras são regravadas", () => {
    const primeira = vigiar(defesaVazia(), 32500, [{ valor: "CN", pedidos: 28000 }], [], T);
    const depois = vigiar(primeira.defesa, 500, [{ valor: "CN", pedidos: 10 }], [], T + DURACAO_MS + 1);
    expect(depois.expirados.map((i) => i.valor)).toEqual(["CN"]);
    expect(depois.defesa.itens).toEqual([]);
    expect(depois.regravarRegras).toBe(true);
  });
});

describe("roboLiberado", () => {
  it("node só sozinho", () => {
    expect(roboLiberado("node")).toBe(true);
    expect(roboLiberado("nodecrawler/1.0")).toBe(false);
  });
  it("Perplexity-User sim, PerplexityBot não", () => {
    expect(roboLiberado("Mozilla/5.0 (compatible; Perplexity-User/1.0)")).toBe(true);
    expect(roboLiberado("Mozilla/5.0 (compatible; PerplexityBot/1.0)")).toBe(false);
  });
});

describe("expressões do firewall", () => {
  it("aspas escapa aspas e barra", () => {
    expect(aspas('a"b\\c')).toBe('"a\\"b\\\\c"');
  });
  it("Brasil primeiro vale só no site e poupa robôs verificados e liberados", () => {
    const e = expressaoBrasilPrimeiro("panoptico.social.br", undefined);
    expect(e).toContain('http.host eq "panoptico.social.br"');
    expect(e).toContain('not ip.src.country in {"BR"}');
    expect(e).toContain("not cf.client.bot");
    expect(e).toContain('lower(http.user_agent) contains "whatsapp"');
    expect(e).not.toContain("ip.src eq");
    expect(expressaoBrasilPrimeiro("x", "200.1.2.3")).toContain("not ip.src eq 200.1.2.3");
  });
  it("países: sem repetição, sem BR, só códigos válidos", () => {
    expect(expressaoPaises(["CN", "cn", "BR", "XYZ"])).toBe(
      '(ip.src.country in {"CN"} and not cf.client.bot)',
    );
    expect(expressaoPaises(["BR"])).toBeNull();
  });
  it("robôs: igualdade exata e nunca um liberado", () => {
    expect(expressaoRobos([CHROME99, "node"])).toBe(`(http.user_agent eq ${aspas(CHROME99)})`);
    expect(expressaoRobos([])).toBeNull();
  });
});
