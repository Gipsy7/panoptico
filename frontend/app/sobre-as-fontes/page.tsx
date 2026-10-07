import type { Metadata } from "next";
import { Suspense } from "react";

import { getFontes } from "@/lib/api";
import { formatarData } from "@/lib/formato";

export const metadata: Metadata = {
  title: "Sobre as fontes",
  description: "De onde vem cada dado do Panóptico, como é calculado e quando foi atualizado.",
};

export default function SobreAsFontesPage() {
  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Sobre as fontes</h1>
        <p className="text-muted-foreground">
          Todos os dados do Panóptico vêm de fontes públicas e oficiais. Não fazemos notas,
          rankings nem avaliações: mostramos o dado, a média para comparação e o link para a
          fonte.
        </p>
      </header>

      <section aria-labelledby="fontes-titulo" className="flex flex-col gap-3">
        <h2 id="fontes-titulo" className="text-xl font-semibold">
          De onde vem cada dado
        </h2>
        <Suspense fallback={<p className="text-muted-foreground">Carregando…</p>}>
          <ListaFontes />
        </Suspense>
      </section>

      <section aria-labelledby="calculo-titulo" className="flex flex-col gap-4">
        <h2 id="calculo-titulo" className="text-xl font-semibold">
          Como cada número é calculado
        </h2>
        <Item titulo="Gastos do gabinete">
          Soma dos reembolsos da cota parlamentar no ano (CEAP na Câmara, CEAPS no Senado),
          incluindo restituições, que aparecem como valores negativos. A média da Casa é a média
          do total por parlamentar em exercício; quem não gastou entra com zero.
        </Item>
        <Item titulo="Presença em votações">
          Quantas votações nominais do Plenário o parlamentar registrou voto, contadas a partir do
          início do ano ou do início do seu exercício atual (posse, posse de suplente ou retorno),
          o que vier depois. Quem preside a sessão conta como presente. O Senado informa ausências
          justificadas (missão oficial, licença); a Câmara publica apenas quem votou.
        </Item>
        <Item titulo="Projetos de lei">
          Projetos de lei (PL e PLP), propostas de emenda à Constituição (PEC) e projetos de
          decreto legislativo (PDL) apresentados desde fevereiro de 2023. O número principal conta
          só os projetos em que o parlamentar é o autor principal; coautorias aparecem à parte.
          &quot;Virou lei ou norma&quot; quer dizer que a situação oficial é &quot;transformado em
          norma jurídica&quot;.
        </Item>
        <Item titulo="Dinheiro enviado para a cidade">
          Valores de emendas individuais, dos orçamentos de 2023 em diante, pagos à prefeitura, aos
          fundos municipais e a entidades sem fins lucrativos da cidade. Não entram emendas de
          bancada, de comissão ou de relator, nem pagamentos a empresas ou a bancos
          intermediários. O autor é identificado pelo nome usado no orçamento; quem não está em
          exercício aparece em &quot;outros autores&quot;.
        </Item>
        <Item titulo="Salário">
          O subsídio é o mesmo para todos os deputados federais e senadores e é fixado por decreto
          legislativo. Os gastos do gabinete são uma verba separada.
        </Item>
      </section>

      <section aria-labelledby="erros-titulo" className="flex flex-col gap-2">
        <h2 id="erros-titulo" className="text-xl font-semibold">
          Encontrou um erro?
        </h2>
        <p className="text-muted-foreground">
          Os dados são copiados das fontes oficiais sem edição. Se algo estiver diferente da
          fonte, confira a data de atualização: as fontes corrigem dados com frequência e o
          Panóptico atualiza tudo diariamente.
        </p>
      </section>
    </article>
  );
}

async function ListaFontes() {
  const resultado = await getFontes();
  if (!resultado.ok) {
    return <p className="text-muted-foreground">Não foi possível carregar a lista agora.</p>;
  }
  return (
    <ul className="flex flex-col divide-y rounded-xl bg-card ring-1 ring-foreground/10">
      {resultado.dados.map((f) => (
        <li key={f.dado} className="flex flex-col gap-0.5 p-4">
          <span className="font-medium">{f.dado}</span>
          <span className="text-sm text-muted-foreground">
            <a
              href={f.url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              {f.orgao}
            </a>
            {f.atualizado_em && <> · atualizado em {formatarData(f.atualizado_em)}</>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Item({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-medium">{titulo}</h3>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}
