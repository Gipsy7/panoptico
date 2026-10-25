"use client";

import Link from "next/link";
import { type ReactNode, Suspense, use, useEffect, useRef, useState } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import { Foto } from "@/components/parlamentar-card";
import { type EstadoPanoptico, PanopticoDesenho, type PessoaNaTorre } from "@/components/panoptico-desenho";

/** Um parlamentar mostrado dentro da torre, com um número oficial e a média da Casa ao lado. */
export type PessoaDaHistoria = PessoaNaTorre & {
  casaNome: string; // "Senado"
  gastos: string; // já formatado
  media: string | null; // já formatada
};

export type DadosDaHistoria = {
  pessoas: PessoaDaHistoria[];
  indisponivel: boolean;
  ano: number | null;
  fonte: { nome: string; url: string; atualizadoEm: string | null } | null;
};

const LINK = "underline underline-offset-2";
const NOMES_DOS_PASSOS = ["A cela", "De onde vem", "Foucault", "A inversão", "Os limites", "Sua vez"];
const VAZIO: DadosDaHistoria = { pessoas: [], indisponivel: false, ano: null, fonte: null };

/**
 * Página /o-panoptico como história ao rolar. O desenho fica fixo (sticky) e cada passo de texto,
 * ao passar da linha de leitura (60% da altura no celular, 50% no computador), muda o estado do
 * desenho. A história monta uma vez só: os dados dos senadores chegam por uma promessa lida apenas
 * no trecho do exemplo (dentro de um Suspense) e entram no desenho por estado, sem remontá-lo.
 *
 * O estado inicial é 0, o mesmo do HTML do servidor, e as transições só ligam depois do primeiro
 * cálculo (dois quadros), para nada animar ao carregar. Sem JavaScript o desenho fica na cela
 * (passo 1) enquanto os textos aparecem em sequência. Os textos são HTML normal, lidos em ordem por
 * leitores de tela; o desenho tem descrição própria.
 */
