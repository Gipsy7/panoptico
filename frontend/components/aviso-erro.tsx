import Link from "next/link";

export function AvisoErro({ titulo, mensagem }: { titulo: string; mensagem: string }) {
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-xl bg-card p-5 border border-border/80">
      <h2 className="text-lg font-semibold">{titulo}</h2>
      <p className="text-muted-foreground">{mensagem}</p>
      <Link href="/" className="font-medium text-primary underline underline-offset-4">
        Fazer outra busca
      </Link>
    </div>
  );
}
