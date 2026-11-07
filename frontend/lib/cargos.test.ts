import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  CARGOS,
  CARGOS_LISTA,
  CF_URL,
  FAIXAS_VEREADOR,
  SUBSIDIO_FEDERAL,
  TETO_DEPUTADO_ESTADUAL,
  cargoDoRotulo,
  ganhaVereador,
  percentualDe,
  tetoVereador,
  tetoVereadorPercentual,
  textoDoCargo,
  type CargoId,
} from "./cargos";

const IDS: CargoId[] = [
  "presidente",
  "vice-presidente",
  "senador",
  "deputado-federal",
  "governador",
  "vice-governador",
  "deputado-estadual",
  "prefeito",
  "vice-prefeito",
  "vereador",
];

describe("registro de cargos", () => {
  it("tem os dez cargos, no mapa e na lista", () => {
    expect(Object.keys(CARGOS).sort()).toEqual([...IDS].sort());
    expect(CARGOS_LISTA.map((c) => c.id)).toEqual(IDS);
  });

  it.each(IDS)("%s tem faz, pode e não pode, cada frase com artigo da CF", (id) => {
    const c = CARGOS[id];
    expect(c.faz.length).toBeGreaterThan(10);
    expect(c.fazOficial.length).toBeGreaterThan(3);
    expect(c.pode.length).toBeGreaterThan(0);
    expect(c.naoPode.length).toBeGreaterThan(0);
    for (const i of [...c.pode, ...c.naoPode]) {
      expect(i.texto.length).toBeGreaterThan(10);
      expect(i.artigo).toMatch(/^CF art\. \d+/);
    }
    expect(c.ganha.texto.length).toBeGreaterThan(10);
    expect(c.ganha.artigo).toMatch(/^CF art\. \d+/);
    expect(c.ganha.fonte.url).toMatch(/^https:\/\//);
  });

  it("não usa adjetivo de juízo", () => {
    const tudo = CARGOS_LISTA.flatMap((c) => [
      c.faz,
      ...c.pode.map((p) => p.texto),
      ...c.naoPode.map((p) => p.texto),
      c.ganha.texto,
    ]).join(" ");
    expect(tudo).not.toMatch(/\b(melhor|pior|bom|mau|corrupt\w*|honest\w*)\b/i);
  });

  it("mantém os textos que a página de representantes já mostrava", () => {
    expect(CARGOS.presidente.faz).toBe(
      "O presidente comanda o governo do país: dirige os ministérios e cuida do dinheiro e dos serviços nacionais, como o INSS.",
    );
    expect(CARGOS.senador.faz).toBe("Os senadores votam as leis do país e analisam o que o governo faz. Cada estado tem 3.");
    expect(textoDoCargo(CARGOS["deputado-estadual"], true).faz).toBe(
      "Os deputados distritais votam as leis do Distrito Federal e acompanham o que o governador faz.",
    );
    expect(textoDoCargo(CARGOS.governador, false).fazOficial).toBe("Chefia do Poder Executivo estadual");
    expect(textoDoCargo(CARGOS.governador, true).fazOficial).toBe("Chefia do Poder Executivo distrital");
    expect(CARGOS.vereador.fazOficial).toBe("Vereadores");
  });
});

describe("salário", () => {
  it("deputado federal e senador ganham o mesmo, o da tabela do backend", () => {
    const py = readFileSync(path.resolve(__dirname, "../../backend/app/services/remuneracao.py"), "utf8");
    const valores = [...py.matchAll(/Decimal\("([\d.]+)"\)/g)].map((m) => Number(m[1]));
    expect(SUBSIDIO_FEDERAL).toBe(valores[valores.length - 1]);
    expect(CARGOS.senador.ganha.valor).toBe(SUBSIDIO_FEDERAL);
    expect(CARGOS["deputado-federal"].ganha.valor).toBe(SUBSIDIO_FEDERAL);
  });

  it("deputado estadual: teto de 75% do federal, sem valor fixo", () => {
    expect(TETO_DEPUTADO_ESTADUAL).toBe(34774.64);
    expect(CARGOS["deputado-estadual"].ganha.valor).toBeUndefined();
    expect(CARGOS["deputado-estadual"].ganha.texto).toContain("75%");
  });

  it("presidente, governador e prefeito dizem quem fixa o valor e não trazem número", () => {
    for (const id of ["presidente", "governador", "prefeito"] as CargoId[]) {
      expect(CARGOS[id].ganha.valor).toBeUndefined();
      expect(CARGOS[id].ganha.texto).not.toMatch(/R\$/);
    }
    expect(CARGOS.presidente.ganha.fonte.url).toBe(CF_URL);
  });
});

describe("teto do vereador pela população (CF art. 29, VI)", () => {
  it.each([
    [1, 20],
    [10_000, 20],
    [10_001, 30],
    [50_000, 30],
    [50_001, 40],
    [100_000, 40],
    [100_001, 50],
    [300_000, 50],
    [300_001, 60],
    [500_000, 60],
    [500_001, 75],
    [12_000_000, 75],
  ])("%i habitantes: até %i%% do deputado estadual", (habitantes, pct) => {
    expect(tetoVereadorPercentual(habitantes)).toBe(pct);
    expect(ganhaVereador(habitantes).percentual).toBe(pct);
  });

  it("a frase cita a faixa e diz que a câmara define o valor", () => {
    const g = ganhaVereador(360_000);
    expect(g.faixa).toBe("de 300.001 a 500 mil habitantes");
    expect(g.texto).toContain("60%");
    expect(g.texto).toContain("câmara da cidade define");
  });

  it("tem seis faixas, crescentes", () => {
    expect(FAIXAS_VEREADOR).toHaveLength(6);
    const pcts = FAIXAS_VEREADOR.map((f) => f.percentual);
    expect(pcts).toEqual([...pcts].sort((a, b) => a - b));
  });
});

describe("teto em reais do vereador e do deputado estadual", () => {
  it("Blumenau (390.371 hab.) em SC: 60% de R$ 34.774,64 = R$ 20.864,78", () => {
    const t = tetoVereador(390_371, 34774.64);
    expect(t).toMatchObject({ percentual: 60, indice: 4, valor: 20864.78 });
  });

  it("sem o subsídio do deputado estadual publicado, só o percentual", () => {
    expect(tetoVereador(1_388_791, null)).toMatchObject({ percentual: 75, valor: null });
  });

  it("percentualDe arredonda em centavos", () => {
    expect(percentualDe(34774.64, 75)).toBe(26080.98);
    expect(percentualDe(46366.19, 75)).toBe(TETO_DEPUTADO_ESTADUAL);
  });
});

describe("cargoDoRotulo", () => {
  it.each([
    ["Deputado Federal", "deputado-federal"],
    ["Deputado Estadual", "deputado-estadual"],
    ["Deputado distrital", "deputado-estadual"],
    ["Vice-prefeito", "vice-prefeito"],
    ["Vice-governador", "vice-governador"],
    ["Vice-presidente", "vice-presidente"],
    ["Vereadora", "vereador"],
    ["Prefeito", "prefeito"],
    ["Governador", "governador"],
    ["Presidente", "presidente"],
    ["Senador", "senador"],
  ])("%s", (rotulo, id) => {
    expect(cargoDoRotulo(rotulo)).toBe(id);
  });

  it("devolve null para suplente, vazio e cargo fora da lista", () => {
    expect(cargoDoRotulo("1º Suplente")).toBeNull();
    expect(cargoDoRotulo("Deputado")).toBeNull();
    expect(cargoDoRotulo(null)).toBeNull();
    expect(cargoDoRotulo("Ministro")).toBeNull();
  });
});
