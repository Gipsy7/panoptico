import type { Metadata } from "next";

import { PainelAcessos } from "@/components/painel-acessos";

// Área privada do dono: fora dos buscadores, fora do menu, do rodapé e do mapa do site. A página
// não traz dado nenhum na renderização (ela fica em cache na borda); tudo vem do navegador, depois
// do login.
export const metadata: Metadata = {
  title: "Painel de acessos",
  robots: { index: false, follow: false },
};

export default function PainelPage() {
  return <PainelAcessos />;
}
