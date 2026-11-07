import { TextoLongo } from "@/components/ui/texto-longo";
import { TabelaRolavel } from "@/components/ui/tabela-rolavel";
import { FonteRodape } from "@/components/fonte-rodape";
import { CobrarLinha } from "@/components/perfil/cobrar-linha";
import Link from "next/link";
import type { Casa, ProjetoItem, Projetos, ViraramLei } from "@/lib/api";
import { CASA_DA, formatarData } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";
import { TermoOficial } from "@/components/termo-oficial";

const NUMERO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export function ProjetosSecao({ projetos, casa }: { projetos: Projetos; casa: Casa }) {
  const desde = new Date(projetos.desde).getUTCFullYear();

  return (
    <section aria-labelledby="projetos-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="projetos-titulo" className="text-2xl">
          Projetos de lei
        </h2>
        <p className="text-sm text-muted-foreground">
          <TermoOficial id="proposicao">Proposições legislativas</TermoOficial> apresentadas desde fevereiro de {desde} (<TermoOficial id="legislatura">legislatura atual</TermoOficial>)
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Numero rotulo="Apresentou como autor principal" valor={projetos.primeiro_autor} />
        <Numero
          rotulo={`Média por parlamentar ${CASA_DA[casa]}`}
          valor={projetos.media_casa_primeiro_autor}
        />
        <Numero rotulo="Assinou como coautor" valor={projetos.coautor} />
        {projetos.viraram_lei && (
          <Numero
            rotulo="Viraram lei (como autor ou coautor)"
            valor={projetos.viraram_lei.total}
            apoio={`Média ${CASA_DA[casa]}: ${NUMERO.format(projetos.viraram_lei.media_casa)}`}
          />
        )}
      </dl>
      <p className="text-sm text-muted-foreground">
        Autor principal é quem propõe o projeto. Coautor é quem assina junto, o que é comum em
        propostas de emenda à Constituição.
      </p>

      {projetos.por_tipo.length > 0 && (
        <TabelaRolavel larguraMinima="24rem" rotulo="Projetos por tipo, tabela com rolagem lateral">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Projetos por tipo</caption>
          <thead className="text-muted-foreground">
            <tr>
              <th scope="col" className="py-1 pr-3 font-normal">Tipo</th>
              <th scope="col" className="py-1 pr-3 text-right font-normal">Autor principal</th>
              <th scope="col" className="py-1 text-right font-normal">Coautor</th>
            </tr>
          </thead>
          <tbody>
            {projetos.por_tipo.map((t) => (
              <tr key={t.sigla} className="border-t">
                <th scope="row" className="py-2 pr-3 font-normal">
                  {t.nome} <span className="text-sm text-muted-foreground">({t.sigla})</span>
                </th>
                <td className="py-2 pr-3 text-right tabular-nums">{t.primeiro_autor}</td>
                <td className="py-2 text-right tabular-nums">{t.coautor}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </TabelaRolavel>
      )}

      {projetos.viraram_lei ? (
        <ViraramLeiBloco v={projetos.viraram_lei} />
      ) : projetos.viraram_norma_lista.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">
            Viraram lei ou norma ({projetos.viraram_norma}){" "}
          </h3>
          <ListaProjetos itens={projetos.viraram_norma_lista} />
        </div>
      )}

      {projetos.recentes.length > 0 ? (
        <details className="painel">
          <summary className="cursor-pointer font-medium">
            {projetos.recentes.length === 1
              ? "Ver o projeto mais recente como autor principal"
              : `Ver os ${projetos.recentes.length} projetos mais recentes como autor principal`}
          </summary>
          <div className="mt-3">
            <ListaProjetos itens={projetos.recentes} />
          </div>
        </details>
      ) : (
        <p className="text-muted-foreground">Nenhum projeto como autor principal neste período.</p>
      )}

      <CobrarLinha tema="projetos" esfera="federal" casa={casa} />
      <FonteRodape
        fonte={projetos.fonte_nome}
        url={projetos.fonte_url}
        atualizadoEm={projetos.atualizado_em}
      />
    </section>
  );
}

function Numero({ rotulo, valor, apoio }: { rotulo: string; valor: number; apoio?: string }) {
  return (
    <div className="figura min-w-0">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="numero text-2xl break-words sm:text-3xl">{NUMERO.format(valor)}</dd>
      {apoio && <dd className="text-sm text-muted-foreground">{apoio}</dd>}
    </div>
  );
}

/** "Viraram lei" (versão B aprovada): lista recolhida, cada projeto com a lei, a data e o texto oficial. */
function ViraramLeiBloco({ v }: { v: ViraramLei }) {
  if (v.total === 0) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">
          Nenhum projeto desta legislatura com a assinatura desta pessoa virou lei, lei complementar ou emenda à
          Constituição até agora.
        </p>
        <FonteRodape fonte={v.fonte_nome} url={v.fonte_url} atualizadoEm={v.atualizado_em} />
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <details className="painel">
        <summary className="flex min-h-11 cursor-pointer items-center font-medium">
          {v.total === 1 ? "Ver o projeto que virou lei" : `Ver os ${v.total} projetos que viraram lei`}
        </summary>
        <ul className="lista-fios mt-3">
          {v.itens.map((i) => (
            <li key={i.projeto} className="flex flex-col gap-1 py-3">
              <p className="text-sm text-muted-foreground">
                <Link href={i.projeto_link} className="underline underline-offset-4">
                  {i.projeto}
                </Link>{" "}
                · {i.primeiro_autor ? "autor principal" : "coautor"}
              </p>
              <p className="font-semibold">
                {i.norma.nome} · <span className="tabular-nums">{formatarData(i.norma.data)}</span>
              </p>
              <TextoLongo linhas={3}>{i.norma.ementa}</TextoLongo>
              <LinkExterno href={i.norma.url} className="alvo-link self-start text-sm font-medium underline underline-offset-4">
                Ler o texto da lei
              </LinkExterno>
            </li>
          ))}
        </ul>
      </details>
      <p className="text-sm text-muted-foreground">
        Conta leis, leis complementares e emendas à Constituição; decretos legislativos ficam de fora.{" "}
        {v.primeiro_autor > 0 && `${NUMERO.format(v.primeiro_autor)} como autor principal.`}
      </p>
      <FonteRodape fonte={v.fonte_nome} url={v.fonte_url} atualizadoEm={v.atualizado_em} />
    </div>
  );
}

function ListaProjetos({ itens }: { itens: ProjetoItem[] }) {
  return (
    <ul className="flex flex-col divide-y">
      {itens.map((p) => (
        <li key={`${p.sigla_tipo}-${p.numero}-${p.ano}`} className="flex flex-col gap-1 py-3">
          <LinkExterno
            href={p.url}
            className="font-medium underline underline-offset-2"
          >
            {p.sigla_tipo} {p.numero}/{p.ano}
          </LinkExterno>
          <TextoLongo linhas={3}>{p.ementa}</TextoLongo>
          <p className="text-sm text-muted-foreground">
            Apresentado em {formatarData(p.data_apresentacao)} ·{" "}
            {p.situacao ?? "Situação não informada"}
          </p>
        </li>
      ))}
    </ul>
  );
}
