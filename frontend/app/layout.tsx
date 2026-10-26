import type { Metadata, Viewport } from "next";
import { Geist, Newsreader } from "next/font/google";
import Link from "next/link";

import { Logo, Marca } from "@/components/logo";
import { MenuPrincipal } from "@/components/menu-principal";
import { CONTATO_EMAIL, SITE_URL } from "@/lib/site";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Serifa editorial dos títulos, dos números em destaque e do nome na logo.
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  axes: ["opsz"],
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  alternates: { canonical: "./" },
  title: { default: "Panóptico: quem te representa, às claras", template: "%s · Panóptico" },
  description:
    "Digite seu CEP e veja quem te representa no Congresso, com dados oficiais e link para a fonte.",
  openGraph: {
    siteName: "Panóptico.social",
    locale: "pt_BR",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f1ea" },
    { media: "(prefers-color-scheme: dark)", color: "#1c1a17" },
  ],
};

const SALTO =
  "sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2 focus:ring-3 focus:ring-ring/50";

// Atalhos do eMAG (accesskey): Alt+1 conteúdo, Alt+2 menu, Alt+3 busca.
const SALTOS = [
  { tecla: "1", href: "#conteudo", rotulo: "Pular para o conteúdo" },
  { tecla: "2", href: "#menu-principal", rotulo: "Ir para o menu" },
  { tecla: "3", href: "/#cep", rotulo: "Ir para a busca por CEP" },
];

const LINK = "alvo-link underline underline-offset-2 hover:text-foreground";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt-BR"
      suppressHydrationWarning
      className={`${geistSans.variable} ${newsreader.variable} h-full antialiased`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              'document.documentElement.dataset.js="1";try{var t=localStorage.getItem("tema");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}',
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">
        <div className="contents">
          {SALTOS.map((l) => (
            // eslint-disable-next-line jsx-a11y/no-access-key -- atalhos 1, 2 e 3 pedidos pelo eMAG
            <a key={l.tecla} href={l.href} accessKey={l.tecla} className={SALTO}>
              {l.rotulo}
            </a>
          ))}
        </div>
        <header
          style={{ viewTransitionName: "site-header" }}
          className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur-md"
        >
          <div id="menu-principal" tabIndex={-1} className="outline-none mx-auto flex w-full max-w-5xl items-center min-h-14 flex-wrap justify-between gap-x-4 gap-y-1 px-4 xl:flex-nowrap">
            <Link
              href="/"
              aria-label="Panóptico.social, página inicial"
              className="shrink-0 rounded-md"
            >
              <Logo tamanho={28} />
            </Link>
            <MenuPrincipal />
          </div>
        </header>
        <main id="conteudo" tabIndex={-1} className="outline-none mx-auto w-full max-w-3xl flex-1 px-4 py-8 has-[[data-largura=larga]]:max-w-5xl">
          {children}
        </main>
        <footer className="mt-8 border-t border-border/70">
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <Marca tamanho={28} traco={2.4} className="shrink-0 text-bronze" />
              <p className="max-w-prose text-sm leading-relaxed">
                O{" "}
                <Link href="/o-panoptico" className="underline underline-offset-2 hover:text-foreground">
                  panóptico
                </Link>{" "}
                era uma prisão em que um vigia, de uma torre, via todos sem ser visto. Aqui é o
                contrário: todos podem ver quem os representa.
              </p>
            </div>
            <nav aria-label="Rodapé" className="flex flex-wrap gap-x-6 gap-y-1">
              <Link href="/partidos" className={LINK}>
                Dinheiro dos partidos
              </Link>
              <Link href="/o-panoptico" className={LINK}>
                O que é o Panóptico
              </Link>
              <Link href="/perguntas" className={LINK}>
                Perguntas frequentes
              </Link>
              <Link href="/sobre-as-fontes" className={LINK}>
                Sobre as fontes
              </Link>
              <Link href="/privacidade" className={LINK}>
                Privacidade
              </Link>
              <Link href="/acessibilidade" className={LINK}>
                Acessibilidade
              </Link>
              <a href="https://github.com/Gipsy7/panoptico" className={LINK}>
                Código aberto
              </a>
              <Link href="/apoie" className={LINK}>
                Apoie
              </Link>
              <Link href="/apoiadores" className={LINK}>
                Apoiadores
              </Link>
              <a href={`mailto:${CONTATO_EMAIL}`} className={LINK}>
                {CONTATO_EMAIL}
              </a>
            </nav>
            <p>
              Dados públicos e oficiais da Câmara dos Deputados, do Senado Federal, do Portal da
              Transparência e do IBGE. O Panóptico não guarda o seu CEP.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