export function HistoriaPanoptico({ dados, cep }: { dados: Promise<DadosDaHistoria>; cep: ReactNode }) {
  const [ativo, setAtivo] = useState<EstadoPanoptico>(0);
  const [animar, setAnimar] = useState(false);
  const [carregados, setCarregados] = useState<DadosDaHistoria>(VAZIO);
  const [selecionado, setSelecionado] = useState(0);
  const lista = useRef<HTMLOListElement>(null);

  useEffect(() => {
    let quadro = 0;
    const calcular = () => {
      quadro = 0;
      const grande = window.matchMedia("(min-width: 1024px)").matches;
      const linha = window.innerHeight * (grande ? 0.5 : 0.6);
      let escolhido = 0;
      const passos = lista.current ? Array.from(lista.current.children) : [];
      passos.forEach((el, i) => {
        if (el.getBoundingClientRect().top <= linha) escolhido = i;
      });
      const noFim = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
      if (noFim) escolhido = passos.length - 1;
      setAtivo(escolhido as EstadoPanoptico);
    };
    const agendar = () => {
      if (!quadro) quadro = requestAnimationFrame(calcular);
    };
    calcular();
    // As transições só ligam depois do primeiro cálculo pintado.
    const ligar = requestAnimationFrame(() => requestAnimationFrame(() => setAnimar(true)));
    window.addEventListener("scroll", agendar, { passive: true });
    window.addEventListener("resize", agendar);
    document.fonts?.ready.then(agendar);
    return () => {
      window.removeEventListener("scroll", agendar);
      window.removeEventListener("resize", agendar);
      if (quadro) cancelAnimationFrame(quadro);
      cancelAnimationFrame(ligar);
    };
  }, []);

  return (
    <div className="relative lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:gap-16">
      <div className="sticky top-14 z-10 -mx-4 border-b border-border bg-background px-4 pt-2 pb-1 lg:top-20 lg:col-start-2 lg:row-start-1 lg:mx-0 lg:flex lg:h-[calc(100svh-7rem)] lg:flex-col lg:justify-center lg:gap-2 lg:self-start lg:border-0 lg:p-0">
        <div className="[--q:min(30svh,240px)] lg:overflow-hidden">
          <PanopticoDesenho
            estado={ativo}
            pessoas={carregados.pessoas}
            selecionado={carregados.pessoas.length > 0 ? selecionado : null}
            onSelecionar={setSelecionado}
            idBase="historia"
            animar={animar}
            className="mx-auto size-(--q) lg:aspect-square lg:size-auto lg:w-full"
          />
        </div>
        <div className="flex min-h-8 items-center justify-between gap-3 text-[0.8125rem] text-muted-foreground lg:justify-center">
          <span aria-hidden className="flex gap-1.5">
            {NOMES_DOS_PASSOS.map((n, i) => (
              <span key={n} className={`size-2 rounded-full ${i <= ativo ? "bg-bronze" : "bg-border"}`} />
            ))}
          </span>
          <span className="text-right">
            Passo {ativo + 1} de {NOMES_DOS_PASSOS.length} · {NOMES_DOS_PASSOS[ativo]}
          </span>
        </div>
      </div>

      <ol ref={lista} className="flex flex-col lg:col-start-1 lg:row-start-1">
        <Passo rotulo="A cela" titulo="Você está numa cela">
          <p>
            Imagine uma cela com uma luz forte vindo de uma torre no meio do pátio. A janela da
            torre é escura: você não consegue ver se há alguém olhando de lá.
          </p>
          <p>Como não tem como saber, você passa a agir como se alguém estivesse.</p>
        </Passo>

        <Passo rotulo="De onde vem" titulo="Uma prisão desenhada em 1791">
          <p>
            O filósofo inglês Jeremy Bentham descreveu o projeto de uma prisão chamada panóptico
            (do grego, &ldquo;que vê tudo&rdquo;). As celas formam um anel em volta de uma torre
            central. De dentro da torre, um vigia enxerga todas as celas; de dentro das celas,
            ninguém enxerga a torre.
          </p>
        </Passo>

        <Passo rotulo="Foucault" titulo="O olhar que funciona sozinho">
          <p>
            Em <em>Vigiar e punir</em> (1975), o filósofo francês Michel Foucault usou o panóptico
            para explicar uma forma de poder: quem pode ser visto a qualquer momento, sem saber
            quando, passa a se vigiar por conta própria.
          </p>
          <p>Na leitura dele, a torre nem precisa ter alguém dentro para o olhar funcionar.</p>
        </Passo>

        <Passo rotulo="A inversão" titulo="Agora é ao contrário">
          <p>
            No Panóptico.social, a torre virou vidro e o olhar mudou de lado. Quem é visto é quem
            exerce mandato público, e quem olha é você. Os dados já são públicos, mas estão
            espalhados em sites de órgãos diferentes. Aqui eles ficam juntos, com a fonte e a data.
          </p>
          <Suspense fallback={<p className="min-h-40 text-base">Carregando o exemplo...</p>}>
            <ExemploCarregado
              promessa={dados}
              selecionado={selecionado}
              onSelecionar={setSelecionado}
              onDados={setCarregados}
            />
          </Suspense>
        </Passo>

        <Passo rotulo="Os limites" titulo="O que o site não faz">
          <ul className="flex list-disc flex-col gap-1 pl-5">
            <li>Não vigia quem usa o site: não há cadastro e o CEP digitado não é guardado.</li>
            <li>Não dá nota, não faz ranking e não classifica ninguém: mostra o número e a média da Casa ao lado.</li>
            <li>Só usa dados públicos e oficiais.</li>
          </ul>
          <p className="text-base">
            Detalhes em{" "}
            <Link href="/privacidade" className={LINK}>
              Privacidade
            </Link>{" "}
            e em{" "}
            <Link href="/sobre-as-fontes" className={LINK}>
              Sobre as fontes
            </Link>
            .
          </p>
        </Passo>

        <Passo ultimo rotulo="Sua vez" titulo="Agora veja quem te representa">
          <p>Digite o seu CEP e veja, do Congresso à câmara da cidade, quem exerce o mandato por você.</p>
          <div id="cep" className="max-w-md scroll-mt-40 border-t border-foreground pt-6">
            {cep}
          </div>
        </Passo>
      </ol>
    </div>
  );
}

