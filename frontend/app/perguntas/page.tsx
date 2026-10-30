import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { JsonLd, LICENCA_DADOS_URL } from "@/components/json-ld";
import { PERGUNTAS_FREQUENTES } from "@/lib/perguntas";
import { CONTATO_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Perguntas frequentes",
  description:
    "De onde vêm os dados, se o site guarda o CEP, o que é a média da Casa, como corrigir um número e como usar os dados.",
};

const LINK = "underline underline-offset-2";
const REPO = "https://github.com/Gipsy7/panoptico";

const RESPOSTAS: Record<string, ReactNode> = {
  fonte: (
    <>
      Todos os dados vêm de fontes públicas e oficiais, como a Câmara dos Deputados, o Senado
      Federal, o Portal da Transparência, o TSE e o IBGE. Cada seção tem o link da fonte e a data
      da última atualização. A página{" "}
      <Link href="/sobre-as-fontes" className={LINK}>
        Sobre as fontes
      </Link>{" "}
      lista as fontes e explica como cada número é calculado.
    </>
  ),
  frequencia: (
    <>
      Os dados federais são atualizados todos os dias. As câmaras municipais e as assembleias são
      atualizadas toda semana, e algumas fontes, como as contas dos partidos e das cidades, uma
      vez por mês. A data de cada fonte aparece na própria seção e em{" "}
      <Link href="/sobre-as-fontes" className={LINK}>
        Sobre as fontes
      </Link>
      .
    </>
  ),
  cobertura: (
    <>
      Nem todo órgão publica seus dados de forma aberta. Quando a fonte não existe, bloqueia o
      acesso automático ou ainda não foi conectada, o site diz o que falta. Nos casos em que o
      acesso foi pedido pela Lei de Acesso à Informação, o pedido fica aberto ao público. A
      página de{" "}
      <Link href="/sobre-as-fontes/cobertura" className={LINK}>
        cobertura
      </Link>{" "}
      mostra a situação estado por estado.
    </>
  ),
  cep: (
    <>
      Não. O CEP é usado só para descobrir a cidade e o estado e não é gravado em banco de
      dados. A localização, se você escolher usá-la, é processada no seu aparelho e não é enviada
      a nenhum servidor. Não há cadastro nem cookies de rastreamento ou publicidade. Os detalhes
      estão na página de{" "}
      <Link href="/privacidade" className={LINK}>
        privacidade
      </Link>
      .
    </>
  ),
  nota: (
    <>
      Não. O Panóptico não é ligado a nenhum partido, mandato ou campanha. O site não dá nota,
      não faz ranking e não classifica ninguém: mostra o número, a média da Casa ao lado e o
      link da fonte. Ele não aceita doações de partidos, mandatos,
      gabinetes ou campanhas eleitorais, e doações não mudam nada no que o site mostra. Veja a
      seção de independência em{" "}
      <Link href="/apoie" className={LINK}>
        Apoie
      </Link>
      .
    </>
  ),
  "media-casa": (
    <>
      É a média entre os parlamentares em exercício na mesma Casa (Câmara ou Senado). Quem não
      tem nada no item, por exemplo quem não gastou, entra na conta com zero. Ela aparece ao lado
      do número para dar uma referência, sem julgamento. Como cada número é calculado está em{" "}
      <Link href="/sobre-as-fontes" className={LINK}>
        Sobre as fontes
      </Link>
      .
    </>
  ),
  erro: (
    <>
      Os dados são copiados das fontes oficiais sem edição. Confira primeiro a data de
      atualização, porque as fontes corrigem dados com frequência. Se ainda estiver diferente,
      escreva para{" "}
      <a href={`mailto:${CONTATO_EMAIL}`} className={LINK}>
        {CONTATO_EMAIL}
      </a>{" "}
      ou abra uma{" "}
      <a href={`${REPO}/issues`} className={LINK}>
        issue no GitHub
      </a>{" "}
      com o link do perfil e da fonte.
    </>
  ),
  "quem-paga": (
    <>
      O trabalho de desenvolvimento é voluntário e o{" "}
      <a href={REPO} className={LINK}>
        código é aberto
      </a>
      . O site é gratuito, sem anúncios e sem cadastro. Os custos de manter tudo no ar são
      pequenos e pagos por doações; a página{" "}
      <Link href="/apoie" className={LINK}>
        Apoie
      </Link>{" "}
      mostra quanto custa. Quem autorizou o nome aparece na lista de{" "}
      <Link href="/apoiadores" className={LINK}>
        apoiadores
      </Link>
      .
    </>
  ),
  dados: (
    <>
      Sim. Os arquivos de dados abertos do Panóptico estão sob a licença Creative Commons
      Atribuição 4.0 (CC BY 4.0): podem ser copiados, adaptados e usados para qualquer fim,
      inclusive comercial, com crédito ao Panóptico e à fonte oficial. Em caso de dúvida, vale o
      que consta na fonte oficial. Veja os termos em{" "}
      <a href={LICENCA_DADOS_URL} className={LINK}>
        LICENCA-DADOS.md
      </a>
      .
    </>
  ),
};

const PERGUNTAS = PERGUNTAS_FREQUENTES;

export default function PerguntasPage() {
  return (
    <article className="pagina-secoes">
      <JsonLd
        dados={{
          "@context": "https://schema.org",
          "@type": "FAQPage",
          inLanguage: "pt-BR",
          mainEntity: PERGUNTAS.map((p) => ({
            "@type": "Question",
            name: p.pergunta,
            acceptedAnswer: { "@type": "Answer", text: p.texto },
          })),
        }}
      />
      <header className="flex flex-col gap-2">
        <p className="sobretitulo">Dúvidas</p>
        <h1 className="titulo-pagina">Perguntas frequentes</h1>
        <p className="text-muted-foreground">
          Respostas curtas sobre de onde vêm os dados, privacidade e como usar o site.
        </p>
      </header>

      <div className="lista-fios flex flex-col">
        {PERGUNTAS.map((p) => (
          <details key={p.id} id={p.id} className="group py-1">
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-4 py-2 text-lg font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze [&::-webkit-details-marker]:hidden">
              <span>{p.pergunta}</span>
              <span aria-hidden className="shrink-0 text-bronze-texto transition-transform duration-200 group-open:rotate-45 motion-reduce:transition-none">
                +
              </span>
            </summary>
            <p className="max-w-prose pb-4 text-muted-foreground">{RESPOSTAS[p.id]}</p>
          </details>
        ))}
      </div>

      <p className="text-muted-foreground">
        Prefere perguntar com as suas palavras? Use o{" "}
        <Link href="/pergunte" className={LINK}>
          Argos
        </Link>
        , um assistente de respostas prontas (não é inteligência artificial). Não achou o que procurava?
        Escreva para{" "}
        <a href={`mailto:${CONTATO_EMAIL}`} className={LINK}>
          {CONTATO_EMAIL}
        </a>
        .
      </p>
    </article>
  );
}
