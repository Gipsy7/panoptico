import { readFile } from "node:fs/promises";
import path from "node:path";

import { ImageResponse } from "next/og";

import { type DadosCartao, type FormatoCartao, type NumeroCartao, quebrarNome } from "@/lib/cartao";
import { LINHAS_MARCA } from "@/lib/marca-svg";

// Cartão do perfil para compartilhar (Feed 1080x1080 e Stories 1080x1920): pôster escuro
// com a foto oficial em tom bronze. As cores são os tokens da marca (lib/marca-svg.ts e
// globals.css): tinta, papel, bronze. Sem cor de "bom" ou "ruim".

const TINTA = "#141414";
const PAPEL = "#f4f1ea";
const BRONZE_CLARO = "#c9954a";
const BRONZE_ESCURO = "#7a5a32";
const CINZA = "#6e6a63";
const CINZA_CLARO = "#a39d92";
const AREIA = "#c4a77d";

export const TAMANHOS: Record<FormatoCartao, { width: number; height: number }> = {
  feed: { width: 1080, height: 1080 },
  stories: { width: 1080, height: 1920 },
};

/** Geist (a mesma fonte do site) em dois pesos; o Satori não lê woff2, por isso o .ttf do projeto. */
async function fontes() {
  const dir = path.join(process.cwd(), "assets", "fonts");
  const [medio, preto] = await Promise.all([
    readFile(path.join(dir, "Geist-Medium.ttf")),
    readFile(path.join(dir, "Geist-Black.ttf")),
  ]);
  return [
    { name: "Geist", data: medio, weight: 500 as const, style: "normal" as const },
    { name: "Geist", data: preto, weight: 900 as const, style: "normal" as const },
  ];
}

// Cinza (luminância) multiplicado pelo bronze claro: branco vira bronze, preto fica preto.
const DUOTOM: [[number, number, number], [number, number, number], [number, number, number]] = [
  [0.299, 0.587, 0.114],
  [0.299, 0.587, 0.114],
  [0.299, 0.587, 0.114],
].map((linha, i) => linha.map((v) => v * [201 / 255, 149 / 255, 74 / 255][i])) as [
  [number, number, number],
  [number, number, number],
  [number, number, number],
];

function ehWebp(b: Buffer) {
  return b.length > 12 && b.toString("ascii", 0, 4) === "RIFF" && b.toString("ascii", 8, 12) === "WEBP";
}

/**
 * Baixa a foto oficial e a devolve como data URL, em tom bronze quando o `sharp` está
 * disponível (o gerador de imagens não tem filtro de cor). Sem `sharp`, a foto vai natural
 * (jpeg/png); webp sem `sharp` vira silhueta. Qualquer falha devolve null (silhueta).
 */
export async function prepararFoto(url: string | null, largura: number, altura: number): Promise<string | null> {
  if (!url) return null;
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(6000) });
    if (!r.ok) return null;
    const bruto = Buffer.from(await r.arrayBuffer());
    try {
      const sharp = (await import("sharp")).default;
      const saida = await sharp(bruto)
        .resize(largura, altura, { fit: "cover", position: "north" })
        .linear(1.2, -20)
        .recomb(DUOTOM)
        .jpeg({ quality: 86 })
        .toBuffer();
      return `data:image/jpeg;base64,${saida.toString("base64")}`;
    } catch {
      if (ehWebp(bruto)) return null;
      const tipo = r.headers.get("content-type")?.split(";")[0] || "image/jpeg";
      return `data:${tipo};base64,${bruto.toString("base64")}`;
    }
  } catch {
    return null;
  }
}

function Marca({ tam, cor }: { tam: number; cor: string }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 64 64" fill="none">
      <g stroke={cor} strokeWidth={3.4} strokeLinecap="round">
        {LINHAS_MARCA.map((l, i) => (
          <line key={i} {...l} />
        ))}
        <circle cx={32} cy={32} r={8} />
      </g>
    </svg>
  );
}

