import { describe, expect, it } from "vitest";
import { idDaCasa } from "@/lib/cobertura";

describe("idDaCasa", () => {
  it("minúsculas", () => expect(idDaCasa("ALAC")).toBe("alac"));
  it("espaços viram hífen", () => expect(idDaCasa("Governo de AC")).toBe("governo-de-ac"));
  it("remove acentos", () => expect(idDaCasa("Câmara de São Paulo")).toBe("camara-de-sao-paulo"));
  it("sequências de símbolos viram um hífen só", () => expect(idDaCasa("A  &  B / C")).toBe("a-b-c"));
  it("não deixa hífen nas pontas", () => expect(idDaCasa("  (Senado)  ")).toBe("senado"));
  it("mantém dígitos", () => expect(idDaCasa("Casa 2")).toBe("casa-2"));
  it("vazio dá vazio", () => expect(idDaCasa("")).toBe(""));
});
