import type { Metadata } from "next";
import Link from "next/link";

import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { AvisoErro } from "@/components/aviso-erro";
import { Revelacao } from "@/components/revelacao";
import { FonteRodape } from "@/components/fonte-rodape";
import { Foto } from "@/components/parlamentar-card";
import { CampoSelect, CampoTexto, type FiltroAtivo, PilulasAtivas, SemResultados } from "@/components/ui/campos-filtro";
import { CamposOrdenacao } from "@/components/ui/campos-filtro-cliente";
import { PainelFiltros } from "@/components/ui/painel-filtros";
import { Resumo2x2 } from "@/components/ui/resumo-2x2";
import {
  type CriterioId,
  type FiltrosLista,
  type ListaParlamentares,
  type ParlamentarNaLista,
  getParlamentares,
} from "@/lib/api";
import { CASA_CURTA, formatarGastos, formatarReais, formatarReaisCompacto } from "@/lib/formato";
import { UFS } from "@/lib/ufs";

export const metadata: Metadata = {
  title: "Todos os parlamentares",
  description:
    "Deputados federais e senadores em exercício, com gastos, presença, projetos e emendas, ordenáveis por um critério de cada vez.",
};

const CAMPOS: (keyof FiltrosLista)[] = ["busca", "casa", "uf", "partido", "ordenar", "ordem", "ano", "pagina"];

