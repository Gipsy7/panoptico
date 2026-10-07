import { ImageResponse } from "next/og";

import { COR_MARCA, COR_PAPEL, LINHAS_MARCA } from "@/lib/marca-svg";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
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
      <svg width={128} height={128} viewBox="0 0 64 64" fill="none" stroke={COR_MARCA} strokeLinecap="round">
        {LINHAS_MARCA.map((l, i) => (
          <line key={i} {...l} strokeWidth={3.2} />
        ))}
        <circle cx={32} cy={32} r={7.5} strokeWidth={2.6} />
      </svg>
    </div>,
    size,
  );
}
