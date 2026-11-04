import type { NextRequest } from "next/server";

import { lerFormato } from "@/lib/cartao";
import { dadosFederal } from "@/lib/cartao-dados";
import { cartaoImagem, cartaoNaoEncontrado } from "@/lib/og-cartao";

// Cartão do perfil em imagem para compartilhar: ?formato=feed (1080x1080) ou stories (1080x1920).
export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const formato = lerFormato(request.nextUrl.searchParams.get("formato"));
  const dados = await dadosFederal(id);
  if (!dados) return cartaoNaoEncontrado();
  return cartaoImagem(dados, formato);
}
