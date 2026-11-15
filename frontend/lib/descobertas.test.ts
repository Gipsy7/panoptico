import { describe, expect, it } from "vitest";

import type { TempoDoLugar, SerieTempo } from "@/lib/api";
import { extremoDaSerie, formatarValor, gerarDescobertas, inicioDaJanela } from "@/lib/descobertas";

const serie = (id: string, pontos: [number, number][], extra: Partial<SerieTempo> = {}): SerieTempo => ({
  id,
  tema: "seguranca",
  rotulo: id,
  unidade: "por ano",
  responsavel: "estado",
  decimais: 0,
  pontos: pontos.map(([ano, valor]) => ({ ano, valor })),
  comparacoes: [],
  fonte_nome: "x",
  nota: null,
  ...extra,
});

const linha = (series: SerieTempo[]): TempoDoLugar => ({
  codigo: "4205902",
  uf: "SC",
  ano_inicial: 2014,
  ano_final: 2024,
  reais_de: 2025,
  series,
  gestoes: {},
});

describe("descobertas", () => {
  it("usa a janela fixa, não o ano de pico", () => {
    const pts = [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024].map(
      (a, i) => ({ ano: a, valor: [6, 3, 6, 9, 7, 3, 8, 4, 2, 3, 3][i] }),
    );
    expect(inicioDaJanela(pts, 5)).toEqual({ ano: 2019, valor: 3 });
    expect(inicioDaJanela([{ ano: 2024, valor: 1 }], 5)).toBeNull();
  });

  it("monta a frase literal com estado e Brasil no mesmo ano", () => {
    const d = gerarDescobertas(
      linha([
        serie("homicidios", [[2019, 3], [2020, 8], [2024, 3]]),
        serie("homicidios_taxa", [[2024, 3.9]], {
          decimais: 1,
          unidade: "por 100 mil moradores",
          comparacoes: [
            { rotulo: "estado", pontos: [{ ano: 2024, valor: 8.1 }] },
            { rotulo: "Brasil", pontos: [{ ano: 2024, valor: 20 }] },
          ],
        }),
      ]),
      "Gaspar",
      "SC",
    );
    expect(d).toHaveLength(1);
    expect(d[0].frase).toBe("3 em 2019, 3 em 2024");
    expect(d[0].pergunta).toBe("Como a violência mudou em Gaspar?");
    expect(d[0].detalhe).toContain("3,9 por 100 mil moradores em 2024; SC: 8,1; Brasil: 20,0");
  });

  it("série com um ponto só não vira descoberta; reais em mil, mi e bi", () => {
    expect(gerarDescobertas(linha([serie("pib", [[2023, 5e9]])]), "X")).toEqual([]);
    const r = { id: "x", unidade: "R$ de 2025", decimais: 0 };
    expect(formatarValor(r, 455.2)).toBe("R$ 455");
    expect(formatarValor(r, 5.54e9)).toBe("R$ 5,5 bi");
  });
});

// Os mesmos casos de backend/tests/test_extremos.py.
const CASOS: [[number, number][], string | null][] = [
  [[[2019, 5], [2020, 6], [2021, 7], [2022, 9]], "o maior da série, que começa em 2019"],
  [[[2019, 9], [2020, 7], [2021, 6], [2022, 5]], "o menor da série, que começa em 2019"],
  [[[2017, 10], [2018, 4], [2019, 5], [2020, 6], [2021, 8]], "o maior desde 2017"],
  [[[2017, 2], [2018, 8], [2019, 7], [2020, 9], [2021, 3]], "o menor desde 2017"],
  [[[2016, 1], [2017, 10], [2018, 4], [2019, 5], [2020, 8]], null],
  [[[2019, 9], [2020, 5], [2021, 6], [2022, 9]], null],
  [[[2018, 9], [2019, 5], [2020, 6], [2021, 7], [2022, 9]], "o maior desde 2018"],
  [[[2020, 1], [2021, 2], [2022, 3]], null],
  [[[2018, 5], [2019, 9], [2020, 1], [2021, 6], [2022, 5]], null],
];

describe("extremoDaSerie", () => {
  it.each(CASOS)("%j -> %s", (pontos, esperado) => {
    expect(extremoDaSerie(pontos.map(([ano, valor]) => ({ ano, valor })))).toBe(esperado);
  });

  it("entra na descoberta com o valor e o ano", () => {
    const d = gerarDescobertas(linha([serie("homicidios", [[2017, 10], [2018, 4], [2019, 5], [2020, 6], [2021, 8]])]), "Gaspar");
    expect(d[0].extremo).toBe("O maior desde 2017 (8 em 2021).");
    const sem = gerarDescobertas(linha([serie("homicidios", [[2020, 1], [2021, 2]])]), "Gaspar");
    expect(sem[0]?.extremo ?? null).toBeNull();
  });
});
