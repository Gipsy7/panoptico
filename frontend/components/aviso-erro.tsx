import Link from "next/link";

export function AvisoErro({
  titulo,
  mensagem,
  principal = false,
  acao = { href: "/", rotulo: "Fazer outra busca" },
  children,
}: {
  titulo: string;
  mensagem: string;
  /** O aviso é a página inteira (não encontrada, erro): o título vira o h1. */
  principal?: boolean;
  /** Para onde levar; o padrão é a escolha da cidade, na home. */
  acao?: { href: string; rotulo: string };
  children?: React.ReactNode;
}) {
  const Titulo = principal ? "h1" : "h2";
  return (
    <div role="alert" className="painel flex flex-col gap-3">
      <Titulo className="text-lg font-semibold">{titulo}</Titulo>
      <p className="text-muted-foreground">{mensagem}</p>
      {children}
      <Link href={acao.href} className="alvo-link font-medium text-primary underline underline-offset-4">
        {acao.rotulo}
      </Link>
    </div>
  );
}
