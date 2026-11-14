import { describe, expect, it } from "vitest";

import {
  chaveDoNome,
  enderecoComparar,
  listaDeNomes,
  maisVotadosEmExercicio,
  mesmoGrupo,
  senadoresDoEstado,
} from "./comparar-sugestoes";

const p = (id: number, nome_parlamentar: string) => ({ id, nome_parlamentar });
const v = (nome_urna: string, eleito = true) => ({ nome_urna, eleito });

describe("chaveDoNome", () => {
  it("ignora acento, caixa e espaços a mais", () => {
    expect(chaveDoNome("  Esperidião   Amin ")).toBe("ESPERIDIAO AMIN");
    expect(chaveDoNome("ANA PAULA LIMA")).toBe(chaveDoNome("Ana Paula Lima"));
  });
});

describe("senadoresDoEstado", () => {
  it("devolve todos em ordem alfabética", () => {
    const r = senadoresDoEstado([p(554, "Jorge Seif"), p(538, "Esperidião Amin"), p(547, "Ivete da Silveira")]);
    expect(r?.map((s) => s.id)).toEqual([538, 547, 554]);
    expect(enderecoComparar(r!.map((s) => s.id))).toBe("/comparar?ids=538,547,554");
  });

  it("com menos de dois não há atalho", () => {
    expect(senadoresDoEstado([p(1, "Só Um")])).toBeNull();
    expect(senadoresDoEstado([])).toBeNull();
  });
});

describe("maisVotadosEmExercicio", () => {
  const deputados = [p(33, "Ana Paula Lima"), p(242, "Ismael"), p(261, "Jorge Goetten"), p(84, "Caroline de Toni")];

  it("pega os dois eleitos mais votados, na ordem dos votos, pulando quem não se elegeu", () => {
    const votados = [v("ANA PAULA LIMA"), v("ALBA", false), v("ISMAEL"), v("JORGE GOETTEN")];
    expect(maisVotadosEmExercicio(votados, deputados)?.map((d) => d.id)).toEqual([33, 242]);
  });

  it("some quando um dos dois primeiros eleitos não é reconhecido pelo nome", () => {
    // "CAROL DE TONI" é a segunda eleita mais votada, mas o nome parlamentar é outro: mostrar
    // a terceira como se fosse a segunda seria errado.
    const votados = [v("ANA PAULA LIMA"), v("CAROL DE TONI"), v("ISMAEL")];
    expect(maisVotadosEmExercicio(votados, deputados)).toBeNull();
  });

  it("some quando o nome serve a dois deputados ou há menos de dois eleitos", () => {
    const dois = [...deputados, p(999, "ISMAEL")];
    expect(maisVotadosEmExercicio([v("ANA PAULA LIMA"), v("ISMAEL")], dois)).toBeNull();
    expect(maisVotadosEmExercicio([v("ANA PAULA LIMA"), v("ALBA", false)], deputados)).toBeNull();
    expect(maisVotadosEmExercicio([], deputados)).toBeNull();
  });
});

describe("mesmoGrupo e listaDeNomes", () => {
  it("compara ids sem olhar a ordem", () => {
    expect(mesmoGrupo([538, 547, 554], [554, 538, 547])).toBe(true);
    expect(mesmoGrupo([538, 547], [538, 547, 554])).toBe(false);
  });

  it("junta nomes com vírgula e 'e'", () => {
    expect(listaDeNomes(["Amin", "Seif", "Ivete"])).toBe("Amin, Seif e Ivete");
    expect(listaDeNomes(["Ana", "Ismael"])).toBe("Ana e Ismael");
    expect(listaDeNomes(["Ana"])).toBe("Ana");
  });
});
