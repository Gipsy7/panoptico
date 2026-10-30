import { describe, expect, it } from "vitest";

import { SITE_OFICIAL, baseCanonica, lerAmbiente } from "@/lib/site";

describe("lerAmbiente", () => {
  it("só 'release' é homologação", () => {
    expect(lerAmbiente("release")).toBe("release");
    expect(lerAmbiente(" Release ")).toBe("release");
  });
  it("vazio, ausente ou outro valor é produção", () => {
    expect(lerAmbiente(undefined)).toBe("producao");
    expect(lerAmbiente("")).toBe("producao");
    expect(lerAmbiente("producao")).toBe("producao");
    expect(lerAmbiente("teste")).toBe("producao");
  });
});

describe("baseCanonica", () => {
  it("no release aponta para o site oficial", () => {
    expect(baseCanonica("release", "https://release.panoptico.social.br")).toBe(SITE_OFICIAL);
  });
  it("na produção usa o próprio endereço", () => {
    expect(baseCanonica("producao", "https://panoptico.social.br")).toBe("https://panoptico.social.br");
    expect(baseCanonica("producao", "http://localhost:3000")).toBe("http://localhost:3000");
  });
});
