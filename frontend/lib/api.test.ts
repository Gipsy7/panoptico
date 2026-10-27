import { describe, expect, it } from "vitest";
import { legendaFoto, urlFotoDe, urlFotoTse } from "@/lib/api";

describe("urlFotoTse", () => {
  it("monta o endereço da foto em webp com o id da candidatura", () => {
    expect(urlFotoTse(12345)).toMatch(/^https?:\/\/.+\/fotos\/12345\.webp$/);
  });
  it("ids diferentes dão endereços diferentes", () => {
    expect(urlFotoTse(1)).not.toBe(urlFotoTse(2));
  });
});

describe("foto emprestada de outra eleição", () => {
  it("usa a candidatura dona da foto, se houver", () => {
    expect(urlFotoDe({ id: 2, foto_de: 1 })).toBe(urlFotoTse(1));
    expect(urlFotoDe({ id: 2, foto_de: null })).toBe(urlFotoTse(2));
    expect(urlFotoDe({ id: 2 })).toBe(urlFotoTse(2));
  });
  it("só legenda com o ano quando a foto é de outra eleição", () => {
    expect(legendaFoto({ foto_ano: 2022 })).toBe("foto de 2022");
    expect(legendaFoto({ foto_ano: null })).toBeNull();
    expect(legendaFoto({})).toBeNull();
  });
});