function Passo({
  rotulo,
  titulo,
  ultimo = false,
  children,
}: {
  rotulo: string;
  titulo: string;
  ultimo?: boolean;
  children: ReactNode;
}) {
  return (
    <li
      className={`flex flex-col gap-3 py-6 ${ultimo ? "min-h-[70svh] justify-start" : "min-h-[42svh] justify-center lg:min-h-[85svh]"}`}
    >
      <p className="sobretitulo">{rotulo}</p>
      <h2 className="text-[1.9rem] leading-[1.1] text-balance lg:text-5xl">{titulo}</h2>
      <div className="flex max-w-prose flex-col gap-3 text-[1.0625rem] leading-relaxed text-pretty text-muted-foreground lg:text-lg">{children}</div>
    </li>
  );
}

/** Lê a promessa dos dados (suspende só aqui), entrega as pessoas ao desenho e mostra o exemplo. */
function ExemploCarregado({
  promessa,
  selecionado,
  onSelecionar,
  onDados,
}: {
  promessa: Promise<DadosDaHistoria>;
  selecionado: number;
  onSelecionar: (i: number) => void;
  onDados: (d: DadosDaHistoria) => void;
}) {
  const dados = use(promessa);
  useEffect(() => onDados(dados), [dados, onDados]);
  return <Exemplo dados={dados} selecionado={selecionado} onSelecionar={onSelecionar} pessoa={dados.pessoas[selecionado]} />;
}

function Exemplo({
  dados,
  pessoa,
  selecionado,
  onSelecionar,
}: {
  dados: DadosDaHistoria;
  pessoa?: PessoaDaHistoria;
  selecionado: number;
  onSelecionar: (i: number) => void;
}) {
  if (dados.indisponivel || dados.pessoas.length === 0) {
    return (
      <p className="text-base">
        Não foi possível carregar os exemplos agora. Na busca por CEP você vê os representantes reais.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3 text-base">
      <p>Exemplo, com os senadores de Santa Catarina (os mesmos da página inicial). Toque ou clique num nome:</p>
      <div role="group" aria-label="Senadores de exemplo" className="flex flex-wrap gap-2">
        {dados.pessoas.map((p, i) => (
          <button
            key={p.id}
            type="button"
            aria-pressed={selecionado === i}
            onClick={() => onSelecionar(i)}
            className="flex min-h-12 items-center gap-2 rounded-[2px] border border-foreground/35 py-1 pr-3 pl-1 text-left text-sm text-foreground transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze aria-pressed:border-bronze aria-pressed:ring-1 aria-pressed:ring-bronze motion-reduce:transition-none"
          >
            <Foto parlamentar={p} largura={30} decorativa />
            <span className="line-clamp-2 font-medium">{p.nome_parlamentar}</span>
          </button>
        ))}
      </div>
      {pessoa && (
        <div aria-live="polite" className="flex flex-col gap-2 rounded-[2px] border border-border bg-card p-4 text-foreground">
          <div className="flex flex-col gap-0.5">
            <span className="text-lg font-semibold">{pessoa.nome_parlamentar}</span>
            <span className="flex gap-1">
              {pessoa.partido && <span className="pilula">{pessoa.partido}</span>}
              <span className="pilula">{pessoa.uf}</span>
              <span className="pilula">{pessoa.casaNome}</span>
            </span>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Gastos do gabinete em {dados.ano}</p>
            <p className="numero text-2xl">{pessoa.gastos}</p>
            {pessoa.media && <p className="text-sm text-muted-foreground">Média do {pessoa.casaNome}: {pessoa.media}</p>}
          </div>
          <Link href={`/parlamentar/${pessoa.id}`} className={`${LINK} text-sm`}>
            Ver o perfil completo
          </Link>
        </div>
      )}
      {dados.fonte && <FonteRodape fonte={dados.fonte.nome} url={dados.fonte.url} atualizadoEm={dados.fonte.atualizadoEm} />}
    </div>
  );
}
