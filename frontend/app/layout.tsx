import type { Metadata, Viewport } from "next";
import { Fraunces, Geist } from "next/font/google";
import Link from "next/link";

import { Logo, Marca } from "@/components/logo";
import { SITE_URL } from "@/lib/site";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Serifa dos títulos e do nome na logo: dá o tom editorial.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz", "SOFT"],
});

const CONTATO = process.env.NEXT_PUBLIC_CONTATO_EMAIL;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
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
  themeColor: "#faf6ef",
};

const LINK = "underline underline-offset-2 hover:text-foreground";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2 focus:ring-3 focus:ring-ring/50"
        >
          Pular para o conteúdo
        </a>
        <header
          style={{ viewTransitionName: "site-header" }}
          className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur-md"
        >
          <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-4 py-3">
            <Link
              href="/"
              aria-label="Panóptico.social, página inicial"
              className="rounded-md focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              <Logo tamanho={28} />
            </Link>
            <nav aria-label="Principal" className="flex gap-4 text-sm">
              <Link href="/parlamentares" className="underline-offset-4 hover:underline">
                Todos os parlamentares
              </Link>
            </nav>
          </div>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
          {children}
        </main>
        <footer className="mt-8 border-t border-border/70">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-8 text-xs text-muted-foreground">
            <div className="flex items-start gap-3">
              <Marca tamanho={28} className="shrink-0 text-primary" />
              <p className="max-w-prose text-sm leading-relaxed">
                O panóptico era uma prisão em que um vigia, de uma torre, via todos sem ser visto.
                Aqui é o contrário: todos podem ver quem os representa.
              </p>
            </div>
            <nav aria-label="Rodapé" className="flex flex-wrap gap-x-4 gap-y-1">
              <Link href="/sobre-as-fontes" className={LINK}>
                Sobre as fontes
              </Link>
              <Link href="/privacidade" className={LINK}>
                Privacidade
              </Link>
              <a href="https://github.com/Gipsy7/panoptico" className={LINK}>
                Código aberto
              </a>
              {CONTATO && (
                <a href={`mailto:${CONTATO}`} className={LINK}>
                  Contato
                </a>
              )}
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
