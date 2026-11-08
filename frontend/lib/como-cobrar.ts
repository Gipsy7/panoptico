/**
 * "Como cobrar": canais oficiais para tirar dúvida, pedir informação ou levar uma queixa sobre
 * quem exerce um mandato. Dados estáticos, só endereços oficiais conferidos (resposta 200 em
 * 03/11/2026). Onde o endereço não foi confirmado o campo `url` fica `null` e a tela mostra o
 * nome do órgão sem link; nunca se inventa endereço.
 *
 * O texto descreve o que cada órgão faz, sem juízo sobre a pessoa nem sobre o resultado.
 */
export type Esfera = "federal" | "estadual" | "municipal";
export type CasaFederal = "camara" | "senado";

export type CanalCobranca = {
  id: string;
  nome: string;
  /** O que o canal faz, em uma frase do dia a dia. */
  oQueFaz: string;
  url: string | null;
};

/** Canal de uma cidade já catalogado (`data/canais_oficiais.csv`, rota /municipios/{ibge}/canais). */
export type CanalCidade = { tipo: string; url: string };

export const VERIFICADO_EM = "2026-11-03";

const FALE_CONOSCO_CAMARA = "https://www.camara.leg.br/fale-conosco";
const OUVIDORIA_SENADO = "https://www12.senado.leg.br/institucional/ouvidoria";
const FALA_BR = "https://falabr.cgu.gov.br/";
const MPF = "https://www.mpf.mp.br/";
const OUVIDORIA_TCU = "https://portal.tcu.gov.br/ouvidoria/";

/** Site da Assembleia Legislativa (ou Câmara Legislativa, no DF) de cada UF. */
export const ASSEMBLEIA_POR_UF: Record<string, string> = {
  AC: "https://www.al.ac.leg.br/",
  AL: "https://www.al.al.leg.br/",
  AP: "https://www.al.ap.leg.br/",
  AM: "https://www.aleam.gov.br/",
  BA: "https://www.al.ba.gov.br/",
  CE: "https://www.al.ce.gov.br/",
  DF: "https://www.cl.df.gov.br/",
  ES: "https://www.al.es.gov.br/",
  GO: "https://portal.al.go.leg.br/",
  MA: "https://www.al.ma.leg.br/",
  MT: "https://www.al.mt.gov.br/",
  MS: "https://al.ms.gov.br/",
  MG: "https://www.almg.gov.br/",
  PA: "https://www.alepa.pa.gov.br/",
  PB: "https://www.al.pb.leg.br/",
  PR: "https://www.assembleia.pr.leg.br/",
  PE: "https://www.alepe.pe.gov.br/",
  PI: "https://www.al.pi.leg.br/",
  RJ: "https://www.alerj.rj.gov.br/",
  RN: "https://www.al.rn.leg.br/",
  RS: "https://www.al.rs.gov.br/",
  RO: "https://www.al.ro.leg.br/",
  RR: "https://al.rr.leg.br/",
  SC: "https://www.alesc.sc.gov.br/",
  SP: "https://www.al.sp.gov.br/",
  SE: "https://al.se.leg.br/",
  TO: "https://www.al.to.leg.br/",
};

/** Ministério Público do estado (MPDFT no DF). AL, AP e SP conferidos em 08/11/2026 (o site do MPSP recusa
 * robôs, mas o domínio é o oficial e o link é para o cidadão abrir). */
export const MINISTERIO_PUBLICO_POR_UF: Record<string, string | null> = {
  AC: "https://www.mpac.mp.br/",
  AL: "https://www.mpal.mp.br/",
  AP: "https://www.mpap.mp.br/",
  AM: "https://www.mpam.mp.br/",
  BA: "https://www.mpba.mp.br/",
  CE: "https://mpce.mp.br/",
  DF: "https://www.mpdft.mp.br/portal/",
  ES: "https://mpes.mp.br/",
  GO: "https://www.mpgo.mp.br/portal/",
  MA: "https://www.mpma.mp.br/",
  MT: "https://www.mpmt.mp.br/",
  MS: "https://www.mpms.mp.br/",
  MG: "https://www.mpmg.mp.br/portal/",
  PA: "https://www.mppa.mp.br/",
  PB: "https://www.mppb.mp.br/",
  PR: "https://mppr.mp.br/",
  PE: "https://portal.mppe.mp.br/",
  PI: "https://www.mppi.mp.br/internet/",
  RJ: "https://www.mprj.mp.br/",
  RN: "https://www.mprn.mp.br/",
  RS: "https://www.mprs.mp.br/",
  RO: "https://www.mpro.mp.br/",
  RR: "https://www.mprr.mp.br/",
  SC: "https://www.mpsc.mp.br/",
  SP: "https://www.mpsp.mp.br/",
  SE: "https://www.mpse.mp.br/",
  TO: "https://www.mpto.mp.br/portal/",
};

