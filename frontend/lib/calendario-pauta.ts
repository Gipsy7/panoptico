// Pauta do Plenário em formato de calendário (iCalendar, RFC 5545), para assinar no celular.
// Lógica pura: recebe os itens da API e devolve o texto do arquivo. Eventos de dia inteiro,
// porque a pauta traz a data da sessão, não a hora de cada votação.

import type { ItemDePauta } from "@/lib/api";

const CASA = { camara: "da Câmara", senado: "do Senado" } as const;

/** Escapa o texto como o formato pede (barra, ponto e vírgula, vírgula e quebra de linha). */
export function escaparIcs(texto: string): string {
  return texto.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
}

/** Dobra a linha a cada 75 bytes (UTF-8), sem cortar um caractere no meio. */
export function dobrarLinha(linha: string): string {
  const codificar = new TextEncoder();
  const partes: string[] = [];
  let atual = "";
  let limite = 75;
  for (const ch of linha) {
    if (codificar.encode(atual + ch).length > limite) {
      partes.push(atual);
      atual = ch;
      limite = 74; // as linhas seguintes começam com um espaço
    } else {
      atual += ch;
    }
  }
  partes.push(atual);
  return partes.join("\r\n ");
}

function dataIcs(iso: string): string {
  return iso.slice(0, 10).replace(/-/g, "");
}

function diaSeguinte(iso: string): string {
  const d = new Date(`${iso.slice(0, 10)}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10).replace(/-/g, "");
}

function carimbo(agora: Date): string {
  return agora.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

/** Texto completo do arquivo .ics. `site` é o endereço base para os links das páginas. */
export function calendarioDaPauta(itens: ItemDePauta[], site: string, agora: Date): string {
  const linhas = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Panoptico//Pauta do Plenario//PT",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Pauta do Plenário (Panóptico)",
    "X-WR-CALDESC:Projetos marcados para votação no Plenário da Câmara e do Senado. Fonte: Dados Abertos da Câmara e do Senado.",
    "X-WR-TIMEZONE:America/Sao_Paulo",
    "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
  ];
  const vistos = new Set<string>();
  for (const i of itens) {
    const uid = `${i.casa}-${i.data.slice(0, 10)}-${i.sessao}-${i.ordem ?? ""}-${i.proposicao ?? "item"}`
      .replace(/[^A-Za-z0-9-]/g, "")
      .toLowerCase();
    if (vistos.has(uid)) continue;
    vistos.add(uid);
    const url = i.link ? `${site}${i.link.replace(/^\/votacoes\/local\//, "/votacao/local/")}` : i.url_oficial;
    const descricao = [
      i.ementa,
      "Estar na pauta não garante que o projeto será votado neste dia.",
      url ? `Mais: ${url}` : null,
      `Fonte: Dados Abertos ${CASA[i.casa]}.`,
    ]
      .filter(Boolean)
      .join("\n");
    linhas.push(
      "BEGIN:VEVENT",
      `UID:${uid}@panoptico.social.br`,
      `DTSTAMP:${carimbo(agora)}`,
      `DTSTART;VALUE=DATE:${dataIcs(i.data)}`,
      `DTEND;VALUE=DATE:${diaSeguinte(i.data)}`,
      `SUMMARY:${escaparIcs(`Na pauta do Plenário ${CASA[i.casa]}: ${i.proposicao ?? "item sem identificação"}`)}`,
      `DESCRIPTION:${escaparIcs(descricao)}`,
      ...(url ? [`URL:${url}`] : []),
      "TRANSP:TRANSPARENT",
      "END:VEVENT",
    );
  }
  linhas.push("END:VCALENDAR");
  return linhas.map(dobrarLinha).join("\r\n") + "\r\n";
}
