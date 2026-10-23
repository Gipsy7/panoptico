import Link from "next/link";
import { Suspense } from "react";

import { AvisoSegundoTurno } from "@/components/aviso-segundo-turno";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { BuscaGeral } from "@/components/busca-geral";
import { CepForm } from "@/components/cep-form";
import { FonteRodape } from "@/components/fonte-rodape";
import { MENSAGEM_CARREGANDO, reais, textoSemDado } from "@/components/dinheiro-federal/formatos";
import { MapaHome } from "@/components/home-mapa/mapa-home";
import { Marca } from "@/components/logo";
import { PanopticoDesenho } from "@/components/panoptico-desenho";
import { Foto } from "@/components/parlamentar-card";
import {
  type ParlamentarNaLista,
  type ParlamentarResumo,
  getComparacao,
  getDinheiroFederal,
  getRepresentantes,
} from "@/lib/api";
import { formatarGastos } from "@/lib/formato";

// O exemplo de comparação usa os senadores deste estado (sempre há 3 em exercício).
const UF_DO_EXEMPLO = "SC";

export default function Home() {
  return (
    <div data-largura="larga" className="flex flex-col gap-[var(--esp-16)]">
      <section className="grid items-start gap-12 pt-2 md:grid-cols-[minmax(0,1fr)_minmax(0,25rem)] md:gap-16 md:pt-10">
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <Marca tamanho={28} animada traco={2.6} className="text-bronze" />
            <p className="sobretitulo">O panóptico, invertido</p>
          </div>
          <h1 className="text-[2rem] leading-[1.1] text-balance sm:text-5xl lg:text-6xl">
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
          <Suspense fallback={null}>
            <div className="max-w-md empty:hidden">
              <AvisoSegundoTurno href="/segundo-turno" />
            </div>
          </Suspense>
        </div>

        <Suspense
          fallback={
            <div className="min-h-96 border border-border p-[var(--esp-4)]">
              <EsqueletoSecao rotulo="Carregando o exemplo de comparação…" />
            </div>
          }
        >
          <ExemploDeComparacao />
        </Suspense>
      </section>

      <Suspense fallback={<div className="min-h-96" aria-hidden />}>
        <DinheiroFederalHome />
      </Suspense>

      <OQueVoceEncontra />

      <PorQuePanoptico />
    </div>
  );
}

