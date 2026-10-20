import { describe, expect, it } from "vitest";
import { urlFotoTse } from "@/lib/api";

describe("urlFotoTse", () => {
  it("monta o endereço da foto em webp com o id da candidatura", () => {
    expect(urlFotoTse(12345)).toMatch(/^https?:\/\/.+\/fotos\/12345\.webp$/);
  });
  it("ids diferentes dão endereços diferentes", () => {
    expect(urlFotoTse(1)).not.toBe(urlFotoTse(2));
  });
});
