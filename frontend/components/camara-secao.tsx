import Link from "next/link";

import { Iniciais } from "@/components/eleitos-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { ListaResumida } from "@/components/painel/lista-resumida";
import { type Camara, type VereadorItem, urlFotoTse } from "@/lib/api";

/** Quem está no cargo hoje, segundo a própria casa (SAPL): câmara municipal ou assembleia. */
export function CamaraSecao({
  dados,
  nome,
  casa = "camara",
  limite,
}: {
  dados: Camara;
  /** "Câmara de Blumenau", "Assembleia de Roraima". */
  nome: string;
  casa?: "camara" | "assembleia";
  /** Mostra só os primeiros; o resto fica em "Ver todos". */
  limite?: number;
}) {
  const id = `${casa}-titulo`;
  return (
    <section aria-labelledby={id} className="revelar flex flex-col gap-3">
      <div>
        <h2 id={id} className="text-2xl">
          {nome} hoje <span className="text-muted-foreground">({dados.itens.length})</span>
        </h2>
        <p className="text-sm text-muted-foreground">
          Quem está no cargo agora, como a própria {casa === "camara" ? "câmara" : "assembleia"}{" "}
          publica: inclui suplentes que assumiram e o partido atual de cada um.
        </p>
      </div>
      <ListaResumida
        limite={limite}
        itens={dados.itens.map((v) => (
          <li key={v.id} className="border-b border-border">
            <Link
              href={`/${casa === "camara" ? "vereador" : "deputado-estadual"}/${v.id}`}
              className="group flex items-center gap-4 py-3 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
            >
              <FotoVereador vereador={v} decorativa />
              <div className="min-w-0">
                <p className="truncate text-base font-semibold">{v.nome}</p>
                <p className="text-sm text-muted-foreground">
                  {[v.partido, v.titular ? null : "suplente"].filter(Boolean).join(" · ")}
                </p>
                <p className="text-sm text-muted-foreground">
                  {[
                    `${v.projetos} ${v.projetos === 1 ? "projeto" : "projetos"}`,
                    `${v.proposicoes} proposições`,
                    v.sessoes ? `em ${v.presencas ?? 0} de ${v.sessoes} sessões` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}{" "}
                  (ano atual e anterior)
                </p>
              </div>
            </Link>
          </li>
        ))}
      />
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

export function FotoVereador({
  vereador,
  tamanho = 44,
  decorativa = false,
}: {
  vereador: VereadorItem;
  tamanho?: number;
  /** Com o nome escrito ao lado, dentro do mesmo link: alt vazio. */
  decorativa?: boolean;
}) {
  const src =
    vereador.foto_tse && vereador.candidatura_id ? urlFotoTse(vereador.candidatura_id) : vereador.foto_url;
  if (!src) return <Iniciais nome={vereador.nome} tamanho={tamanho} />;
  const altura = Math.round((tamanho * 4) / 3);
  return (
    // eslint-disable-next-line @next/next/no-img-element -- fotos de servidores das câmaras e do TSE
    <img
      src={src}
      alt={decorativa ? "" : `Foto de ${vereador.nome}`}
      width={tamanho}
      height={altura}
      loading="lazy"
      className="shrink-0 rounded-[2px] bg-muted object-cover"
      style={{ width: tamanho, height: altura }}
    />
  );
}
