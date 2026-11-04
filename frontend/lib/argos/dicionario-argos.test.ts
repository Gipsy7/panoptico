import { describe, expect, it } from "vitest";

import { termoPorId } from "@/lib/dicionario";

import { interpretar } from "./interpretar";
import { respostaTermo } from "./responder";

describe("Argos e o dicionário", () => {
  it.each([
    ["o que é PEC?", "pec"],
    ["O que significa quórum", "quorum"],
    ["oq e obstrucao", "obstrucao"],
    ["o que quer dizer votação simbólica?", "votacao-simbolica"],
    ["o que é a cota parlamentar?", "cota"],
    ["o que é uma emenda pix", "transferencia-especial"],
    ["significado de CEAP", "cota"],
    ["PEC, o que é?", "pec"],
    ["o que é emenda de relator", "emenda-relator"],
    ["o que é o Fundo Partidário", "fundo-partidario"],
  ])("%s → %s", (frase, id) => {
    expect(interpretar(frase)).toMatchObject({ assunto: "termo", termoId: id });
  });

  it("não toma o lugar de outras perguntas", () => {
    expect(interpretar("o que é a média da Casa?").assunto).toBe("site");
    expect(interpretar("o que faz um vereador?").assunto).toBe("cargo");
    expect(interpretar("quanto o Fulano gastou da cota").assunto).toBe("gastos");
    expect(interpretar("o que é a cota do Nikolas").assunto).not.toBe("termo");
    expect(interpretar("pec").assunto).not.toBe("termo");
  });

  it("responde com o texto do dicionário, o termo oficial, a fonte e o link", () => {
    const t = termoPorId("pec")!;
    const m = respostaTermo("pec");
    expect(m.texto).toContain(t.explicacao);
    expect(m.detalhes).toEqual([`Termo oficial: ${t.oficial}.`]);
    expect(m.fonte).toMatchObject({ nome: t.fonte.rotulo, url: t.fonte.url });
    expect(m.fonte?.atualizadoEm).toBeTruthy();
    expect(m.links[0]).toEqual({ rotulo: 'Ver "PEC" no dicionário', href: "/dicionario#pec" });
  });

  it("termo desconhecido cai no 'não entendi'", () => {
    expect(respostaTermo("nao-existe").fonte).toBeUndefined();
  });
});
