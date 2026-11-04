import { describe, expect, it } from "vitest";
import { decidirModo, nomeArquivoCartao, textoComLink, urlCartao } from "./compartilhar";

describe("urlCartao", () => {
  it("usa o feed por padrão e aceita stories", () => {
    expect(urlCartao("/parlamentar/12/cartao")).toBe("/parlamentar/12/cartao?formato=feed");
    expect(urlCartao("/cidade/4205407/cartao", "stories")).toBe("/cidade/4205407/cartao?formato=stories");
  });
  it("troca o formato que já vinha no caminho", () => {
    expect(urlCartao("/eleito/3/cartao?formato=stories", "feed")).toBe("/eleito/3/cartao?formato=feed");
  });
});

describe("nomeArquivoCartao", () => {
  it("tira acento e símbolos", () => {
    expect(nomeArquivoCartao("João D'Ávila Neto")).toBe("joao-d-avila-neto-feed.png");
  });
  it("cai num nome padrão quando não sobra nada", () => {
    expect(nomeArquivoCartao("???", "stories")).toBe("panoptico-stories.png");
  });
});

describe("textoComLink", () => {
  it("junta frase e link", () => {
    expect(textoComLink("Veja:", "https://x.br/a")).toBe("Veja: https://x.br/a");
  });
});

describe("decidirModo", () => {
  it("nativo quando compartilha arquivos", () => {
    expect(decidirModo({ compartilha: true, compartilhaArquivos: true, podeBaixar: true })).toBe("nativo");
  });
  it("baixar quando não compartilha arquivos", () => {
    expect(decidirModo({ compartilha: true, compartilhaArquivos: false, podeBaixar: true })).toBe("baixar");
    expect(decidirModo({ compartilha: false, compartilhaArquivos: false, podeBaixar: true })).toBe("baixar");
  });
  it("só WhatsApp quando nada é possível", () => {
    expect(decidirModo({ compartilha: false, compartilhaArquivos: false, podeBaixar: false })).toBe("whatsapp");
  });
});
