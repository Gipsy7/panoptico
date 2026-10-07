import { FonteRodape } from "@/components/fonte-rodape";
import type { Casa, ProjetoItem, Projetos } from "@/lib/api";
import { CASA_CURTA, formatarData } from "@/lib/formato";

const NUMERO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export function ProjetosSecao({ projetos, casa }: { projetos: Projetos; casa: Casa }) {
  const desde = new Date(projetos.desde).getUTCFullYear();

  return (
    <section aria-labelledby="projetos-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="projetos-titulo" className="text-2xl">
          Projetos de lei
        </h2>
        <p className="text-xs text-muted-foreground">
          Proposições legislativas apresentadas desde fevereiro de {desde} (legislatura atual)
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Numero rotulo="Apresentou como autor principal" valor={projetos.primeiro_autor} />
        <Numero
          rotulo={`Média por parlamentar do ${CASA_CURTA[casa]}`}
          valor={projetos.media_casa_primeiro_autor}
        />
        <Numero rotulo="Assinou como coautor" valor={projetos.coautor} />
      </dl>
      <p className="text-sm text-muted-foreground">
        Autor principal é quem propõe o projeto. Coautor é quem assina junto, o que é comum em
        propostas de emenda à Constituição.
      </p>

      {projetos.por_tipo.length > 0 && (
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
                  {t.nome} <span className="text-xs text-muted-foreground">({t.sigla})</span>
                </th>
                <td className="py-2 pr-3 text-right tabular-nums">{t.primeiro_autor}</td>
                <td className="py-2 text-right tabular-nums">{t.coautor}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {projetos.viraram_norma_lista.length > 0 && (
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
            Ver os {projetos.recentes.length} projetos mais recentes como autor principal
          </summary>
          <div className="mt-3">
            <ListaProjetos itens={projetos.recentes} />
          </div>
        </details>
      ) : (
        <p className="text-muted-foreground">Nenhum projeto como autor principal neste período.</p>
      )}

      <FonteRodape
        fonte={projetos.fonte_nome}
        url={projetos.fonte_url}
        atualizadoEm={projetos.atualizado_em}
      />
    </section>
  );
}

function Numero({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <div className="figura">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="numero text-3xl">{NUMERO.format(valor)}</dd>
    </div>
  );
}

function ListaProjetos({ itens }: { itens: ProjetoItem[] }) {
  return (
    <ul className="flex flex-col divide-y">
      {itens.map((p) => (
        <li key={`${p.sigla_tipo}-${p.numero}-${p.ano}`} className="flex flex-col gap-1 py-3">
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline underline-offset-2"
          >
            {p.sigla_tipo} {p.numero}/{p.ano}
          </a>
          <p className="text-sm">{p.ementa}</p>
          <p className="text-xs text-muted-foreground">
            Apresentado em {formatarData(p.data_apresentacao)} ·{" "}
            {p.situacao ?? "Situação não informada"}
          </p>
        </li>
      ))}
    </ul>
  );
}
