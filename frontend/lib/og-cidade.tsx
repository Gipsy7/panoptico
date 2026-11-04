import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

import {
  type Contagem,
  type Esfera,
  type FormatoCartao,
  FORMATOS,
  ROTULO_FOTO,
} from "@/lib/cartao-cidade";
import { LINHAS_MARCA } from "@/lib/marca-svg";

// Cartão "Quem decide por [cidade]" (versão A, mosaico de rostos). Imagem fixa em tema escuro,
// igual nos dois temas do site; as cores vêm dos tokens da marca (lib/marca-svg e globals.css).

const TINTA = "#141414"; // --foreground
const PAPEL = "#f4f1ea"; // --background
const BRONZE_CL = "#c9954a"; // bronze claro (versão escura da marca)
const AREIA = "#c4a77d";
const TERRA = "#8f7650";
const CINZA = "#6e6a63"; // --muted-foreground
const CINZA_CL = "#a39d92";

export type TileCartao = { chave: string; esfera: Esfera; foto: string | null };

export type DadosCartao = {
  formato: FormatoCartao;
  cidade: string;
  uf: string;
  ibge: string;
  total: number;
  contagens: Contagem[];
  mosaico: TileCartao[];
  /** "Câmara, Senado e TSE". */
  fontes: string;
  /** Data já formatada (dd/mm/aaaa) ou nulo. */
  atualizadoEm: string | null;
  /** "Dado não publicado: vereadores." ou nulo. */
  fora: string | null;
};

function Sol({ tamanho }: { tamanho: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64">
      <g fill="none" stroke={BRONZE_CL} strokeLinecap="round" strokeWidth={3.4}>
        {LINHAS_MARCA.map((l, i) => (
          <line key={i} {...l} />
        ))}
        <circle cx={32} cy={32} r={8} />
      </g>
    </svg>
  );
}

function Silhueta({ lado }: { lado: number }) {
  return (
    <svg width={lado} height={lado} viewBox="0 0 100 100">
      <circle cx={50} cy={40} r={19} fill={AREIA} />
      <path d="M12 104C12 74 30 63 50 63S88 74 88 104Z" fill={AREIA} />
    </svg>
  );
}

function Tile({ t, largura, altura, fonteRotulo }: { t: TileCartao; largura: number; altura: number; fonteRotulo: number }) {
  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        width: largura,
        height: altura,
        background: t.foto ? BRONZE_CL : TERRA,
        overflow: "hidden",
        alignItems: "flex-end",
        justifyContent: "center",
      }}
    >
      {t.foto ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={t.foto}
          alt=""
          width={largura}
          height={altura}
          style={{ position: "absolute", top: 0, left: 0, objectFit: "cover", objectPosition: "50% 18%", filter: "grayscale(1) contrast(1.15)" }}
        />
      ) : (
        <div style={{ display: "flex", position: "absolute", bottom: 0, left: 0, width: largura, justifyContent: "center" }}>
          <Silhueta lado={Math.round(altura * 0.8)} />
        </div>
      )}
      {t.foto && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: largura,
            height: altura,
            display: "flex",
            background: "rgba(201,149,74,0.42)",
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          left: 0,
          bottom: 0,
          width: largura,
          height: Math.round(altura * 0.34),
          display: "flex",
          background: "linear-gradient(0deg, rgba(20,20,20,0.9), rgba(20,20,20,0))",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 12,
          bottom: 12,
          display: "flex",
          background: TINTA,
          color: PAPEL,
          fontSize: fonteRotulo,
          fontWeight: 700,
          padding: "4px 10px",
        }}
      >
        {ROTULO_FOTO[t.esfera]}
      </div>
    </div>
  );
}

/** Tamanho do nome da cidade para caber em uma ou duas linhas na largura útil. */
function fonteNome(nome: string, base: number, largura: number): number {
  // Caixa alta pesada: cerca de 0,66 em de largura por letra.
  const cabe = Math.floor(largura / (0.66 * base));
  if (nome.length <= cabe) return base;
  return Math.max(54, Math.floor(largura / (0.66 * nome.length)));
}

// Geist (a fonte do site) em TTF: o gerador de imagem não lê woff2. Licença em lib/fontes/OFL.txt.
let fontes: Promise<{ name: string; data: ArrayBuffer; weight: 400 | 700; style: "normal" }[]> | null = null;
function carregarFontes() {
  fontes ??= Promise.all(
    ([["Geist-Regular.ttf", 400], ["Geist-Bold.ttf", 700]] as const).map(async ([arquivo, weight]) => ({
      name: "Geist",
      data: await readFile(join(process.cwd(), "lib", "fontes", arquivo)).then((b) => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer),
      weight,
      style: "normal" as const,
    })),
  );
  return fontes;
}

