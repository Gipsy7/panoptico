import { describe, expect, it } from "vitest";

import { TERMOS, acharTermo, buscarTermos, letraDoTermo, normalizarTermo, termoPorId, termosEmOrdem } from "./dicionario";

describe("dicionário", () => {
  it("tem ids únicos, em minúsculas e sem acento (servem de âncora)", () => {
    const ids = TERMOS.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id).toMatch(/^[a-z0-9-]+$/);
  });

  it("todo termo tem explicação, resumo e fonte oficial com endereço https", () => {
    for (const t of TERMOS) {
      expect(t.termo.length, t.id).toBeGreaterThan(0);
      expect(t.oficial.length, t.id).toBeGreaterThan(0);
      expect(t.resumo.length, t.id).toBeGreaterThan(0);
      expect(t.explicacao.length, t.id).toBeGreaterThan(40);
      expect(t.fonte.rotulo.length, t.id).toBeGreaterThan(0);
      expect(t.fonte.url, t.id).toMatch(/^https:\/\//);
    }
  });

  it("exemplos apontam para rotas do próprio site", () => {
    for (const t of TERMOS) {
      if (t.exemplo) expect(t.exemplo.href, t.id).toMatch(/^\/([a-z]|#)/);
    }
  });

  it("sinônimos já estão normalizados", () => {
    for (const t of TERMOS) for (const s of t.sinonimos ?? []) expect(normalizarTermo(s), t.id).toBe(s);
  });

  it("busca sem acento e sem maiúscula", () => {
    expect(buscarTermos("quorum").map((t) => t.id)).toContain("quorum");
    expect(buscarTermos("QUÓRUM").map((t) => t.id)).toContain("quorum");
    expect(buscarTermos("obstrucao").map((t) => t.id)).toContain("obstrucao");
    expect(buscarTermos("votação simbólica").map((t) => t.id)).toEqual(["votacao-simbolica"]);
    expect(buscarTermos("ceap").map((t) => t.id)).toContain("cota");
    expect(buscarTermos("")).toHaveLength(TERMOS.length);
    expect(buscarTermos("palavra que não existe")).toHaveLength(0);
  });

  it("índice em ordem alfabética, com a letra sem acento", () => {
    const ordem = termosEmOrdem();
    expect(ordem).toHaveLength(TERMOS.length);
    const letras = ordem.map(letraDoTermo);
    expect([...letras].sort()).toEqual(letras);
    expect(letraDoTermo(termoPorId("orientacao")!)).toBe("O");
  });

  it("acha o termo num trecho de frase, a forma mais longa vence", () => {
    expect(acharTermo("a pec")?.id).toBe("pec");
    expect(acharTermo("cota parlamentar")?.id).toBe("cota");
    expect(acharTermo("emenda pix")?.id).toBe("transferencia-especial");
    expect(acharTermo("emenda de relator")?.id).toBe("emenda-relator");
    expect(acharTermo("emenda")?.id).toBe("emenda-parlamentar");
    expect(acharTermo("votação nominal")?.id).toBe("votacao-nominal");
    expect(acharTermo("Lula")).toBeUndefined();
  });
});