function Silhueta({ largura, altura }: { largura: number; altura: number }) {
  return (
    <div style={{ display: "flex", width: largura, height: altura, background: AREIA, alignItems: "flex-end" }}>
      <svg width={largura} height={Math.round(largura * 0.9)} viewBox="0 0 100 90">
        <circle cx="50" cy="32" r="19" fill={CINZA} />
        <path d="M10 92C10 62 28 52 50 52S90 62 90 92Z" fill={CINZA} />
      </svg>
    </div>
  );
}

/** Tamanho que cabe: números curtos ("112") grandes, textos longos ("R$ 312 mil") menores. */
export function tamanhoGrande(valor: string, maximo: number, largura: number): number {
  return Math.max(34, Math.min(maximo, Math.floor(largura / (valor.length * 0.62))));
}

function ColunaFaixa({ n, s }: { n: NumeroCartao; s: boolean }) {
  const tamanho = tamanhoGrande(n.valor, s ? 78 : 56, s ? 286 : 290);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        borderTop: `6px solid ${TINTA}`,
        paddingTop: 12,
        minWidth: 0,
      }}
    >
      <div style={{ display: "flex", fontSize: s ? 30 : 24, lineHeight: 1.15, minHeight: s ? 70 : 56, fontWeight: 500 }}>
        {n.rotulo}
      </div>
      <div style={{ display: "flex", fontSize: tamanho, fontWeight: 900, lineHeight: 1, marginTop: 6, letterSpacing: -1 }}>
        {n.valor}
      </div>
      {n.media && (
        <div style={{ display: "flex", fontSize: s ? 30 : 24, marginTop: 8, color: CINZA, fontWeight: 500, lineHeight: 1.15 }}>
          {n.media}
        </div>
      )}
      {!n.media && n.nota && (
        <div style={{ display: "flex", fontSize: s ? 30 : 24, marginTop: 8, color: CINZA, fontWeight: 500, lineHeight: 1.15 }}>
          {n.nota}
        </div>
      )}
    </div>
  );
}

