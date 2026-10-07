/**
 * Geometria da marca para usos fora do React DOM (ícones e imagens de compartilhamento,
 * gerados com ImageResponse). Mesmos números do componente <Marca>.
 */
export const COR_MARCA = "#9c6a2a"; // --bronze
export const COR_PAPEL = "#f4f1ea"; // --background
export const COR_TINTA = "#141414"; // --foreground
export const COR_SUAVE = "#6e6a63"; // --muted-foreground

const r = (n: number) => Math.round(n * 100) / 100;

export const LINHAS_MARCA = Array.from({ length: 12 }, (_, i) => {
  const angulo = (i / 12) * 2 * Math.PI - Math.PI / 2;
  return {
    x1: r(32 + 28 * Math.cos(angulo)),
    y1: r(32 + 28 * Math.sin(angulo)),
    x2: r(32 + 15 * Math.cos(angulo)),
    y2: r(32 + 15 * Math.sin(angulo)),
  };
});
