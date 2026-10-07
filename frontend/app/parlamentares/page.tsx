import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";
import { Suspense } from "react";

import { AvisoErro } from "@/components/aviso-erro";
import { FonteRodape } from "@/components/fonte-rodape";
import { Foto } from "@/components/parlamentar-card";
import { Button } from "@/components/ui/button";
import {
  type CriterioId,
  type FiltrosLista,
  type ListaParlamentares,
  type ParlamentarNaLista,
  getParlamentares,
} from "@/lib/api";
import { CASA_CURTA, formatarReais } from "@/lib/formato";
import { UFS } from "@/lib/ufs";

export const metadata: Metadata = {
  title: "Todos os parlamentares",
  description:
    "Deputados federais e senadores em exercício, com gastos, presença, projetos e emendas, ordenáveis por um critério de cada vez.",
};

const CAMPOS: (keyof FiltrosLista)[] = ["busca", "casa", "uf", "partido", "ordenar", "ordem", "ano", "pagina"];

export default function ParlamentaresPage({ searchParams }: PageProps<"/parlamentares">) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Todos os parlamentares</h1>
        <p className="text-muted-foreground">
          Deputados federais e senadores em exercício. Escolha um critério para ordenar a lista:
          cada número vem de fonte oficial e não é uma nota.
        </p>
      </header>
      <Suspense fallback={<p className="text-muted-foreground">Carregando…</p>}>
        {searchParams.then((sp) => {
          const filtros: FiltrosLista = {};
          for (const campo of CAMPOS) {
            const valor = sp[campo];
            if (typeof valor === "string" && valor) filtros[campo] = valor;
          }
          return <Lista filtros={filtros} />;
        })}
      </Suspense>
    </div>
  );
}

async function Lista({ filtros }: { filtros: FiltrosLista }) {
  const resultado = await getParlamentares(filtros);
  if (!resultado.ok) {
    return <AvisoErro titulo="Não deu para carregar a lista" mensagem={resultado.mensagem} />;
  }
  const dados = resultado.dados;
  const criterio = dados.criterios.find((c) => c.id === dados.ordenar)!;
  const paginas = Math.max(1, Math.ceil(dados.total / dados.por_pagina));

  return (
    <>
      <Filtros dados={dados} filtros={filtros} />

      <section aria-labelledby="lista-titulo" className="flex flex-col gap-3">
        <div className="flex flex-col gap-1 rounded-xl bg-muted p-4 text-sm">
          <h2 id="lista-titulo" className="font-semibold">
            {dados.total} {dados.total === 1 ? "parlamentar" : "parlamentares"}
            {dados.ordenar !== "nome" && <> · ordenado por {criterio.nome.toLowerCase()}</>}
          </h2>
          <p className="text-muted-foreground">{criterio.definicao}</p>
          {dados.ordenar !== "nome" && (
            <p className="text-muted-foreground">
              Média em {dados.ano}:{" "}
              {(["camara", "senado"] as const)
                .filter((casa) => dados.medias[casa][dados.ordenar] != null)
                .map(
                  (casa) =>
                    `${CASA_CURTA[casa]} ${formatarValor(dados.ordenar, dados.medias[casa][dados.ordenar]!)}`,
                )
                .join(" · ")}
            </p>
          )}
        </div>

        {dados.itens.length === 0 ? (
          <p className="text-muted-foreground">Ninguém encontrado com esses filtros.</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {dados.itens.map((p) => (
              <li key={p.id}>
                <Cartao p={p} ordenar={dados.ordenar} />
              </li>
            ))}
          </ul>
        )}

        {paginas > 1 && (
          <nav aria-label="Páginas" className="flex items-center justify-between gap-2 text-sm">
            <LinkPagina filtros={filtros} pagina={dados.pagina - 1} ativo={dados.pagina > 1}>
              ← Anteriores
            </LinkPagina>
            <span className="text-muted-foreground">
              Página {dados.pagina} de {paginas}
            </span>
            <LinkPagina filtros={filtros} pagina={dados.pagina + 1} ativo={dados.pagina < paginas}>
              Próximos →
            </LinkPagina>
          </nav>
        )}
      </section>

      <FonteRodape fonte="Câmara, Senado e Portal da Transparência" url="/sobre-as-fontes" atualizadoEm={dados.atualizado_em} />
    </>
  );
}

const SELECT =
  "h-11 rounded-xl border border-input bg-card px-3 text-sm focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none";