function Cartao({ d, formato, foto }: { d: DadosCartao; formato: FormatoCartao; foto: string | null }) {
  const s = formato === "stories";
  const { width, height } = TAMANHOS[formato];
  const fotoL = s ? width : 470;
  const fotoA = s ? 960 : 720;
  const linhas = quebrarNome(d.nome.toUpperCase());
  const maisLonga = Math.max(...linhas.map((l) => l.length));
  const tamNome = Math.max(
    s ? 72 : 52,
    Math.min(s ? 112 : 84, Math.floor((s ? 900 : 600) / (maisLonga * 0.66))),
  );
  const p = d.principal;
  const duas = linhas.length > 1;
  const grande = p ? tamanhoGrande(p.valor, s ? 236 : duas ? 180 : 236, s ? 900 : 560) : 0;

  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        width,
        height,
        background: TINTA,
        color: PAPEL,
        fontFamily: "Geist",
        fontWeight: 500,
      }}
    >
      {/* Foto sangrando: no Feed na metade direita; nos Stories em toda a largura, no topo. */}
      <div style={{ position: "absolute", top: 0, right: 0, display: "flex", width: fotoL, height: fotoA }}>
        {foto ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={foto} alt="" width={fotoL} height={fotoA} style={{ objectFit: "cover" }} />
        ) : (
          <Silhueta largura={fotoL} altura={fotoA} />
        )}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: fotoL,
            height: fotoA,
            display: "flex",
            backgroundImage: s
              ? `linear-gradient(0deg, ${TINTA} 0%, ${TINTA} 24%, rgba(20,20,20,0) 72%)`
              : `linear-gradient(90deg, ${TINTA} 0%, rgba(20,20,20,0) 38%), linear-gradient(0deg, ${TINTA} 0%, rgba(20,20,20,0) 24%)`,
          }}
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", padding: s ? "250px 72px 0" : "56px 64px 0", position: "relative" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            fontSize: s ? 46 : 40,
            fontWeight: 900,
            alignSelf: "flex-start",
            background: s ? TINTA : "transparent",
            padding: s ? "12px 26px 12px 18px" : 0,
          }}
        >
          <Marca tam={s ? 56 : 48} cor={BRONZE_CLARO} />
          Panóptico
        </div>
        <div
          style={{
            display: "flex",
            marginTop: s ? 286 : 44,
            fontSize: s ? 34 : 28,
            letterSpacing: 4,
            textTransform: "uppercase",
            color: BRONZE_CLARO,
            fontWeight: 900,
          }}
        >
          {d.contexto}
        </div>
        <div style={{ display: "flex", flexDirection: "column", marginTop: 10, fontSize: tamNome, lineHeight: 0.94, fontWeight: 900 }}>
          {linhas.map((l) => (
            <div key={l} style={{ display: "flex" }}>
              {l}
            </div>
          ))}
        </div>

        {p ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <div
              style={{
                display: "flex",
                marginTop: s ? 28 : 30,
                fontSize: s ? 36 : 30,
                textTransform: "uppercase",
                letterSpacing: 3,
                fontWeight: 900,
              }}
            >
              {p.rotulo}
            </div>
            <div style={{ display: "flex", fontSize: grande, lineHeight: 0.88, fontWeight: 900, color: BRONZE_CLARO, letterSpacing: -4, marginTop: 6 }}>
              {p.valor}
            </div>
            {p.complemento && (
              <div style={{ display: "flex", fontSize: s ? 46 : 38, marginTop: 10 }}>{p.complemento}</div>
            )}
            {p.media && (
              <div
                style={{
                  display: "flex",
                  marginTop: 18,
                  background: PAPEL,
                  color: TINTA,
                  fontSize: s ? 40 : 32,
                  padding: s ? "14px 24px" : "10px 20px",
                  fontWeight: 900,
                }}
              >
                {p.media}
              </div>
            )}
            {!p.media && p.nota && (
              <div style={{ display: "flex", fontSize: s ? 38 : 30, marginTop: 14, color: CINZA_CLARO }}>{p.nota}</div>
            )}
          </div>
        ) : (
          <div style={{ display: "flex", marginTop: 36, fontSize: s ? 56 : 44, lineHeight: 1.15, maxWidth: s ? 900 : 640 }}>
            {d.frase}
          </div>
        )}
      </div>

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          display: "flex",
          flexDirection: "column",
          background: PAPEL,
          color: TINTA,
          padding: s ? "40px 72px 250px" : "30px 64px 28px",
        }}
      >
        {d.outros.length > 0 && (
          <div style={{ display: "flex", gap: 28 }}>
            {d.outros.map((n) => (
              <ColunaFaixa key={n.rotulo} n={n} s={s} />
            ))}
          </div>
        )}
        <div
          style={{
            display: "flex",
            flexDirection: s ? "column" : "row",
            justifyContent: "space-between",
            gap: s ? 6 : 20,
            alignItems: s ? "flex-start" : "baseline",
            marginTop: d.outros.length > 0 ? 22 : 0,
            paddingTop: d.outros.length > 0 ? 14 : 0,
            borderTop: d.outros.length > 0 ? `2px solid ${CINZA_CLARO}` : "none",
            fontSize: s ? 28 : 22,
            color: CINZA,
          }}
        >
          <div style={{ display: "flex", flex: 1, minWidth: 0 }}>{d.fonte}</div>
          <div style={{ display: "flex", flexShrink: 0, color: BRONZE_ESCURO, fontSize: s ? 34 : 28, fontWeight: 900 }}>
            panoptico.social.br
          </div>
        </div>
      </div>
    </div>
  );
}

/** Imagem pronta, com cache de uma hora na CDN e o navegador revalidando. */
export async function cartaoImagem(d: DadosCartao, formato: FormatoCartao) {
  const tamanho = TAMANHOS[formato];
  const s = formato === "stories";
  const foto = await prepararFoto(d.foto, s ? 1080 : 470, s ? 960 : 720);
  return new ImageResponse(<Cartao d={d} formato={formato} foto={foto} />, {
    ...tamanho,
    fonts: await fontes(),
    headers: { "Cache-Control": "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400" },
  });
}

export function cartaoNaoEncontrado() {
  return new Response("Perfil não encontrado.", { status: 404, headers: { "Cache-Control": "public, s-maxage=60" } });
}
