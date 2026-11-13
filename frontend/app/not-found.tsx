import type { Metadata } from "next";

import { AvisoErro } from "@/components/aviso-erro";

export const metadata: Metadata = { title: "Página não encontrada" };

export default function NotFound() {
  return (
    <AvisoErro
      principal
      titulo="Página não encontrada"
      mensagem="O endereço pode estar errado ou o que você procura não está na nossa base. Procure de novo pela cidade ou pelo nome."
      acao={{ href: "/", rotulo: "Procurar pela cidade ou pelo nome" }}
    />
  );
}
