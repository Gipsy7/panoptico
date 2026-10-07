import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";

import { SITE_URL } from "@/lib/site";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const CONTATO = process.env.NEXT_PUBLIC_CONTATO_EMAIL;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "Panóptico: quem te representa, às claras", template: "%s · Panóptico" },
  description:
    "Digite seu CEP e veja quem te representa no Congresso, com dados oficiais e link para a fonte.",
  openGraph: {
    siteName: "Panóptico",
    locale: "pt_BR",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#fbf8f3",
};

const LINK = "underline underline-offset-2 hover:text-foreground";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2 focus:ring-3 focus:ring-ring/50"
        >
          Pular para o conteúdo
        </a>
        <header className="mx-auto w-full max-w-3xl px-4 pt-4">
          <Link
            href="/"
            className="text-lg font-bold tracking-tight text-primary focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            Panóptico
          </Link>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
          {children}
        </main>
        <footer className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-4 pb-6 text-xs text-muted-foreground">
          <nav aria-label="Rodapé" className="flex flex-wrap gap-x-4 gap-y-1">
            <Link href="/sobre-as-fontes" className={LINK}>
              Sobre as fontes
            </Link>
            <Link href="/privacidade" className={LINK}>
              Privacidade
            </Link>
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
        </footer>
      </body>
    </html>
  );
}
