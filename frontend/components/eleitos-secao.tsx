import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { type Eleito, type ListaEleitos, urlFotoTse } from "@/lib/api";

/** Vereadores de uma cidade ou deputados estaduais de um estado, como eleitos no TSE. */
export function EleitosSecao({
  id,
  titulo,
  explicacao,
  dados,
  recolhido = false,
}: {
  id: string;
  titulo: string;
  explicacao: string;
  dados: ListaEleitos;
  /** Quando a câmara já mostra quem está no cargo hoje, a lista do TSE fica recolhida. */
  recolhido?: boolean;
}) {
  if (recolhido) {
    return (
      <details className="painel">
        <summary className="cursor-pointer font-medium">
          {titulo} na eleição ({dados.itens.length}), segundo o TSE
        </summary>
        <ul className="mt-3 grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
          {dados.itens.map((e) => (
            <li key={e.id} className="border-b border-border">
              <CartaoEleito eleito={e} />
            </li>
          ))}
        </ul>
      </details>
    );
  }
  return (
    <section aria-labelledby={id} className="revelar flex flex-col gap-3">
      <div>
        <h2 id={id} className="text-2xl">
          {titulo} <span className="text-muted-foreground">({dados.itens.length})</span>
        </h2>
        <p className="text-sm text-muted-foreground">{explicacao}</p>
      </div>
      {dados.itens.length === 0 ? (
        <p className="text-muted-foreground">Nenhum dado carregado ainda.</p>
      ) : (
        <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
          {dados.itens.map((e) => (
            <li key={e.id} className="border-b border-border">
              <CartaoEleito eleito={e} />
            </li>
          ))}
        </ul>
      )}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

function CartaoEleito({ eleito }: { eleito: Eleito }) {
  const href = eleito.parlamentar_id ? `/parlamentar/${eleito.parlamentar_id}` : `/eleito/${eleito.id}`;
  return (
    <Link
      href={href}
      className="group flex items-center gap-4 py-3 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
    >
      <FotoOuIniciais eleito={eleito} />
      <div className="min-w-0">
        <p className="truncate text-base font-semibold">{eleito.nome_urna}</p>
        <p className="text-sm text-muted-foreground">
          {[eleito.partido, eleito.uf].filter(Boolean).join(" · ")}
        </p>
        {eleito.votos != null && (
          <p className="text-xs text-muted-foreground">{eleito.votos.toLocaleString("pt-BR")} votos</p>
        )}
        {eleito.parlamentar_id ? (
          <p className="text-xs font-medium text-bronze-texto">Hoje é deputado federal</p>
        ) : (
          eleito.depois && (
            <p className="text-xs font-medium text-bronze-texto">
              Eleito {eleito.depois.cargo.toLowerCase()} de {eleito.depois.unidade} em {eleito.depois.ano}
            </p>
          )
        )}
      </div>
    </Link>
  );
}

/** Foto do TSE quando houver; senão, as iniciais. */
export function FotoOuIniciais({ eleito, tamanho = 44 }: { eleito: Eleito; tamanho?: number }) {
  if (!eleito.foto) return <Iniciais nome={eleito.nome_urna} tamanho={tamanho} />;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- WebP pequeno, já reduzido e com cache longo na CDN
    <img
      src={urlFotoTse(eleito.id)}
      alt={`Foto de ${eleito.nome_urna}`}
      width={tamanho}
      height={Math.round((tamanho * 4) / 3)}
      loading="lazy"
      className="shrink-0 rounded-[2px] bg-muted object-cover"
      style={{ width: tamanho, height: Math.round((tamanho * 4) / 3) }}
    />
  );
}

/** Sem foto: as iniciais no lugar. */
export function Iniciais({ nome, tamanho = 44 }: { nome: string; tamanho?: number }) {
  const partes = nome.split(/\s+/).filter(Boolean);
  const iniciais = ((partes[0]?.[0] ?? "") + (partes.length > 1 ? partes.at(-1)![0] : "")).toUpperCase();
  return (
    <span
      aria-hidden
      style={{ width: tamanho, height: Math.round((tamanho * 4) / 3) }}
      className="flex shrink-0 items-center justify-center rounded-[2px] bg-muted font-heading text-lg text-muted-foreground"
    >
      {iniciais}
    </span>
  );
}
