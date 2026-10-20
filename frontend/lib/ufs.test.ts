import { describe, expect, it } from "vitest";
import { UFS } from "@/lib/ufs";

describe("UFS", () => {
  it("são 27 unidades da federação", () => expect(UFS).toHaveLength(27));
  it("as siglas são únicas, com duas letras maiúsculas", () => {
    const siglas = UFS.map((u) => u.sigla);
    expect(new Set(siglas).size).toBe(27);
    for (const s of siglas) expect(s).toMatch(/^[A-Z]{2}$/);
  });
  it("todas têm nome, e os nomes são únicos", () => {
    for (const u of UFS) expect(u.nome.trim().length).toBeGreaterThan(0);
    expect(new Set(UFS.map((u) => u.nome)).size).toBe(27);
  });
  it("traz siglas e nomes conhecidos", () => {
    const por = Object.fromEntries(UFS.map((u) => [u.sigla, u.nome]));
    expect(por.DF).toBe("Distrito Federal");
    expect(por.SP).toBe("São Paulo");
    expect(por.AC).toBe("Acre");
  });
});
