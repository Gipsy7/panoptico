// Fotos oficiais embutidas nos cartões em imagem (cidade e votação). Só roda no servidor.

/** Baixa a foto e a embute (data URL); sem foto ou com erro, volta nulo (o cartão usa a silhueta). */
export async function embutirFoto(url: string | null | undefined): Promise<string | null> {
  if (!url) return null;
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!r.ok) return null;
    let tipo = (r.headers.get("content-type") ?? "").split(";")[0];
    if (!tipo.startsWith("image/")) return null;
    let bytes: Buffer = Buffer.from(await r.arrayBuffer());
    if (bytes.length === 0 || bytes.length > 3_000_000) return null;
    if (tipo === "image/webp") {
      // O gerador de imagem não lê WebP (as fotos do TSE são WebP): converte para JPEG.
      const { default: sharp } = await import("sharp");
      bytes = await sharp(bytes).resize({ width: 720, withoutEnlargement: true }).jpeg({ quality: 85 }).toBuffer();
      tipo = "image/jpeg";
    }
    return `data:${tipo};base64,${bytes.toString("base64")}`;
  } catch {
    return null;
  }
}
