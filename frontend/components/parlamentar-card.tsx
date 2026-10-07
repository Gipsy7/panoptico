import Image from "next/image";
import Link from "next/link";
import { ViewTransition } from "react";

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
      className="flex items-center gap-4 rounded-xl border border-border/80 bg-card p-3 transition-[background-color,transform,box-shadow] duration-300 ease-out hover:-translate-y-0.5 hover:bg-accent/60 hover:shadow-[0_10px_30px_-18px_oklch(0.36_0.1_330/0.45)] focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none motion-reduce:transition-none motion-reduce:hover:translate-y-0"
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
  // Mesmo nome no card e no topo do perfil: a foto "voa" de um para o outro.
  // Cada parlamentar aparece no máximo uma vez por página, então o nome é único.
  return (
    <ViewTransition name={`foto-${parlamentar.id}`} share="morph" default="none">
      <Image
        src={parlamentar.foto_url}
        alt={`Foto de ${parlamentar.nome_parlamentar}`}
        width={largura}
        height={altura}
        preload={prioridade}
        className="shrink-0 rounded-lg bg-muted object-cover"
        style={{ width: largura, height: altura }}
      />
    </ViewTransition>
  );
}
