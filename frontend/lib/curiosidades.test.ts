import { describe, expect, it } from "vitest";

import type { Camara, ContasMunicipio, DinheiroFederalMunicipio, EmendasMunicipio } from "@/lib/api";
import { escolherCuriosidades, sortearCuriosidade } from "@/lib/curiosidades";

const cidade = { nome: "Gaspar", uf: "SC", ibge: "4205902" };

const federal = {
  municipio: cidade,
  serie: [
    { ano: 2024, repasse: 1, fpm: 1, outros: 0, populacao: 10, por_habitante: 100, media_estado_por_habitante: 150 },
    { ano: 2025, repasse: 1, fpm: 1, outros: 0, populacao: 10, por_habitante: 200, media_estado_por_habitante: 250 },
    { ano: 2026, repasse: 1, fpm: 1, outros: 0, populacao: 10, por_habitante: 50, media_estado_por_habitante: 60 },
  ],
  contas: null,
  fontes: [{ nome: "Tesouro", url: "https://t", atualizado_em: "2026-10-01" }],
} as unknown as DinheiroFederalMunicipio;

const contas = {
  ano: 2024,
  despesa_paga: 1000,
  despesa_por_habitante: 3500,
  media_uf_despesa_por_habitante: 4000,
  fonte_nome: "Siconfi",
  fonte_url: "https://s",
  atualizado_em: "2026-09-01",
} as unknown as ContasMunicipio;

const emendas = {
  total: 500,
  total_geral: 900,
  por_habitante_geral: 12,
  media_uf_por_habitante_geral: 20,
  periodo: { inicio: 2020, fim: 2025 },
  desde: 2020,
  por_ano: [],
  fonte_nome: "Transparência",
  fonte_url: "https://e",
  atualizado_em: "2026-10-02",
} as unknown as EmendasMunicipio;

const camara = {
  itens: [{ em_exercicio: true }, { em_exercicio: true }, { em_exercicio: false }],
  fonte_nome: "SAPL",
  fonte_url: "https://c",
  atualizado_em: "2026-10-03",
} as unknown as Camara;

describe("escolherCuriosidades", () => {
  it("monta as quatro com número literal, média do estado, link e fonte", () => {
    const r = escolherCuriosidades({ cidade, federal, contas, emendas, camara, anoLimiteRepasses: 2025 });
    expect(r.map((c) => c.id)).toEqual(["repasses", "contas", "emendas", "vereadores"]);
    expect(r[0].rotulo).toContain("2025"); // ano em curso (2026) fica de fora
    expect(r[0].media?.rotulo).toBe("Média das cidades de SC");
    expect(r[0].href).toBe("/impostos-e-repasses/SC/4205902");
    expect(r[0].fonte.atualizadoEm).toBe("2026-10-01");
    expect(r[2].rotulo).toContain("2020 a 2025");
    expect(r[3].valor).toBe("2 vereadores");
    expect(r[3].href).toBe("/representantes?uf=SC&municipio=4205902");
    expect(r[3].media).toBeUndefined();
  });

  it("omite o que não tem dado", () => {
    expect(escolherCuriosidades({ cidade, anoLimiteRepasses: 2025 })).toEqual([]);
    const semGasto = { ...contas, despesa_paga: 0 } as ContasMunicipio;
    const r = escolherCuriosidades({ cidade, contas: semGasto, camara, anoLimiteRepasses: 2025 });
    expect(r.map((c) => c.id)).toEqual(["vereadores"]);
  });

  it("sem média, mostra o número sozinho; singular para um vereador", () => {
    const c = { ...contas, media_uf_despesa_por_habitante: null } as ContasMunicipio;
    const um = { ...camara, itens: [{ em_exercicio: true }] } as unknown as Camara;
    const r = escolherCuriosidades({ cidade, contas: c, camara: um, anoLimiteRepasses: 2025 });
    expect(r[0].media).toBeUndefined();
    expect(r[1].valor).toBe("1 vereador");
  });
});

describe("sortearCuriosidade", () => {
  it("escolhe uma pelo gerador e devolve null sem nenhuma", () => {
    const itens = escolherCuriosidades({ cidade, federal, contas, emendas, camara, anoLimiteRepasses: 2025 });
    expect(sortearCuriosidade(itens, () => 0)?.id).toBe("repasses");
    expect(sortearCuriosidade(itens, () => 0.99)?.id).toBe("vereadores");
    expect(sortearCuriosidade([])).toBeNull();
  });
});
