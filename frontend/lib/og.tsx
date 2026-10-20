import { ImageResponse } from "next/og";
import type { ReactNode } from "react";

import { formatarData } from "@/lib/formato";
import {
  COR_MARCA,
  COR_MARCA_NOME,
  COR_PAPEL,
  COR_SUAVE,
  COR_TINTA,
  LINHAS_MARCA,
} from "@/lib/marca-svg";
import {
  CAMINHO_NOME,
  CAMINHO_SOCIAL,
  LOGO_ALTURA,
  LOGO_LARGURA,
  LOGO_SOL,
  LOGO_VIEWBOX,
} from "@/lib/logo-caminhos";

// Cartões de prévia para compartilhar (WhatsApp, redes). Paleta clara fixa: a imagem
// não segue o modo escuro. O gerador não lê CSS, então as cores vêm de lib/marca-svg.ts.

export const TAMANHO = { width: 1200, height: 630 };
export const COR = {
  fundo: COR_PAPEL,
  texto: COR_TINTA,
  suave: COR_SUAVE,
  primaria: COR_MARCA,
  cartao: "#f8f6f0",
  borda: "#d9d3c7",
};

/** Logo completa (sol, nome e .social) com as cores fixas da paleta clara. */
function LogoCompleta({ altura }: { altura: number }) {
  return (
    <svg
      width={Math.round((LOGO_LARGURA * altura) / LOGO_ALTURA)}
      height={altura}
      viewBox={LOGO_VIEWBOX}
    >
      <path d={CAMINHO_NOME} fill={COR_MARCA_NOME} />
      <path d={CAMINHO_SOCIAL} fill={COR_MARCA} />
      <g
        transform={`translate(${LOGO_SOL.cx} ${LOGO_SOL.cy}) scale(${LOGO_SOL.escala}) translate(-32 -32)`}
        fill="none"
        stroke={COR_MARCA}
        strokeLinecap="round"
        strokeWidth={2.6}
      >
        {LINHAS_MARCA.map((l, i) => (
          <line key={i} {...l} />
        ))}
        <circle cx={32} cy={32} r={7.5} strokeWidth={2.1} />
      </g>
    </svg>
  );
}

/** "Fonte: TSE · atualizado em 10/10/2026" (sem a data quando a fonte não a tem). */
export function rodapeFonte(
  fonte: string,
  atualizadoEm?: string | null,
): string {
  return `Fonte: ${fonte}${atualizadoEm ? ` · atualizado em ${formatarData(atualizadoEm)}` : ""}`;
}

/** Corta com reticências para o texto caber. */
export function cortar(texto: string, max: number): string {
  return texto.length > max ? `${texto.slice(0, max - 1)}…` : texto;
}

export function imagemPadrao() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: COR.fundo,
        color: COR.primaria,
        fontSize: 72,
        fontWeight: 700,
      }}
    >
      <LogoCompleta altura={120} />
    </div>,
    TAMANHO,
  );
}

/**
 * Moldura comum: conteúdo no topo/centro, frase de destaque opcional e o rodapé com a marca.
 * `rodape` leva a fonte e a data; sem ele, aparece o lema do site.
 */
export function moldura(
  centro: ReactNode,
  destaque: string | null,
  fonteDestaque = 40,
  rodape?: string,
) {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: COR.fundo,
        color: COR.texto,
        padding: 64,
      }}
    >
      {centro}
      {destaque && (
        <div
          style={{
            fontSize: fonteDestaque,
            textAlign: "center",
            display: "flex",
            justifyContent: "center",
          }}
        >
          {destaque}
        </div>
      )}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: 26,
        }}
      >
        <LogoCompleta altura={44} />
        <div
          style={{
            color: COR.suave,
            fontSize: rodape && rodape.length > 48 ? 22 : 26,
            display: "flex",
            whiteSpace: "nowrap",
          }}
        >
          {rodape ?? "Quem te representa, às claras · dados oficiais"}
        </div>
      </div>
    </div>,
    TAMANHO,
  );
}

export type NumeroOg = { rotulo: string; valor: string };

/** Cabeçalho com foto (opcional), nome e uma linha de contexto, mais cartões de número. */
export function cartaoPessoa({
  foto,
  nome,
  contexto,
  numeros,
  rodape,
}: {
  foto?: string | null;
  nome: string;
  contexto: string;
  numeros: NumeroOg[];
  rodape: string;
}) {
  return moldura(
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        justifyContent: "space-between",
        paddingBottom: 32,
      }}
    >
      <div style={{ display: "flex", gap: 48, alignItems: "center" }}>
        {foto && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={foto}
            alt=""
            width={180}
            height={240}
            style={{ borderRadius: 24, objectFit: "cover" }}
          />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 64, fontWeight: 700 }}>
            {cortar(nome, 28)}
          </div>
          <div style={{ fontSize: 34, color: COR.suave }}>
            {cortar(contexto, 60)}
          </div>
        </div>
      </div>
      <CartoesNumero numeros={numeros} />
    </div>,
    null,
    40,
    rodape,
  );
}

export function CartoesNumero({ numeros }: { numeros: NumeroOg[] }) {
  return (
    <div style={{ display: "flex", gap: 24 }}>
      {numeros.map((n) => (
        <div
          key={n.rotulo}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            background: COR.cartao,
            border: `2px solid ${COR.borda}`,
            borderRadius: 24,
            padding: 28,
          }}
        >
          <div style={{ fontSize: 24, color: COR.suave }}>{n.rotulo}</div>
          <div style={{ fontSize: 40, fontWeight: 700 }}>{n.valor}</div>
        </div>
      ))}
    </div>
  );
}
