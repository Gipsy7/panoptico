import type { Metadata } from "next";

import { AvisoErro } from "@/components/aviso-erro";

export const metadata: Metadata = { title: "Projeto não encontrado" };

export default function NotFound() {
  return (
    <AvisoErro
      principal
      titulo="Projeto não encontrado"
      mensagem="O endereço pode estar errado, ou este projeto não está entre os que acompanhamos. Procure pelo número (PL 2338/2023) ou por uma palavra do assunto."
      acao={{ href: "/projetos", rotulo: "Buscar projetos e votações" }}
    />
  );
}
