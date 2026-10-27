import type { Metadata } from "next";

import { LinkExterno } from "@/components/link-externo";

export const metadata: Metadata = {
  title: "Acessibilidade",
  description: "O que o Panóptico faz para ser usado por todos, como conferimos e o que ainda falta.",
};

const REPOSITORIO = "https://github.com/Gipsy7/panoptico/issues";

export default function AcessibilidadePage() {
  return (
    <article className="pagina-secoes">
      <header className="flex flex-col gap-[var(--esp-2)]">
        <p className="sobretitulo">Para todos</p>
        <h1 className="titulo-pagina">Acessibilidade</h1>
        <p className="text-muted-foreground">
          Resumo: o site foi feito para ser usado sem mouse, com leitor de tela e com letra grande.
          Esta página diz o que conferimos e o que ainda não conseguimos conferir.
        </p>
      </header>

      <Secao titulo="Nossa meta">
        <p>
          Seguir as regras internacionais de acessibilidade da web, no nível AA, e o modelo do
          governo brasileiro para sites públicos.
        </p>
        <p className="text-sm">WCAG 2.2 nível AA e eMAG 3.1.</p>
      </Secao>

      <Secao titulo="O que dá para fazer">
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>
            Usar o site só pelo teclado: Tab para avançar, Enter para abrir, Esc para fechar e as
            setas no mapa e nas listas de busca.
          </li>
          <li>Usar com leitor de tela (NVDA, TalkBack, VoiceOver).</li>
          <li>Aumentar a letra até 200% sem perder conteúdo.</li>
          <li>Usar em telas a partir de 320 px de largura.</li>
          <li>Trocar para o modo escuro.</li>
          <li>Reduzir o movimento: se o seu aparelho pede menos animação, o site respeita.</li>
        </ul>
      </Secao>

      <Secao titulo="Atalhos de teclado">
        <p>
          Em toda página há três atalhos para pular direto a uma parte. Eles aparecem no canto da
          tela quando você aperta Tab.
        </p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>
            <kbd>1</kbd>: ir para o conteúdo.
          </li>
          <li>
            <kbd>2</kbd>: ir para o menu.
          </li>
          <li>
            <kbd>3</kbd>: ir para a busca por CEP.
          </li>
        </ul>
        <p>A combinação depende do navegador:</p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>Chrome e Edge no Windows ou Linux: Alt + número.</li>
          <li>Firefox no Windows ou Linux: Alt + Shift + número.</li>
          <li>Safari e outros navegadores no Mac: Control + Option + número.</li>
        </ul>
        <p className="text-sm">Atalhos de acesso (accesskey), recomendados pelo eMAG.</p>
      </Secao>

      <Secao titulo="Como conferimos">
        <p>
          Todos os dias, testes automáticos rodam contra o site no ar: verificação de
          acessibilidade em 13 páginas, uso só pelo teclado, tela de 320 px de largura e letra a
          200%.
        </p>
        <p className="text-sm">axe-core com regras WCAG 2.2 AA, executado com Playwright.</p>
        <p>
          O que ainda não foi feito: não houve teste com pessoas que usam leitor de tela no dia a
          dia. Testes automáticos não pegam tudo.
        </p>
      </Secao>

      <Secao titulo="Limitações conhecidas">
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>
            Os desenhos (os prédios e o panóptico) e o mapa têm alternativa em texto ou em lista,
            mas a experiência visual é mais rica.
          </li>
          <li>Os nomes das cidades dentro do mapa são pequenos; a mesma informação está na lista.</li>
          <li>
            Os documentos e sites dos órgãos oficiais (PDFs, páginas de câmaras e tribunais, que o
            Panóptico só aponta) não são controlados por nós e podem não ser acessíveis.
          </li>
        </ul>
      </Secao>

      <Secao titulo="Encontrou um problema?">
        <p>
          Abra uma{" "}
          <LinkExterno href={REPOSITORIO} className="underline underline-offset-2">
            issue no GitHub do projeto
          </LinkExterno>{" "}
          dizendo qual página, qual aparelho e qual leitor de tela (se usa um). Vamos olhar.
        </p>
      </Secao>

      <p className="text-sm text-muted-foreground">Última revisão desta página: 25/10/2026.</p>
    </article>
  );
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2 text-muted-foreground">
      <h2 className="text-lg font-semibold text-foreground">{titulo}</h2>
      {children}
    </section>
  );
}
