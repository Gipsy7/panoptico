import Image from "next/image";
import Link from "next/link";

import type { ParlamentarResumo } from "@/lib/api";

export function ParlamentarCard({
  parlamentar,
  destaque,
}: {
  parlamentar: ParlamentarResumo;
  destaque?: string;
}) {
  return (
    <Link
      href={`/parlamentar/${parlamentar.id}`}
      className="flex items-center gap-4 rounded-xl bg-card p-3 ring-1 ring-foreground/10 transition-colors hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <Foto parlamentar={parlamentar} largura={56} />
      <div className="min-w-0">
        <p className="truncate text-base font-semibold">{parlamentar.nome_parlamentar}</p>
        <p className="text-sm text-muted-foreground">
          {[parlamentar.partido, parlamentar.uf].filter(Boolean).join(" · ")}
        </p>
        {destaque && <p className="text-xs font-medium text-primary">{destaque}</p>}
      </div>
    </Link>
  );
}

export function Foto({
  parlamentar,
  largura,
  prioridade = false,
}: {
  parlamentar: ParlamentarResumo;
  largura: number;
  prioridade?: boolean;
}) {
  const altura = Math.round((largura * 4) / 3);
  if (!parlamentar.foto_url) {
    return (
      <div
        aria-hidden
        style={{ width: largura, height: altura }}
        className="shrink-0 rounded-lg bg-muted"
      />
    );
  }
  return (
    <Image
      src={parlamentar.foto_url}
      alt={`Foto de ${parlamentar.nome_parlamentar}`}
      width={largura}
      height={altura}
      preload={prioridade}
      className="shrink-0 rounded-lg bg-muted object-cover"
      style={{ width: largura, height: altura }}
    />
  );
}
