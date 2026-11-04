import type { Metadata } from "next";
import Link from "next/link";

import { DicionarioIndice } from "@/components/dicionario-indice";
import { JsonLd } from "@/components/json-ld";
import { Migalhas } from "@/components/ui/migalhas";
import { DICIONARIO_CONFERIDO_EM, TERMOS } from "@/lib/dicionario";
import { formatarData } from "@/lib/formato";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Dicionário da política",
  description:
    "As palavras da política em português do dia a dia: PEC, cota parlamentar, quórum, emenda Pix e outras, cada uma com a fonte oficial.",
  alternates: { canonical: "/dicionario" },
};

export default function DicionarioPage() {
  return (
    <article className="pagina-secoes">
      <JsonLd
        dados={{
          "@context": "https://schema.org",
          "@type": "DefinedTermSet",
          name: "Dicionário da política do Panóptico",
          inLanguage: "pt-BR",
          hasDefinedTerm: TERMOS.map((t) => ({
            "@type": "DefinedTerm",
            name: t.termo,
            alternateName: t.oficial,
            description: t.explicacao,
            url: `${SITE_URL}/dicionario#${t.id}`,
          })),
        }}
      />
      <header className="flex flex-col gap-[var(--esp-2)]">
        <Migalhas itens={[{ rotulo: "Início", href: "/" }, { rotulo: "Dicionário" }]} />
        <p className="sobretitulo">Dicionário</p>
        <h1 className="titulo-pagina">As palavras da política, em português do dia a dia</h1>
        <p className="text-muted-foreground">
          {TERMOS.length} palavras que aparecem no site. Cada uma com a explicação simples, um exemplo do
          site e a fonte oficial (Constituição, Regimento Interno da Câmara ou a lei). Toque numa palavra
          para ler a explicação inteira.
        </p>
      </header>

      <DicionarioIndice />

      <p className="text-sm text-muted-foreground">
        Explicações conferidas nos textos oficiais em {formatarData(DICIONARIO_CONFERIDO_EM)}. Ficaram de fora
        as palavras que o site ainda não usa. Não achou a sua?{" "}
        <Link href="/pergunte" className="underline underline-offset-2">
          Pergunte ao Argos
        </Link>
        .
      </p>
    </article>
  );
}