/** Tribunal de Contas do estado (do DF no DF). AL e AM conferidos em 08/11/2026 (o TCE-AM mudou de
 * tce.am.gov.br para tceam.tc.br). */
export const TRIBUNAL_DE_CONTAS_POR_UF: Record<string, string | null> = {
  AC: "https://tceac.tc.br/site/",
  AL: "https://www.tceal.tc.br/",
  AP: "https://www.tce.ap.gov.br/",
  AM: "https://www.tceam.tc.br/",
  BA: "https://www.tce.ba.gov.br/",
  CE: "https://www.tce.ce.gov.br/",
  DF: "https://www2.tc.df.gov.br/",
  ES: "https://www.tcees.tc.br/",
  GO: "https://portal.tce.go.gov.br/",
  MA: "https://www.tcema.tc.br/",
  MT: "https://www.tce.mt.gov.br/",
  MS: "https://www.tce.ms.gov.br/",
  MG: "https://www.tce.mg.gov.br/",
  PA: "https://www.tcepa.tc.br/",
  PB: "https://tce.pb.gov.br/",
  PR: "https://www1.tce.pr.gov.br/",
  PE: "https://www.tcepe.tc.br/internet/",
  PI: "https://www.tcepi.tc.br/",
  RJ: "https://www.tcerj.tc.br/portalnovo/",
  RN: "https://www.tce.rn.gov.br/",
  RS: "https://www.tce.rs.gov.br/",
  RO: "https://tcero.tc.br/",
  RR: "https://www.tcerr.tc.br/",
  SC: "https://www.tcesc.tc.br/",
  SP: "https://www.tce.sp.gov.br/",
  SE: "https://www.tce.se.gov.br/SitePages/home.aspx",
  TO: "https://www.tceto.tc.br/",
};

// Na Bahia, em Goiás e no Pará, as contas das prefeituras ficam com um tribunal próprio dos municípios.
const UFS_COM_TRIBUNAL_DOS_MUNICIPIOS = new Set(["BA", "GO", "PA"]);

function normalizarUf(uf?: string | null): string {
  return (uf ?? "").trim().toUpperCase();
}

function urlDaUf(mapa: Record<string, string | null>, uf: string): string | null {
  return mapa[uf] ?? null;
}

const MP_FAZ =
  "Recebe denúncia e representação sobre o uso de dinheiro público e pode abrir investigação.";

function ministerioPublicoEstadual(uf: string): CanalCobranca {
  return {
    id: "mp-estadual",
    nome: uf === "DF" ? "Ministério Público do Distrito Federal (MPDFT)" : "Ministério Público do estado",
    oQueFaz: MP_FAZ,
    url: urlDaUf(MINISTERIO_PUBLICO_POR_UF, uf),
  };
}

function tribunalDeContasEstadual(uf: string, municipal: boolean): CanalCobranca {
  const tribunalDosMunicipios = municipal && UFS_COM_TRIBUNAL_DOS_MUNICIPIOS.has(uf);
  return {
    id: "tce",
    nome: uf === "DF" ? "Tribunal de Contas do Distrito Federal" : "Tribunal de Contas do estado",
    oQueFaz: tribunalDosMunicipios
      ? "Fiscaliza as contas do governo do estado. As contas das prefeituras desta UF ficam com o Tribunal de Contas dos Municípios."
      : municipal
        ? "Fiscaliza as contas das prefeituras e câmaras do estado e recebe denúncia."
        : "Fiscaliza as contas do governo do estado e da Assembleia e recebe denúncia.",
    url: urlDaUf(TRIBUNAL_DE_CONTAS_POR_UF, uf),
  };
}

function umCanalDaCidade(canais: CanalCidade[] | undefined, tipo: string): string | null {
  return canais?.find((c) => c.tipo === tipo)?.url ?? null;
}

export function ouvidoriaFederal(casa: CasaFederal): CanalCobranca {
  return casa === "senado"
    ? {
        id: "casa",
        nome: "Ouvidoria do Senado Federal",
        oQueFaz: "Recebe elogio, pedido de informação, sugestão e reclamação sobre o Senado.",
        url: OUVIDORIA_SENADO,
      }
    : {
        id: "casa",
        nome: "Fale Conosco da Câmara dos Deputados",
        oQueFaz: "Recebe dúvida, pedido de informação, sugestão e reclamação sobre a Câmara e seus deputados.",
        url: FALE_CONOSCO_CAMARA,
      };
}

export const TCU: CanalCobranca = {
  id: "tcu",
  nome: "Ouvidoria do Tribunal de Contas da União (TCU)",
  oQueFaz: "Recebe denúncia sobre o uso de dinheiro público federal.",
  url: OUVIDORIA_TCU,
};

/**
 * Canais para a esfera do cargo.
 * - federal: ouvidoria da Câmara ou do Senado, Fala.BR (CGU), Ministério Público Federal e TCU;
 * - estadual: Assembleia, Ministério Público e Tribunal de Contas do estado;
 * - municipal: câmara e prefeitura da cidade (quando o catálogo tem o site), Ministério Público
 *   e Tribunal de Contas do estado.
 */
