"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useRef, useState } from "react";

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

/**
 * Página /o-panoptico como história ao rolar. O desenho fica fixo (sticky) e cada passo de texto,
 * ao passar da linha de leitura, muda o estado do desenho. Sem JavaScript os passos aparecem em
 * sequência e o desenho fica no estado final. Os textos são HTML normal, lidos em ordem por
 * leitores de tela; o desenho tem descrição própria.
 */
export function HistoriaPanoptico({ dados, cep }: { dados: DadosDaHistoria; cep: ReactNode }) {
  // Sem JS (ou antes de hidratar), vale o estado final.
  const [ativo, setAtivo] = useState<EstadoPanoptico>(5);
  const [selecionado, setSelecionado] = useState<number | null>(dados.pessoas.length > 0 ? 0 : null);
  const figura = useRef<HTMLDivElement>(null);
  const lista = useRef<HTMLOListElement>(null);

  useEffect(() => {
    let quadro = 0;
    const calcular = () => {
      quadro = 0;
      const H = window.innerHeight;
      const grande = window.matchMedia("(min-width: 1024px)").matches;
      const baseFigura = figura.current?.getBoundingClientRect().bottom ?? 0;
      // Linha de leitura: no meio da tela no computador; no celular, abaixo do desenho fixo.
      const linha = grande ? H * 0.5 : baseFigura + (H - baseFigura) * 0.4;
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
    window.addEventListener("scroll", agendar, { passive: true });
    window.addEventListener("resize", agendar);
    return () => {
      window.removeEventListener("scroll", agendar);
      window.removeEventListener("resize", agendar);
      if (quadro) cancelAnimationFrame(quadro);
    };
  }, []);

  const pessoa = selecionado !== null ? dados.pessoas[selecionado] : undefined;

  return (
    <div className="relative lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:gap-16">
      <div
        ref={figura}
        className="sticky top-14 z-10 -mx-4 flex h-[40svh] justify-center border-b border-border bg-background px-4 py-2 lg:top-20 lg:col-start-2 lg:row-start-1 lg:mx-0 lg:h-[calc(100svh-7rem)] lg:items-center lg:self-start lg:border-0 lg:px-0"
      >
        <PanopticoDesenho
          estado={ativo}
          pessoas={dados.pessoas}
          selecionado={selecionado}
          onSelecionar={setSelecionado}
          idBase="historia"
          className="h-full w-auto max-w-full lg:h-auto lg:w-full"
        />
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
          <Exemplo dados={dados} selecionado={selecionado} onSelecionar={setSelecionado} pessoa={pessoa} />
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

        <Passo rotulo="Sua vez" titulo="Agora veja quem te representa">
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
  children,
}: {
  rotulo: string;
  titulo: string;
  children: ReactNode;
}) {
  return (
    <li className="flex min-h-[48svh] flex-col justify-center gap-3 py-8 lg:min-h-[85svh]">
      <p className="sobretitulo">{rotulo}</p>
      <h2 className="text-[2rem] leading-[1.08] text-balance sm:text-5xl">{titulo}</h2>
      <div className="flex max-w-prose flex-col gap-3 text-lg leading-relaxed text-pretty text-muted-foreground">{children}</div>
    </li>
  );
}

function Exemplo({
  dados,
  pessoa,
  selecionado,
  onSelecionar,
}: {
  dados: DadosDaHistoria;
  pessoa?: PessoaDaHistoria;
  selecionado: number | null;
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
      <p>Exemplo, com os senadores de Santa Catarina (os mesmos da página inicial). Toque num nome:</p>
      <div role="group" aria-label="Senadores de exemplo" className="flex flex-wrap gap-2">
        {dados.pessoas.map((p, i) => (
          <button
            key={p.id}
            type="button"
            aria-pressed={selecionado === i}
            onClick={() => onSelecionar(i)}
            className="flex min-h-12 items-center gap-2 rounded-[2px] border border-foreground/35 py-1 pr-3 pl-1 text-left text-sm text-foreground transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze aria-pressed:border-bronze aria-pressed:ring-1 aria-pressed:ring-bronze motion-reduce:transition-none"
          >
            <Foto parlamentar={p} largura={30} />
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
