import Link from "next/link";

import { Iniciais } from "@/components/eleitos-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { type Camara, type VereadorItem, urlFotoTse } from "@/lib/api";

/** Vereadores no cargo hoje, segundo a própria câmara (SAPL). */
export function CamaraSecao({ dados, cidade }: { dados: Camara; cidade: string }) {
  return (
    <section aria-labelledby="camara-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="camara-titulo" className="text-2xl">
          Câmara de {cidade} hoje <span className="text-muted-foreground">({dados.itens.length})</span>
        </h2>
        <p className="text-sm text-muted-foreground">
          Quem está no cargo agora, como a própria câmara publica: inclui suplentes que assumiram
          e o partido atual de cada um.
        </p>
      </div>
      <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
        {dados.itens.map((v) => (
          <li key={v.id} className="border-b border-border">
            <Link
              href={`/vereador/${v.id}`}
              className="group flex items-center gap-4 py-3 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
            >
              <FotoVereador vereador={v} />
              <div className="min-w-0">
                <p className="truncate text-base font-semibold">{v.nome}</p>
                <p className="text-sm text-muted-foreground">
                  {[v.partido, v.titular ? null : "suplente"].filter(Boolean).join(" · ")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {v.projetos} {v.projetos === 1 ? "projeto" : "projetos"} · {v.proposicoes} proposições
                  (ano atual e anterior)
                </p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

export function FotoVereador({ vereador, tamanho = 44 }: { vereador: VereadorItem; tamanho?: number }) {
  const src =
    vereador.foto_tse && vereador.candidatura_id ? urlFotoTse(vereador.candidatura_id) : vereador.foto_url;
  if (!src) return <Iniciais nome={vereador.nome} tamanho={tamanho} />;
  const altura = Math.round((tamanho * 4) / 3);
  return (
    // eslint-disable-next-line @next/next/no-img-element -- fotos de servidores das câmaras e do TSE
    <img
      src={src}
      alt={`Foto de ${vereador.nome}`}
      width={tamanho}
      height={altura}
      loading="lazy"
      className="shrink-0 rounded-[2px] bg-muted object-cover"
      style={{ width: tamanho, height: altura }}
    />
  );
}