export async function cartaoCidade(d: DadosCartao): Promise<ImageResponse> {
  const { width, height } = FORMATOS[d.formato];
  const stories = d.formato === "stories";
  const margem = stories ? 72 : 60;
  const gap = 6;
  const colunas = 3;
  const linhas = Math.max(1, Math.ceil(d.mosaico.length / colunas));
  const larguraTile = Math.floor((width - gap * (colunas - 1)) / colunas);
  const alturaTile = stories ? 240 : linhas === 1 ? 300 : 262;
  const nome = d.cidade.toUpperCase();
  const tamNome = stories ? fonteNome(nome, 140, width - margem * 2) : fonteNome(nome, 104, width - margem * 2 - 330);
  const tamNumero = stories ? 270 : 270;
  const rodape = `Fonte: ${d.fontes}${d.atualizadoEm ? ` · atualizado em ${d.atualizadoEm}` : ""}`;
  const link = `panoptico.social.br/cidade/${d.ibge}`;

  const mosaico = (
    <div style={{ display: "flex", flexWrap: "wrap", gap, width, position: "relative", marginTop: stories ? 250 : 0 }}>
      {d.mosaico.map((t) => (
        <Tile key={t.chave} t={t} largura={larguraTile} altura={alturaTile} fonteRotulo={stories ? 28 : 22} />
      ))}
      <div
        style={{
          position: "absolute",
          top: stories ? -170 : 40,
          ...(stories ? { left: 72 } : { left: 48 }),
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: TINTA,
          color: PAPEL,
          padding: "12px 22px 12px 14px",
          fontSize: stories ? 46 : 36,
          fontWeight: 700,
        }}
      >
        <Sol tamanho={stories ? 54 : 44} />
        Panóptico
      </div>
    </div>
  );

  const intro = (
    <div style={{ display: "flex", fontSize: stories ? 46 : 38, fontWeight: 400, lineHeight: 1.1 }}>
      {d.total === 1 ? "pessoa eleita decide por" : "pessoas eleitas decidem por"}
    </div>
  );
  const nomeEl = (
    <div
      style={{
        display: "flex",
        fontSize: tamNome,
        fontWeight: 700,
        lineHeight: 0.95,
        letterSpacing: "-0.02em",
        maxWidth: stories ? width - margem * 2 : width - margem * 2 - 330,
      }}
    >
      {nome}
      <span style={{ fontSize: Math.round(tamNome * 0.36), color: CINZA_CL, marginLeft: 16, alignSelf: "flex-end", paddingBottom: 6 }}>{d.uf}</span>
    </div>
  );

  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: TINTA,
        color: PAPEL,
      }}
    >
      {mosaico}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
          padding: `0 ${margem}px`,
          marginTop: stories ? 30 : 26,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-end", gap: 30 }}>
          <div
            style={{
              display: "flex",
              fontSize: tamNumero,
              fontWeight: 700,
              lineHeight: 0.82,
              color: BRONZE_CL,
              letterSpacing: "-0.05em",
            }}
          >
            {d.total.toLocaleString("pt-BR")}
          </div>
          {stories ? (
            <div style={{ display: "flex", paddingBottom: 6, maxWidth: 420 }}>{intro}</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingBottom: 6 }}>
              {intro}
              {nomeEl}
            </div>
          )}
        </div>
        {stories && nomeEl}
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: stories ? 14 : 10,
          padding: `0 ${margem}px`,
          marginTop: stories ? 30 : 22,
        }}
      >
        {d.contagens.map((c) => (
          <div
            key={c.esfera}
            style={{
              display: "flex",
              border: `2px solid ${CINZA}`,
              padding: stories ? "8px 18px" : "6px 14px",
              fontSize: stories ? 34 : 26,
              gap: 8,
            }}
          >
            <span style={{ color: BRONZE_CL, fontWeight: 700 }}>{c.n.toLocaleString("pt-BR")}</span>
            <span>{c.rotulo.replace(/^[\d.]+ /, "")}</span>
          </div>
        ))}
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          marginTop: "auto",
          padding: stories ? `20px ${margem}px 230px` : `0 ${margem}px 30px`,
          fontSize: stories ? 28 : 22,
          color: CINZA_CL,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ display: "flex" }}>{rodape}</div>
          {d.fora && <div style={{ display: "flex" }}>{d.fora}</div>}
        </div>
        <div style={{ display: "flex", color: PAPEL, fontSize: stories ? 34 : 26, fontWeight: 700 }}>{link}</div>
      </div>
    </div>,
    { width, height, fonts: await carregarFontes() },
  );
}
