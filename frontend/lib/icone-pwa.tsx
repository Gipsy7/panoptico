import { ImageResponse } from "next/og";

import { COR_MARCA, COR_PAPEL, LINHAS_MARCA } from "@/lib/marca-svg";

/** Ícone quadrado da marca (mesmo desenho do apple-icon) para o manifest e para a notificação. */
export function iconePwa(lado: number) {
  const marca = Math.round(lado * 0.71);
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: COR_PAPEL,
      }}
    >
      <svg width={marca} height={marca} viewBox="0 0 64 64" fill="none" stroke={COR_MARCA} strokeLinecap="round">
        {LINHAS_MARCA.map((l, i) => (
          <line key={i} {...l} strokeWidth={3.2} />
        ))}
        <circle cx={32} cy={32} r={7.5} strokeWidth={2.6} />
      </svg>
    </div>,
    { width: lado, height: lado },
  );
}
