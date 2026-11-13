import type { Metadata } from "next";

import { AvisoErro } from "@/components/aviso-erro";

export const metadata: Metadata = { title: "Votação não encontrada" };

export default function NotFound() {
  return (
    <AvisoErro
      principal
      titulo="Votação não encontrada"
      mensagem="O endereço pode estar errado, ou esta votação não está entre as que acompanhamos. Procure pelo número do projeto ou por uma palavra do assunto."
      acao={{ href: "/projetos", rotulo: "Buscar projetos e votações" }}
    />
  );
}
