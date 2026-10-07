import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "Panóptico: quem te representa, às claras", template: "%s · Panóptico" },
  description:
    "Digite seu CEP e veja quem te representa no Congresso, com dados oficiais e link para a fonte.",
};

export const viewport: Viewport = {
  themeColor: "#fbf8f3",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="mx-auto w-full max-w-3xl px-4 pt-4">
          <Link
            href="/"
            className="text-lg font-bold tracking-tight text-primary focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            Panóptico
          </Link>
        </header>
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">{children}</main>
        <footer className="mx-auto w-full max-w-3xl px-4 pb-6 text-xs text-muted-foreground">
          Dados públicos e oficiais da Câmara dos Deputados, do Senado Federal e do ViaCEP. O
          Panóptico não guarda o seu CEP.
        </footer>
      </body>
    </html>
  );
}