async function DinheiroFederalHome() {
  const r = await getDinheiroFederal();
  if (!r.ok) return null;
  if (r.dados.sem_dados) {
    return (
      <section aria-labelledby="impostos-titulo" className="revelar flex flex-col gap-3">
        <p className="sobretitulo">Impostos e repasses</p>
        <h2 id="impostos-titulo" className="text-3xl leading-tight text-balance sm:text-4xl">
          Quanto a União arrecada e repassa em cada estado
        </h2>
        <p className="text-muted-foreground">{MENSAGEM_CARREGANDO}</p>
        <div>
          <Link href="/impostos-e-repasses" className="botao-linha">
            Ir para a página de impostos e repasses
          </Link>
        </div>
      </section>
    );
  }
  const { brasil, ufs, ano, avisos, fontes } = r.dados;
  const dataFonte = fontes.map((f) => f.atualizado_em).filter((d): d is string => Boolean(d)).sort()[0] ?? null;
  return (
    <section aria-labelledby="impostos-titulo" className="revelar grid items-start gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-16">
      <div className="flex flex-col gap-4">
        <p className="sobretitulo">Impostos e repasses</p>
        <h2 id="impostos-titulo" className="text-3xl leading-tight text-balance sm:text-4xl">
          Quanto a União arrecada e repassa em cada estado
        </h2>
        <p className="text-muted-foreground">Dados de {ano}. Passe o mouse ou toque num estado para ver os números.</p>
        <dl className="grid grid-cols-2 gap-4 border-t border-foreground pt-4">
          <div>
            <dt className="text-sm text-muted-foreground">Arrecadado no país</dt>
            <dd className="numero text-2xl">{reais(brasil.arrecadacao)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Repassado a estados e cidades</dt>
            <dd className="numero text-2xl">{reais(brasil.repasse)}</dd>
          </div>
        </dl>
        {textoSemDado(brasil, ano) && <p className="text-sm text-muted-foreground">{textoSemDado(brasil, ano)}</p>}
        {avisos.map((a) => (
          <p key={a} className="text-sm text-muted-foreground">
            {a}
          </p>
        ))}
        <div>
          <Link href="/impostos-e-repasses" className="botao-linha">
            Ver o mapa completo, com as 5.570 cidades
          </Link>
        </div>
        <FonteRodape fonte={fontes[0]?.nome ?? "Tesouro Nacional e Receita Federal"} url={fontes[0]?.url} atualizadoEm={dataFonte} />
      </div>
      <MapaHome
        ufs={ufs.map((u) => ({ uf: u.uf, nome: u.nome, arrecadacao: u.arrecadacao, repasse: u.repasse }))}
      />
    </section>
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
      <div className="flex flex-col rounded-[2px] border border-border bg-card">
        <div className="grid grid-cols-2 gap-3 border-b border-foreground p-4 sm:gap-4 sm:p-5">
          <Pessoa p={a} />
          <Pessoa p={b} />
        </div>
        <dl className="flex flex-col px-4 sm:px-5">
          {linhas.map((l) => (
            <div key={l.rotulo} className="grid grid-cols-2 gap-x-3 gap-y-1 border-b border-border py-3 sm:gap-x-4">
              <dt className="col-span-2 text-sm text-muted-foreground">{l.rotulo}</dt>
              <dd className="numero text-xl">{l.a}</dd>
              <dd className="numero text-xl">{l.b}</dd>
            </div>
          ))}
        </dl>
        {convergencia && convergencia.votacoes_em_comum > 0 && (
          <div className="flex flex-col gap-2 px-4 pt-4 sm:px-5">
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
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
          <Link href={`/comparar?a=${a.id}&b=${b.id}`} className="botao-linha">
            Ver a comparação completa
          </Link>
          <Link href="/comparar" className="alvo-link text-sm underline underline-offset-4">
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
        <span className="line-clamp-2 break-words text-sm font-semibold leading-tight">{p.nome_parlamentar}</span>
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
    titulo: "Projetos e votações",
    texto: "Procure um projeto pelo número ou assunto: o que diz, quem votou e o que disseram no Plenário.",
    href: "/projetos",
    icone: (
      <svg aria-hidden viewBox="0 0 24 24" className={ICONE} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="10.5" cy="10.5" r="6" />
        <path d="M15 15l5 5M8 10.5h5M10.5 8v5" />
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
    titulo: "Impostos e repasses por estado e cidade",
    texto: "Quanto a União arrecada e repassa em cada estado e município, no mapa, e as emendas pagas à sua cidade.",
    href: "/impostos-e-repasses",
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

function PorQuePanoptico() {
  return (
    <section aria-labelledby="porque-titulo" className="revelar grid items-center gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,18rem)] md:gap-16">
      <div className="flex flex-col gap-3">
        <p className="sobretitulo">A ideia</p>
        <h2 id="porque-titulo" className="text-4xl leading-tight text-balance">
          Por que &ldquo;Panóptico&rdquo;?
        </h2>
        <p className="max-w-lg text-muted-foreground">
          Uma prisão imaginada em 1791 para vigiar todos, usada aqui ao contrário: quem está sob o
          olhar de todos é quem exerce o mandato.
        </p>
        <div>
          <Link href="/o-panoptico" className="botao-linha">
            Entenda a ideia →
          </Link>
        </div>
      </div>
      <PanopticoDesenho estado={4} idBase="home" className="mx-auto h-auto w-full max-w-64 md:order-last" />
    </section>
  );
}
