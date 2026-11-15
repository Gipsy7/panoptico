import { describe, expect, it } from "vitest";

import type { ItemDePauta } from "@/lib/api";

import { calendarioDaPauta, dobrarLinha, escaparIcs } from "./calendario-pauta";

const item = (p: Partial<ItemDePauta> = {}): ItemDePauta => ({
  casa: "senado",
  data: "2026-11-17",
  sessao: "594178",
  ordem: 1,
  proposicao: "PLP 299/2026",
  proposicao_id_externo: "176328",
  ementa: "Altera a Lei Complementar nº 200, de 2023; e dá outras providências",
  url_oficial: "https://www25.senado.leg.br/web/atividade/materias/-/materia/176328",
  link: "/projetos/senado/176328",
  ...p,
});

const AGORA = new Date("2026-11-15T10:00:00Z");

/** Desfaz a dobra (CRLF + espaço) para ler cada propriedade inteira. */
const desdobrar = (ics: string) => ics.replace(/\r\n /g, "");

describe("escaparIcs e dobrarLinha", () => {
  it("escapa barra, ponto e vírgula, vírgula e quebra de linha", () => {
    expect(escaparIcs("a;b,c\\d\ne")).toBe("a\\;b\\,c\\\\d\\ne");
  });

  it("dobra em 75 bytes sem cortar acento no meio", () => {
    const longa = `DESCRIPTION:${"ação ".repeat(40)}`;
    const dobrada = dobrarLinha(longa);
    const partes = dobrada.split("\r\n");
    expect(partes.length).toBeGreaterThan(1);
    for (const p of partes) expect(new TextEncoder().encode(p).length).toBeLessThanOrEqual(75);
    expect(dobrada.replace(/\r\n /g, "")).toBe(longa);
  });
});

describe("calendarioDaPauta", () => {
  it("um evento de dia inteiro por item, com link para a página do site", () => {
    const ics = calendarioDaPauta([item()], "https://panoptico.social.br", AGORA);
    expect(ics.startsWith("BEGIN:VCALENDAR\r\n")).toBe(true);
    expect(ics.endsWith("END:VCALENDAR\r\n")).toBe(true);
    expect(ics).not.toMatch(/[^\r]\n/); // só CRLF
    const t = desdobrar(ics);
    expect(t).toContain("DTSTART;VALUE=DATE:20261117");
    expect(t).toContain("DTEND;VALUE=DATE:20261118");
    expect(t).toContain("SUMMARY:Na pauta do Plenário do Senado: PLP 299/2026");
    expect(t).toContain("URL:https://panoptico.social.br/projetos/senado/176328");
    expect(t).toContain("Estar na pauta não garante que o projeto será votado neste dia.");
    expect(t).toContain("Lei Complementar nº 200\\, de 2023\\; e dá outras providências");
    expect(t).toContain("DTSTAMP:20261115T100000Z");
  });

  it("sem link do site usa o oficial; repetido entra uma vez; fim de mês vira o mês", () => {
    const ics = desdobrar(
      calendarioDaPauta(
        [item({ link: null, data: "2026-11-30" }), item({ link: null, data: "2026-11-30" }), item({ casa: "camara", ordem: 2 })],
        "https://panoptico.social.br",
        AGORA,
      ),
    );
    expect(ics.match(/BEGIN:VEVENT/g)).toHaveLength(2);
    expect(ics).toContain("URL:https://www25.senado.leg.br/web/atividade/materias/-/materia/176328");
    expect(ics).toContain("DTEND;VALUE=DATE:20261201");
    expect(ics).toContain("SUMMARY:Na pauta do Plenário da Câmara: PLP 299/2026");
  });

  it("pauta vazia ainda é um calendário válido", () => {
    expect(calendarioDaPauta([], "https://x", AGORA)).toMatch(/^BEGIN:VCALENDAR[\s\S]*END:VCALENDAR\r\n$/);
  });
});
