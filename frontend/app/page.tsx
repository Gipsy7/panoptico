import Link from "next/link";
import { Suspense } from "react";

import { BuscaGeral } from "@/components/busca-geral";
import { CepForm } from "@/components/cep-form";
import { Marca } from "@/components/logo";
import { Foto } from "@/components/parlamentar-card";
import { type ParlamentarNaLista, type ParlamentarResumo, getComparacao, getRepresentantes } from "@/lib/api";
import { formatarGastos } from "@/lib/formato";

// O exemplo de comparação usa os senadores deste estado (sempre há 3 em exercício).
const UF_DO_EXEMPLO = "SC";

export default function Home() {
  return (
    <div data-largura="larga" className="flex flex-col gap-20">
      <section className="grid items-start gap-12 pt-2 md:grid-cols-[minmax(0,1fr)_minmax(0,25rem)] md:gap-16 md:pt-10">
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <Marca tamanho={28} animada traco={2.6} className="text-bronze" />
            <p className="sobretitulo">O panóptico, invertido</p>
          </div>
          <h1 className="text-5xl leading-[1.04] text-balance sm:text-6xl">
            Quem te representa, <span className="text-bronze-texto italic">às claras</span>
          </h1>
          <p className="max-w-lg text-lg leading-relaxed text-pretty text-muted-foreground">
            O panóptico era uma prisão em que um vigia via todos. Aqui é o contrário: todos podem
            ver quem os representa, do Congresso à câmara da cidade, com dados oficiais.
          </p>
          <div id="cep" className="max-w-md scroll-mt-24 border-t border-foreground pt-6">
            <CepForm />
          </div>
          <div className="flex max-w-md flex-col gap-2">
            <BuscaGeral rotulo="Ou procure pelo nome: parlamentar, governador, prefeito ou vereador" />
          </div>
        </div>

        <Suspense fallback={<div className="h-96 animate-pulse rounded-[2px] bg-muted" aria-hidden />}>
          <ExemploDeComparacao />
        </Suspense>
      </section>

      <OQueVoceEncontra />
    </div>
  );
}

