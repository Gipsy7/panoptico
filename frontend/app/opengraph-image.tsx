import { COR, moldura } from "@/lib/og";

export const alt = "Panóptico: quem te representa, às claras";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Cartão da página inicial; vale também para as páginas que não têm imagem própria.
export default function Image() {
  return moldura(
    <div style={{ display: "flex", flexDirection: "column", gap: 32, paddingTop: 40 }}>
      <div style={{ display: "flex", fontSize: 74, fontWeight: 700 }}>
        Quem te representa, às claras
      </div>
      <div style={{ display: "flex", fontSize: 40, color: COR.suave, lineHeight: 1.3 }}>
        Do presidente ao vereador: o que cada um faz, gasta, vota e recebe.
      </div>
    </div>,
    "Digite o CEP. Dado oficial, com link da fonte e data.",
    36,
    "panoptico.social.br",
  );
}
