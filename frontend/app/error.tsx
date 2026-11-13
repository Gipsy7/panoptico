"use client";

import { AvisoErro } from "@/components/aviso-erro";

/** Falha inesperada ao montar uma página: fala com a voz do site e deixa tentar de novo. */
export default function Erro({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <AvisoErro
      principal
      titulo="Esta página não abriu"
      mensagem="Algo deu errado do nosso lado ao montar esta página. Os dados continuam nas fontes oficiais; tente de novo em instantes."
      acao={{ href: "/", rotulo: "Voltar para o início" }}
    >
      <button type="button" onClick={reset} className="botao self-start">
        Tentar de novo
      </button>
    </AvisoErro>
  );
}
