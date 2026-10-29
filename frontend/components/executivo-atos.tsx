import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { LinkExterno } from "@/components/link-externo";
import type { AtosPresidenciais, BlocoPainel } from "@/lib/api";
import { formatarData } from "@/lib/formato";

type Grupo = { chave: string; rotulo: string; termo_oficial: string; quantidade: number };

const TEXTOS = {
  mpv: {
    titulo: "Medidas provisórias",
    pergunta: "O que o Presidente editou por urgência",
    param: "mpv",
    ancora: "ver-gov-mpv",
    verbo: "Editada em",
    vazio: "Nenhuma medida provisória nesta situação.",
  },
  veto: {
    titulo: "Vetos",
    pergunta: "Projetos aprovados pelo Congresso que o Presidente recusou",
    param: "veto",
    ancora: "ver-gov-vetos",
    verbo: "Chegou ao Congresso em",
    vazio: "Nenhum veto nesta situação.",
  },
} as const;

/** Medidas provisórias ou vetos do Presidente no mandato em curso: contagem por situação (cada
 * cartão filtra a lista) e a lista, com a situação como o Congresso registra. */
export function AtosPresidenciaisSecao({
  tipo,
  bloco,
  lista,
  candidaturaId,
  outroFiltro,
}: {
  tipo: "mpv" | "veto";
  bloco: BlocoPainel;
  lista: AtosPresidenciais | null;
  candidaturaId: number;
  /** Parâmetros da outra lista (para não perder o filtro dela ao trocar de página aqui). */
  outroFiltro: Record<string, string | undefined>;
}) {
  const t = TEXTOS[tipo];
  const d = bloco.dados as {
    periodo: { inicio: string; fim: string };
    total: number;
    grupos: Grupo[];
    explicacao: string;
    total_integral?: number;
    total_parcial?: number;
  };
  const href = (grupo?: string, pagina?: number) => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(outroFiltro)) if (v) params.set(k, v);
    if (grupo) params.set(`${t.param}_grupo`, grupo);
    if (pagina && pagina > 1) params.set(`${t.param}_pagina`, String(pagina));
    const q = params.toString();
    return `/eleito/${candidaturaId}${q ? `?${q}` : ""}#${t.ancora}`;
  };
  const ativo = lista?.grupo ?? null;
  const paginas = lista ? Math.max(1, Math.ceil(lista.total / lista.por_pagina)) : 1;
  const nomeAtivo = d.grupos.find((g) => g.chave === ativo)?.rotulo;
  return (
    <section aria-labelledby={`${t.param}-titulo`} className="revelar flex flex-col gap-4">
      <div>
        <h2 id={`${t.param}-titulo`} className="text-2xl">
          {t.titulo} do mandato atual
        </h2>
        <p className="text-sm text-muted-foreground">{t.pergunta}</p>
        <p className="text-sm text-muted-foreground">
          De {formatarData(d.periodo.inicio)} (posse) a {formatarData(d.periodo.fim)}; só o mandato em curso.
        </p>
      </div>
      <p className="text-sm">{d.explicacao}</p>

      <div className="flex flex-col gap-1">
        <p className="figura">
          <span className="numero text-3xl">{d.total.toLocaleString("pt-BR")}</span>{" "}
          <span className="text-muted-foreground">
            {tipo === "mpv" ? "medidas provisórias editadas" : "vetos recebidos pelo Congresso"}
          </span>
        </p>
        {tipo === "veto" && d.total_parcial != null && d.total_integral != null && (
          <p className="text-sm text-muted-foreground">
            {d.total_parcial.toLocaleString("pt-BR")} parciais (só alguns trechos) e{" "}
            {d.total_integral.toLocaleString("pt-BR")} totais (o projeto inteiro).
          </p>
        )}
      </div>

      <ul aria-label={`${t.titulo} por situação`} className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {d.grupos.map((g) => (
          <li key={g.chave}>
            <Link
              href={href(ativo === g.chave ? undefined : g.chave)}
              scroll={false}
              aria-current={ativo === g.chave ? "true" : undefined}
              className={`alvo-link flex h-full items-baseline justify-between gap-3 rounded-xl bg-card p-3 ring-1 ${
                ativo === g.chave ? "ring-2 ring-foreground" : "ring-foreground/10"
              }`}
            >
              <span className="min-w-0">
                <span className="block">{g.rotulo}</span>
                <span className="block text-sm text-muted-foreground">{g.termo_oficial}</span>
              </span>
              <span className="numero shrink-0 text-2xl">{g.quantidade.toLocaleString("pt-BR")}</span>
            </Link>
          </li>
        ))}
      </ul>

      {lista ? (
        <div className="flex flex-col gap-3">
          <h3 className="font-medium">
            {nomeAtivo ? `${nomeAtivo}: ${lista.total.toLocaleString("pt-BR")}` : "Do mais recente para o mais antigo"}
          </h3>
          {ativo && (
            <Link href={href()} scroll={false} className="alvo-link self-start text-sm underline underline-offset-2">
              Ver todas
            </Link>
          )}
          {lista.itens.length === 0 && <p className="text-sm text-muted-foreground">{t.vazio}</p>}
          <ul className="flex flex-col gap-3">
            {lista.itens.map((a) => (
              <li key={a.identificacao} className="flex flex-col gap-1 rounded-xl bg-card p-3 ring-1 ring-foreground/10">
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">{a.identificacao}</span>
                  {a.veto && <span className="pilula">Veto {a.veto.toLowerCase()}</span>}
                  <span className="text-sm text-muted-foreground">
                    {t.verbo} {formatarData(a.data)}
                  </span>
                </p>
                {a.apelido && <p className="text-sm font-medium">{a.apelido}</p>}
                <p className="text-sm">{a.ementa}</p>
                <p className="text-sm">
                  {a.rotulo}
                  {a.data_decisao && <span className="text-muted-foreground"> · {tipo === "mpv" ? "situação definida em" : "decisão em"} {formatarData(a.data_decisao)}</span>}
                  <span className="block text-sm text-muted-foreground">
                    {a.termo_oficial}
                    {a.situacao && a.situacao.toLowerCase() !== a.termo_oficial.toLowerCase() && ` · ${a.situacao.toLowerCase()}`}
                  </span>
                </p>
                <LinkExterno href={a.url} className="alvo-link self-start text-sm underline underline-offset-2">
                  Ver no Congresso Nacional
                </LinkExterno>
              </li>
            ))}
          </ul>
          {paginas > 1 && (
            <nav aria-label={`Páginas de ${t.titulo.toLowerCase()}`} className="flex items-center justify-between gap-3 text-sm">
              {lista.pagina > 1 ? (
                <Link href={href(ativo ?? undefined, lista.pagina - 1)} scroll={false} className="alvo-link underline underline-offset-2">
                  Mais recentes
                </Link>
              ) : (
                <span />
              )}
              <span className="text-muted-foreground">
                Página {lista.pagina} de {paginas}
              </span>
              {lista.pagina < paginas ? (
                <Link href={href(ativo ?? undefined, lista.pagina + 1)} scroll={false} className="alvo-link underline underline-offset-2">
                  Mais antigas
                </Link>
              ) : (
                <span />
              )}
            </nav>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Não deu para buscar a lista agora.</p>
      )}

      <p className="text-sm text-muted-foreground">
        Sem comparação com média: só existe um Presidente por vez. Os textos das ementas são os do Congresso; a
        situação é a registrada por ele na data da fonte.
      </p>
      <FonteRodape
        fonte={bloco.fonte_nome ?? "Congresso Nacional"}
        url={bloco.fonte_url ?? undefined}
        atualizadoEm={bloco.atualizado_em}
      />
    </section>
  );
}