export default function ParlamentaresPage({ searchParams }: PageProps<"/parlamentares">) {
  return (
    <div className="pagina-secoes">
      <CabecalhoPagina
        sobretitulo="Congresso Nacional"
        titulo="Todos os parlamentares"
        subtitulo="Deputados federais e senadores em exercício. Escolha um critério para ordenar a lista: cada número vem de fonte oficial e não é uma nota."
      />
      <Revelacao fallback={<EsqueletoSecao rotulo="Carregando a lista de parlamentares…" secoes={2} />}>
        {searchParams.then((sp) => {
          const filtros: FiltrosLista = {};
          for (const campo of CAMPOS) {
            const valor = sp[campo];
            if (typeof valor === "string" && valor) filtros[campo] = valor;
          }
          return <Lista filtros={filtros} />;
        })}
      </Revelacao>
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
  const ativos = filtrosAtivos(dados, filtros);

  return (
    <>
      <Resumo2x2
        titulo={`Resumo do Congresso em ${dados.ano}`}
        itens={[
          { rotulo: "Deputados federais", valor: dados.por_casa.camara.toLocaleString("pt-BR") },
          { rotulo: "Senadores", valor: dados.por_casa.senado.toLocaleString("pt-BR") },
          { rotulo: "Partidos representados", valor: dados.partidos.length.toLocaleString("pt-BR") },
          {
            rotulo: `Gasto médio por deputado em ${dados.ano}`,
            valor: dados.medias.camara.gastos != null ? formatarReaisCompacto(dados.medias.camara.gastos) : "—",
            apoio:
              dados.medias.senado.gastos != null
                ? `Senado: ${formatarReaisCompacto(dados.medias.senado.gastos)}`
                : undefined,
          },
        ]}
      />
      <FiltrosDaLista dados={dados} filtros={filtros} ativos={ativos} />

      <section aria-labelledby="lista-titulo" className="revelar flex flex-col gap-3">
        <div className="nota flex flex-col gap-1 text-sm">
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
          <SemResultados mensagem="Nenhum parlamentar com esses filtros." limparHref={ativos.length ? "/parlamentares" : undefined}>
            <p className="text-sm text-muted-foreground">Tire um filtro acima ou confira a grafia do nome.</p>
          </SemResultados>
        ) : (
          <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
            {dados.itens.map((p) => (
              <li key={p.id} className="border-b border-border">
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

/** Endereço da lista com uma mudança nos filtros; volta para a página 1 e tira o que é padrão. */
function enderecoLista(filtros: FiltrosLista, mudanca: Partial<Record<keyof FiltrosLista, string>>) {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries({ ...filtros, ...mudanca, pagina: "" })) {
    if (valor && !(chave === "ordenar" && valor === "nome")) params.set(chave, valor);
  }
  const texto = params.toString();
  return texto ? `/parlamentares?${texto}` : "/parlamentares";
}

const NOME_CASA: Record<string, string> = { camara: "Câmara", senado: "Senado" };

/** Filtros ativos, cada um com o endereço da lista sem ele. */
function filtrosAtivos(dados: ListaParlamentares, filtros: FiltrosLista): FiltroAtivo[] {
  const anoPadrao = Math.max(...dados.anos_disponiveis);
  const criterio = dados.criterios.find((c) => c.id === dados.ordenar);
  const ativos: (FiltroAtivo | null)[] = [
    filtros.busca ? { rotulo: `Nome: ${filtros.busca}`, href: enderecoLista(filtros, { busca: "" }) } : null,
    filtros.casa && NOME_CASA[filtros.casa]
      ? { rotulo: `Só ${NOME_CASA[filtros.casa]}`, href: enderecoLista(filtros, { casa: "" }) }
      : null,
    filtros.uf ? { rotulo: `Estado: ${nomeUf(filtros.uf)}`, href: enderecoLista(filtros, { uf: "" }) } : null,
    filtros.partido ? { rotulo: `Partido: ${filtros.partido}`, href: enderecoLista(filtros, { partido: "" }) } : null,
    dados.ordenar !== "nome" && criterio
      ? {
          rotulo: `Ordem: ${criterio.nome.toLowerCase()} (${dados.ordem === "desc" ? "maior primeiro" : "menor primeiro"})`,
          href: enderecoLista(filtros, { ordenar: "", ordem: "" }),
        }
      : dados.ordenar === "nome" && dados.ordem === "desc"
        ? { rotulo: "Ordem: de Z a A", href: enderecoLista(filtros, { ordem: "" }) }
        : null,
    dados.ano !== anoPadrao ? { rotulo: `Ano: ${dados.ano}`, href: enderecoLista(filtros, { ano: "" }) } : null,
  ];
  return ativos.filter((a): a is FiltroAtivo => a !== null);
}

function nomeUf(sigla: string) {
  return UFS.find((u) => u.sigla === sigla.toUpperCase())?.nome ?? sigla.toUpperCase();
}

function FiltrosDaLista({ dados, filtros, ativos }: { dados: ListaParlamentares; filtros: FiltrosLista; ativos: FiltroAtivo[] }) {
  const anoPadrao = Math.max(...dados.anos_disponiveis);
  const chave = new URLSearchParams(Object.entries(filtros) as [string, string][]).toString();
  return (
    <section aria-label="Filtros da lista" className="flex flex-col gap-[var(--esp-4)]">
      <PainelFiltros
        key={chave}
        action="/parlamentares"
        ativos={ativos.length}
        limparHref="/parlamentares"
        padroes={{ ordenar: "nome", ordem: "asc", ano: String(anoPadrao) }}
      >
        <CampoTexto rotulo="Nome" name="busca" defaultValue={filtros.busca} placeholder="Parte do nome" className="md:col-span-3" />
        <CampoSelect
          rotulo="Casa"
          name="casa"
          defaultValue={filtros.casa}
          opcoes={[
            { valor: "", rotulo: "Câmara e Senado" },
            { valor: "camara", rotulo: "Câmara dos Deputados" },
            { valor: "senado", rotulo: "Senado" },
          ]}
        />
        <CampoSelect
          rotulo="Estado"
          name="uf"
          defaultValue={filtros.uf?.toUpperCase()}
          opcoes={[{ valor: "", rotulo: "Todos os estados" }, ...UFS.map((u) => ({ valor: u.sigla, rotulo: u.nome }))]}
        />
        <CampoSelect
          rotulo="Partido"
          name="partido"
          defaultValue={filtros.partido}
          opcoes={[{ valor: "", rotulo: "Todos os partidos" }, ...dados.partidos.map((p) => ({ valor: p, rotulo: p }))]}
        />
        <CamposOrdenacao
          criterios={dados.criterios.map((c) => ({ valor: c.id, rotulo: c.nome }))}
          ordenar={dados.ordenar}
          ordem={dados.ordem}
          textuais={["nome"]}
        />
        {dados.anos_disponiveis.length > 1 && (
          <CampoSelect
            rotulo="Ano dos números"
            name="ano"
            defaultValue={String(dados.ano)}
            opcoes={dados.anos_disponiveis.map((a) => ({ valor: String(a), rotulo: a === anoPadrao ? `${a} (mais recente)` : String(a) }))}
          />
        )}
      </PainelFiltros>
      <PilulasAtivas itens={ativos} limparHref="/parlamentares" />
    </section>
  );
}

function formatarValor(criterio: CriterioId, valor: number): string {
  switch (criterio) {
    case "gastos":
      return formatarGastos(valor, true);
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
    { id: "gastos", rotulo: "Gastos", valor: formatarGastos(p.gastos, true) },
    {
      id: "presenca",
      rotulo: "Votou",
      valor: p.presenca === null ? "—" : `${p.presenca_votou} de ${p.presenca_total}`,
    },
    { id: "projetos", rotulo: "Projetos", valor: String(p.projetos) },
    { id: "normas", rotulo: "Viraram norma", valor: String(p.normas) },
    { id: "emendas", rotulo: "Emendas pagas", valor: formatarReais(p.emendas, true) },
  ];
  {
    numeros.push({
      id: "governo",
      rotulo: "Como o Governo",
      valor: p.governo === null ? "—" : `${p.governo_iguais} de ${p.governo_total}`,
    });
  }
  return (
    <Link
      href={`/parlamentar/${p.id}`}
      className="flex h-full flex-col gap-3 py-4 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
    >
      <div className="flex items-center gap-3">
        <Foto parlamentar={p} largura={44} decorativa />
        <div className="min-w-0">
          <p className="truncate font-semibold">{p.nome_parlamentar}</p>
          <p className="text-sm text-muted-foreground">
            {CASA_CURTA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
          </p>
        </div>
      </div>
      <dl className="grid grid-cols-3 gap-x-2 gap-y-1 text-sm">
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
  if (!ativo) return <span aria-hidden className="invisible">{children}</span>;
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries({ ...filtros, pagina: String(pagina) })) {
    if (valor) params.set(chave, valor);
  }
  return (
    <Link href={`/parlamentares?${params}`} className="alvo-link px-1 font-medium underline underline-offset-4">
      {children}
    </Link>
  );
}
