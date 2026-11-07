import { describe, expect, it } from "vitest";

import {
  mensagemDeFalha,
  montarCorpo,
  normalizarSecao,
  validarConfirmacao,
  validarContato,
  validarTexto,
  type Rascunho,
} from "./avisar-erro";

const ctx = { pagina: "/parlamentar/12", perfilTipo: "parlamentar" as const, perfilId: "12" };
const base: Rascunho = { tipo: "erro", categoria: "numero", texto: "  O valor não bate com a fonte.  ", contato: " ", confirmacao: null, secao: "Gastos do gabinete" };

describe("validarTexto", () => {
  it("exige 10 letras", () => {
    expect(validarTexto("erro", "curto")).toMatch(/pelo menos 10/);
    expect(validarTexto("erro", "1234567890")).toBeNull();
    expect(validarTexto("erro", "   123   ")).not.toBeNull();
  });
  it("limita 2000 no erro e 3000 na resposta", () => {
    expect(validarTexto("erro", "a".repeat(2001))).toMatch(/2000/);
    expect(validarTexto("resposta", "a".repeat(2001))).toBeNull();
    expect(validarTexto("resposta", "a".repeat(3001))).toMatch(/3000/);
  });
});

describe("contato e confirmação", () => {
  it("contato é opcional no erro e obrigatório na resposta", () => {
    expect(validarContato("erro", "")).toBeNull();
    expect(validarContato("resposta", " ")).not.toBeNull();
    expect(validarContato("resposta", "a@b.gov.br")).toBeNull();
    expect(validarContato("erro", "x".repeat(201))).not.toBeNull();
  });
  it("a resposta exige o canal de confirmação", () => {
    expect(validarConfirmacao("resposta", null)).not.toBeNull();
    expect(validarConfirmacao("resposta", "oficio")).toBeNull();
    expect(validarConfirmacao("erro", null)).toBeNull();
  });
});

describe("montarCorpo", () => {
  it("monta o aviso de erro sem contato nem confirmação", () => {
    expect(montarCorpo(base, ctx)).toEqual({
      tipo: "erro",
      categoria: "numero",
      texto: "O valor não bate com a fonte.",
      pagina: "/parlamentar/12",
      secao: "Gastos do gabinete",
      perfil_tipo: "parlamentar",
      perfil_id: "12",
      contato: null,
      confirmacao: null,
    });
  });
  it("na resposta, sem categoria e com confirmação", () => {
    const c = montarCorpo({ ...base, tipo: "resposta", confirmacao: "email_funcional", contato: "g@camara.leg.br", secao: null }, ctx);
    expect(c.categoria).toBeNull();
    expect(c.confirmacao).toBe("email_funcional");
    expect(c.contato).toBe("g@camara.leg.br");
    expect(c.secao).toBeNull();
  });
});

describe("mensagemDeFalha", () => {
  it("avisa do limite por hora com texto amigável", () => {
    expect(mensagemDeFalha(429)).toMatch(/nesta hora/);
  });
  it("trata rota ausente sem expor detalhe técnico", () => {
    expect(mensagemDeFalha(404, "Not Found")).toMatch(/Não foi possível enviar/);
  });
});

describe("normalizarSecao", () => {
  it("ignora acento e caixa", () => {
    expect(normalizarSecao("  Presença  em Votações ")).toBe("presenca em votacoes");
  });
});