function Filtros({ dados, filtros }: { dados: ListaParlamentares; filtros: FiltrosLista }) {
  return (
    <Form action="/parlamentares" className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <label className="col-span-2 flex flex-col gap-1 text-sm sm:col-span-3">
        Nome
        <input
          type="search"
          name="busca"
          defaultValue={filtros.busca}
          placeholder="Parte do nome"
          className={SELECT}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Casa
        <select name="casa" defaultValue={filtros.casa ?? ""} className={SELECT}>
          <option value="">Câmara e Senado</option>
          <option value="camara">Câmara</option>
          <option value="senado">Senado</option>
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Estado
        <select name="uf" defaultValue={filtros.uf ?? ""} className={SELECT}>
          <option value="">Todos</option>
          {UFS.map((uf) => (
            <option key={uf.sigla} value={uf.sigla}>
              {uf.nome}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Partido
        <select name="partido" defaultValue={filtros.partido ?? ""} className={SELECT}>
          <option value="">Todos</option>
          {dados.partidos.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Ordenar por
        <select name="ordenar" defaultValue={dados.ordenar} className={SELECT}>
          {dados.criterios.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Ordem
        <select name="ordem" defaultValue={dados.ordem} className={SELECT}>
          <option value="asc">Crescente</option>
          <option value="desc">Decrescente</option>
        </select>
      </label>
      {dados.anos_disponiveis.length > 1 && (
        <label className="flex flex-col gap-1 text-sm">
          Ano
          <select name="ano" defaultValue={String(dados.ano)} className={SELECT}>
            {dados.anos_disponiveis.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
      )}
      <Button type="submit" className="col-span-2 h-11 rounded-xl sm:col-span-3">
        Aplicar
      </Button>
    </Form>
  );
}

function formatarValor(criterio: CriterioId, valor: number): string {
  switch (criterio) {
    case "gastos":
    case "emendas":
      return formatarReais(valor, true);
    case "presenca":
    case "governo":
      return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
    default:
      return valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  }
}

function Cartao({ p, ordenar }: { p: ParlamentarNaLista; ordenar: CriterioId }) {
  const numeros: { id: CriterioId; rotulo: string; valor: string }[] = [
    { id: "gastos", rotulo: "Gastos", valor: formatarReais(p.gastos, true) },
    {
      id: "presenca",
      rotulo: "Votou",
      valor: p.presenca === null ? "—" : `${p.presenca_votou} de ${p.presenca_total}`,
    },
    { id: "projetos", rotulo: "Projetos", valor: String(p.projetos) },
    { id: "normas", rotulo: "Viraram norma", valor: String(p.normas) },
    { id: "emendas", rotulo: "Emendas pagas", valor: formatarReais(p.emendas, true) },
  ];
  if (p.casa === "camara") {
    numeros.push({
      id: "governo",
      rotulo: "Como o Governo",
      valor: p.governo === null ? "—" : `${p.governo_iguais} de ${p.governo_total}`,
    });
  }
  return (
    <Link
      href={`/parlamentar/${p.id}`}
      className="flex h-full flex-col gap-3 rounded-xl bg-card p-3 ring-1 ring-foreground/10 transition-colors hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <div className="flex items-center gap-3">
        <Foto parlamentar={p} largura={44} />
        <div className="min-w-0">
          <p className="truncate font-semibold">{p.nome_parlamentar}</p>
          <p className="text-sm text-muted-foreground">
            {CASA_CURTA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
          </p>
        </div>
      </div>
      <dl className="grid grid-cols-3 gap-x-2 gap-y-1 text-xs">
        {numeros.map((n) => (
          <div key={n.id} className={n.id === ordenar ? "rounded-md bg-accent px-1.5 py-1" : "px-1.5 py-1"}>
            <dt className="text-muted-foreground">{n.rotulo}</dt>
            <dd className="font-semibold tabular-nums">{n.valor}</dd>
          </div>
        ))}
      </dl>
    </Link>
  );
}

function LinkPagina({
  filtros,
  pagina,
  ativo,
  children,
}: {
  filtros: FiltrosLista;
  pagina: number;
  ativo: boolean;
  children: React.ReactNode;
}) {
  if (!ativo) return <span className="text-muted-foreground/50">{children}</span>;
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries({ ...filtros, pagina: String(pagina) })) {
    if (valor) params.set(chave, valor);
  }
  return (
    <Link href={`/parlamentares?${params}`} className="font-medium underline underline-offset-4">
      {children}
    </Link>
  );
}
