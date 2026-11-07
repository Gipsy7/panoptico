import { describe, expect, it } from "vitest";

import { degrau, enderecoCalendario, gradeDoMes, lerCalendario, rotuloDia } from "@/lib/calendario-votacoes";
import { avisoRecorte, comNumerosDeTodas, recorteDoEndereco } from "@/lib/recorte-votacoes";
import type { Votos } from "@/lib/api";

describe("calendário de votações", () => {
  it("degraus fixos da legenda", () => {
    expect([0, 1, 3, 4, 6, 7, 9, 10, 22].map(degrau)).toEqual([0, 1, 1, 2, 2, 3, 3, 4, 4]);
  });

  it("grade começa no domingo", () => {
    // 01/09/2026 é terça: duas casas vazias antes.
    const g = gradeDoMes(2026, 9);
    expect(g.slice(0, 3)).toEqual([null, null, 1]);
    expect(g.at(-1)).toBe(30);
    expect(gradeDoMes(2024, 2).at(-1)).toBe(29);
  });

  it("nome acessível de cada dia diz o recorte", () => {
    expect(rotuloDia(2026, 9, 9, 5, 11, "merito")).toBe("quarta, 9 de setembro: 5 votações sobre o texto (de 11 no dia)");
    expect(rotuloDia(2026, 9, 1, 1, 1, "todas")).toBe("terça, 1 de setembro: 1 votação");
    expect(rotuloDia(2026, 9, 6, 0, 0, "merito")).toBe("domingo, 6 de setembro: nenhuma votação nominal");
  });

  it("endereço guarda o estado e ignora valores inválidos", () => {
    const e = lerCalendario({ cal_casa: "senado", cal_mes: "2026-13", cal_dia: "2026-09-09", votacoes: "todas" });
    expect(e).toEqual({ casa: "senado", mes: undefined, dia: "2026-09-09", tipo: "todas", pagina: undefined });
    expect(enderecoCalendario(e, { dia: undefined })).toBe("/projetos?cal_casa=senado&votacoes=todas#calendario-votacoes");
    expect(enderecoCalendario({ tipo: "merito" }, { casa: "camara" })).toBe("/projetos#calendario-votacoes");
  });
});

describe("recorte das votações", () => {
  it("chave ligada por padrão", () => {
    expect(recorteDoEndereco(undefined)).toBe("merito");
    expect(recorteDoEndereco("todas")).toBe("todas");
  });

  it("diz quantas ficaram de fora", () => {
    const c = { todas: 123, merito: 48, procedimento: 75 };
    expect(avisoRecorte(c, "merito")).toBe(
      "Mostrando 48 de 123 votações. As outras 75 são de procedimento (urgência, adiamento, retirada de pauta).",
    );
    expect(avisoRecorte(c, "todas")).toBe("Mostrando todas as 123 votações: 48 sobre o texto e 75 de procedimento.");
    expect(avisoRecorte({ todas: 2, merito: 1, procedimento: 1 }, "merito")).toContain("A outra é de procedimento");
  });

  it("resumo do topo usa os números de todas as votações", () => {
    const placar = (iguais: number, total: number) => ({ iguais, total, percentual: (100 * iguais) / total });
    const v = {
      tipo: "merito",
      governo: placar(2, 2),
      partido: placar(1, 2),
      media_governo: 50,
      media_partido: 40,
      todas: { governo: placar(3, 4), partido: placar(2, 4), media_governo: 70, media_partido: 60 },
    } as unknown as Votos;
    const t = comNumerosDeTodas(v);
    expect(t.governo?.total).toBe(4);
    expect(t.media_governo).toBe(70);
    expect(t.tipo).toBe("todas");
  });
});
