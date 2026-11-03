import { describe, expect, it } from "vitest";
import {
  ASSEMBLEIA_POR_UF,
  MINISTERIO_PUBLICO_POR_UF,
  TRIBUNAL_DE_CONTAS_POR_UF,
  canaisParaCobrar,
  linhaDeCobranca,
} from "@/lib/como-cobrar";
import { UFS } from "@/lib/ufs";

const ids = (c: { id: string }[]) => c.map((x) => x.id);

describe("canaisParaCobrar", () => {
  it("federal da Câmara: Fale Conosco, Fala.BR, MPF e TCU", () => {
    const c = canaisParaCobrar({ esfera: "federal", casa: "camara" });
    expect(ids(c)).toEqual(["casa", "falabr", "mpf", "tcu"]);
    expect(c[0].url).toContain("camara.leg.br");
  });

  it("federal do Senado troca o primeiro canal", () => {
    const c = canaisParaCobrar({ esfera: "federal", casa: "senado" });
    expect(c[0].nome).toContain("Senado");
    expect(c[0].url).toContain("senado.leg.br");
  });

  it("estadual usa a Assembleia, o MP e o tribunal da UF", () => {
    const c = canaisParaCobrar({ esfera: "estadual", uf: "sc" });
    expect(ids(c)).toEqual(["casa", "mp-estadual", "tce"]);
    expect(c[0].url).toBe(ASSEMBLEIA_POR_UF.SC);
    expect(c[2].url).toBe(TRIBUNAL_DE_CONTAS_POR_UF.SC);
  });

  it("no DF o texto fala em Câmara Legislativa e MPDFT", () => {
    const c = canaisParaCobrar({ esfera: "estadual", uf: "DF" });
    expect(c[0].nome).toContain("Câmara Legislativa");
    expect(c[1].nome).toContain("MPDFT");
  });

  it("UF sem endereço conferido fica sem link, nunca inventado", () => {
    const c = canaisParaCobrar({ esfera: "estadual", uf: "SP" });
    expect(c[1].url).toBeNull();
    expect(canaisParaCobrar({ esfera: "estadual", uf: "XX" }).every((x) => x.url === null)).toBe(true);
  });

  it("municipal usa câmara e prefeitura do catálogo e o MP e TCE do estado", () => {
    const c = canaisParaCobrar({
      esfera: "municipal",
      uf: "AC",
      canaisCidade: [
        { tipo: "prefeitura", url: "https://p.example/" },
        { tipo: "camara", url: "https://c.example/" },
        { tipo: "sapl", url: "https://s.example/" },
      ],
    });
    expect(ids(c)).toEqual(["camara-municipal", "prefeitura", "mp-estadual", "tce"]);
    expect(c[0].url).toBe("https://c.example/");
  });

  it("municipal sem catálogo da cidade só traz MP e TCE", () => {
    expect(ids(canaisParaCobrar({ esfera: "municipal", uf: "MG" }))).toEqual(["mp-estadual", "tce"]);
  });

  it("BA, GO e PA avisam do tribunal dos municípios", () => {
    const tce = canaisParaCobrar({ esfera: "municipal", uf: "BA" }).find((c) => c.id === "tce")!;
    expect(tce.oQueFaz).toContain("Tribunal de Contas dos Municípios");
    const mg = canaisParaCobrar({ esfera: "municipal", uf: "MG" }).find((c) => c.id === "tce")!;
    expect(mg.oQueFaz).not.toContain("dos Municípios");
  });
});

describe("tabelas por UF", () => {
  it("cobrem as 27 UFs e só usam https", () => {
    for (const { sigla } of UFS) {
      expect(ASSEMBLEIA_POR_UF[sigla], sigla).toMatch(/^https:\/\//);
      expect(sigla in MINISTERIO_PUBLICO_POR_UF, sigla).toBe(true);
      expect(sigla in TRIBUNAL_DE_CONTAS_POR_UF, sigla).toBe(true);
    }
  });
});

describe("linhaDeCobranca", () => {
  it("gastos federais: ouvidoria da Casa e TCU", () => {
    const l = linhaDeCobranca({ tema: "gastos", esfera: "federal", casa: "camara" });
    expect(l.pergunta).toBe("Dúvida sobre um gasto?");
    expect(l.links.map((x) => x.rotulo)).toEqual(["Fale Conosco da Câmara", "Ouvidoria do TCU", "Ver todos os canais"]);
  });

  it("gastos estaduais: Casa e tribunal do estado; sem link conferido, só o atalho", () => {
    expect(linhaDeCobranca({ tema: "gastos", esfera: "estadual", uf: "SC" }).links).toHaveLength(3);
    const sem = linhaDeCobranca({ tema: "gastos", esfera: "estadual", uf: "XX" });
    expect(sem.links.map((x) => x.rotulo)).toEqual(["Ver todos os canais"]);
  });

  it("votos e presença levam ao gabinete", () => {
    for (const tema of ["votos", "presenca"] as const) {
      const l = linhaDeCobranca({ tema, esfera: "federal" });
      expect(l.links[0]).toMatchObject({ rotulo: "Fale com o gabinete", href: "#ver-como-cobrar", externo: false });
    }
  });

  it("projetos federais: site da Casa", () => {
    const l = linhaDeCobranca({ tema: "projetos", esfera: "federal", casa: "senado" });
    expect(l.links[0].href).toContain("senado.leg.br");
    expect(l.links[0].externo).toBe(true);
  });
});