async function ExemploDeComparacao() {
  const representantes = await getRepresentantes({ uf: UF_DO_EXEMPLO });
  if (!representantes.ok) return null;
  const [a, b] = representantes.dados.senadores;
  if (!a || !b) return null;
  const resultado = await getComparacao(String(a.id), String(b.id));
  if (!resultado.ok) return null;
  const { numeros_a: na, numeros_b: nb, convergencia, ano } = resultado.dados;
  if (!na || !nb) return null;

  const linhas: { rotulo: string; a: string; b: string }[] = [
    { rotulo: `Gastos do gabinete em ${ano}`, a: formatarGastos(na.gastos, true), b: formatarGastos(nb.gastos, true) },
    { rotulo: "Votou nas votações", a: presenca(na), b: presenca(nb) },
    { rotulo: "Projetos como autor", a: String(na.projetos), b: String(nb.projetos) },
  ];

  return (
    <aside aria-labelledby="exemplo-titulo" className="flex flex-col gap-3">
      <p id="exemplo-titulo" className="sobretitulo flex items-center gap-2">
        <span aria-hidden className="size-1.5 rounded-full bg-bronze" />
        Exemplo de comparação
      </p>
      <div className="flex flex-col rounded-[2px] border border-border bg-card shadow-[0_24px_48px_-32px_rgb(20_20_20/0.35)]">
        <div className="grid grid-cols-2 gap-4 border-b border-foreground p-5">
          <Pessoa p={a} />
          <Pessoa p={b} />
        </div>
        <dl className="flex flex-col px-5">
          {linhas.map((l) => (
            <div key={l.rotulo} className="border-b border-border py-3">
              <dt className="text-xs text-muted-foreground">{l.rotulo}</dt>
              <div className="mt-1 grid grid-cols-2 gap-4">
                <dd className="numero text-xl">{l.a}</dd>
                <dd className="numero text-xl">{l.b}</dd>
              </div>
            </div>
          ))}
        </dl>
        {convergencia && convergencia.votacoes_em_comum > 0 && (
          <div className="flex flex-col gap-2 px-5 pt-4">
            <p className="text-sm">
              Votaram igual em{" "}
              <span className="numero text-lg">
                {convergencia.iguais} de {convergencia.votacoes_em_comum}
              </span>{" "}
              votações em {ano}
            </p>
            <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
              <div className="h-1.5 rounded-full bg-chart-1" style={{ width: `${convergencia.percentual ?? 0}%` }} />
            </div>
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 p-5">
          <Link href={`/comparar?a=${a.id}&b=${b.id}`} className="botao-linha">
            Ver a comparação completa
          </Link>
          <Link href="/comparar" className="text-sm underline underline-offset-4">
            Comparar outros
          </Link>
        </div>
      </div>
    </aside>
  );
}

function presenca(n: ParlamentarNaLista) {
  return n.presenca === null ? "—" : `${n.presenca_votou} de ${n.presenca_total}`;
}

function Pessoa({ p }: { p: ParlamentarResumo }) {
  return (
    <Link href={`/parlamentar/${p.id}`} className="flex min-w-0 items-center gap-3 hover:opacity-80">
      <Foto parlamentar={p} largura={44} />
      <span className="flex min-w-0 flex-col gap-1">
        <span className="line-clamp-2 text-sm font-semibold leading-tight">{p.nome_parlamentar}</span>
        <span className="flex flex-wrap gap-1">
          {p.partido && <span className="pilula">{p.partido}</span>}
          <span className="pilula">{p.uf}</span>
        </span>
      </span>
    </Link>
  );
}

const ICONE = "size-6 shrink-0 text-bronze";

const RECURSOS = [
  {
    titulo: "Gastos do gabinete",
    texto: "Quanto cada um gastou da cota parlamentar, mês a mês e por tipo de despesa.",
    href: "/parlamentares?ordenar=gastos&ordem=desc",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" />
        <path d="M9 8h6M9 12h6M9 16h3" />
      </svg>
    ),
  },
  {
    titulo: "Presença",
    texto: "Em quantas votações do Plenário cada parlamentar registrou voto.",
    href: "/parlamentares?ordenar=presenca&ordem=desc",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="5" width="16" height="15" rx="1" />
        <path d="M4 10h16M9 3v4M15 3v4M9 15l2 2 4-4" />
      </svg>
    ),
  },
  {
    titulo: "Como votou",
    texto: "Cada votação, por tema, com a orientação do Governo e do partido ao lado.",
    href: "/parlamentares",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 14h16v6H4z" />
        <path d="M8 14V5h8v9M10.5 9.5l1.5 1.5 2.5-3" />
      </svg>
    ),
  },
  {
    titulo: "Projetos",
    texto: "O que apresentou como autor principal e o que virou lei.",
    href: "/parlamentares?ordenar=projetos&ordem=desc",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 3H6v18h12V7z" />
        <path d="M14 3v4h4M9 12h6M9 16h6" />
      </svg>
    ),
  },
  {
    titulo: "Dinheiro para a sua cidade",
    texto: "Emendas pagas ao seu município: quem enviou, para quais áreas e quem recebeu.",
    href: "/#cep",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11z" />
        <circle cx="12" cy="10" r="2.2" />
      </svg>
    ),
  },
  {
    titulo: "Comparar",
    texto: "Dois parlamentares lado a lado: números, temas e em quantas votações votaram igual.",
    href: "/comparar",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="7" height="16" rx="1" />
        <rect x="14" y="4" width="7" height="16" rx="1" />
        <path d="M6.5 9v6M17.5 11v4" />
      </svg>
    ),
  },
];

function OQueVoceEncontra() {
  return (
    <section aria-labelledby="encontra-titulo" className="revelar grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] md:gap-16">
      <div className="flex flex-col gap-3">
        <p className="sobretitulo">O que você encontra</p>
        <h2 id="encontra-titulo" className="text-4xl leading-tight text-balance">
          O mandato de quem te representa, em números oficiais
        </h2>
        <p className="text-muted-foreground">
          Sem notas e sem adjetivos: o número, a média da Casa ao lado e o link para a fonte.
        </p>
      </div>
      <ul className="lista-fios flex flex-col">
        {RECURSOS.map((r) => (
          <li key={r.titulo}>
            <Link
              href={r.href}
              className="group flex gap-4 py-5 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
            >
              {r.icone}
              <span className="flex flex-col gap-1">
                <span className="text-lg font-semibold group-hover:underline group-hover:underline-offset-4">{r.titulo}</span>
                <span className="text-sm text-muted-foreground">{r.texto}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