export function canaisParaCobrar(entrada: {
  esfera: Esfera;
  uf?: string | null;
  /** Casa do parlamentar federal (padrão: Câmara). */
  casa?: CasaFederal;
  /** Sites da cidade já catalogados; só usados na esfera municipal. */
  canaisCidade?: CanalCidade[];
}): CanalCobranca[] {
  const uf = normalizarUf(entrada.uf);
  if (entrada.esfera === "federal") {
    return [
      ouvidoriaFederal(entrada.casa ?? "camara"),
      {
        id: "falabr",
        nome: "Fala.BR (Controladoria-Geral da União)",
        oQueFaz: "Plataforma para pedir informação pública (Lei de Acesso à Informação) e registrar denúncia ou reclamação.",
        url: FALA_BR,
      },
      {
        id: "mpf",
        nome: "Ministério Público Federal",
        oQueFaz: MP_FAZ,
        url: MPF,
      },
      TCU,
    ];
  }
  if (entrada.esfera === "estadual") {
    return [
      {
        id: "casa",
        nome: uf === "DF" ? "Ouvidoria da Câmara Legislativa" : "Ouvidoria da Assembleia Legislativa",
        oQueFaz: "Recebe dúvida, pedido de informação e reclamação sobre a Casa e seus deputados. O endereço leva ao site da Casa.",
        url: urlDaUf(ASSEMBLEIA_POR_UF, uf),
      },
      ministerioPublicoEstadual(uf),
      tribunalDeContasEstadual(uf, false),
    ];
  }
  const camara = umCanalDaCidade(entrada.canaisCidade, "camara");
  const prefeitura = umCanalDaCidade(entrada.canaisCidade, "prefeitura");
  const canais: CanalCobranca[] = [];
  if (camara) {
    canais.push({
      id: "camara-municipal",
      nome: "Ouvidoria da câmara municipal",
      oQueFaz: "Recebe dúvida, pedido de informação e reclamação sobre a câmara e os vereadores. O endereço leva ao site da câmara.",
      url: camara,
    });
  }
  if (prefeitura) {
    canais.push({
      id: "prefeitura",
      nome: "Ouvidoria da prefeitura",
      oQueFaz: "Recebe dúvida, pedido de informação e reclamação sobre a prefeitura. O endereço leva ao site da prefeitura.",
      url: prefeitura,
    });
  }
  canais.push(ministerioPublicoEstadual(uf), tribunalDeContasEstadual(uf, true));
  return canais;
}

export type TemaCobranca = "gastos" | "votos" | "presenca" | "projetos";

export type LinhaCobranca = {
  pergunta: string;
  links: { rotulo: string; href: string; externo: boolean }[];
};

const LINK_TODOS = { rotulo: "Ver todos os canais", href: "#ver-como-cobrar", externo: false };

function comoLink(c: CanalCobranca | undefined, rotulo: string): LinhaCobranca["links"] {
  return c?.url ? [{ rotulo, href: c.url, externo: true }] : [];
}

/**
 * Uma linha curta para o fim da gaveta de cada seção: o canal mais ligado àquele dado.
 * Sempre termina com o atalho para a lista completa na aba Ficha.
 */
export function linhaDeCobranca(entrada: {
  tema: TemaCobranca;
  esfera: Esfera;
  uf?: string | null;
  casa?: CasaFederal;
}): LinhaCobranca {
  const { tema, esfera } = entrada;
  const canais = canaisParaCobrar({ esfera, uf: entrada.uf, casa: entrada.casa });
  const casa = canais.find((c) => c.id === "casa");
  const controle = esfera === "federal" ? TCU : canais.find((c) => c.id === "tce");
  const rotuloCasa =
    esfera !== "federal" ? "Ouvidoria da Casa" : entrada.casa === "senado" ? "Ouvidoria do Senado" : "Fale Conosco da Câmara";

  if (tema === "gastos") {
    return {
      pergunta: "Dúvida sobre um gasto?",
      links: [
        ...comoLink(casa, rotuloCasa),
        ...comoLink(controle, esfera === "federal" ? "Ouvidoria do TCU" : "Tribunal de Contas do estado"),
        LINK_TODOS,
      ],
    };
  }
  if (tema === "projetos") {
    const site =
      esfera === "federal"
        ? entrada.casa === "senado"
          ? "https://www12.senado.leg.br/hpsenado"
          : "https://www.camara.leg.br/"
        : null;
    return {
      pergunta: "Quer acompanhar ou comentar o projeto?",
      links: [...(site ? [{ rotulo: "Site da Casa", href: site, externo: true }] : []), LINK_TODOS],
    };
  }
  return {
    pergunta: tema === "votos" ? "Quer falar sobre um voto?" : "Quer falar sobre a presença nas votações?",
    links: [{ rotulo: "Fale com o gabinete", href: "#ver-como-cobrar", externo: false }],
  };
}
