/* eslint-disable jsx-a11y/no-redundant-roles, jsx-a11y/no-interactive-element-to-noninteractive-role -- no celular a tabela vira blocos (display); os papéis explícitos mantêm a semântica de tabela para leitores de tela */
import Link from "next/link";

import { BaixarCsv } from "@/components/avisar-erro/baixar-csv";
import { FonteRodape } from "@/components/fonte-rodape";
import { getCorrecoes } from "@/lib/api";
import { type Correcao, idLinhaCorrecao } from "@/lib/correcoes";
import { formatarData } from "@/lib/formato";

const ROTA_PERFIL: Record<string, string> = {
  parlamentar: "/parlamentar",
  "deputado-estadual": "/deputado-estadual",
  vereador: "/vereador",
  eleito: "/eleito",
};

function linkPerfil(c: Correcao): string | null {
  const base = c.perfil_tipo ? ROTA_PERFIL[c.perfil_tipo] : undefined;
  return base && c.perfil_id ? `${base}/${c.perfil_id}` : null;
}

const CEL = "block px-4 py-1 before:block before:text-xs before:font-medium before:text-muted-foreground before:content-[attr(data-rotulo)] md:table-cell md:px-3 md:py-3 md:align-top md:before:hidden";

/**
 * Tabela de correções feitas a partir de avisos (Frente 7), por data. No celular cada correção
 * vira um bloco com o rótulo de cada campo; do tamanho médio para cima é uma tabela comum.
 * Quem avisou não aparece.
 */
export async function TabelaCorrecoes() {
  const r = await getCorrecoes();
  if (!r.ok) {
    return <p className="text-muted-foreground">Não foi possível carregar a lista agora.</p>;
  }
  const itens = [...r.dados.itens].sort((a, b) => b.data.localeCompare(a.data));
  if (itens.length === 0) {
    return (
      <p className="text-muted-foreground">
        Nenhuma correção foi feita até agora a partir de avisos. Quando houver, ela aparece aqui, com o que estava, o que ficou e a
        fonte conferida.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <table role="table" className="block w-full text-left text-sm md:table">
        <caption className="mb-2 block text-left text-sm text-muted-foreground md:table-caption md:caption-top">
          Correções feitas a partir de avisos, da mais recente para a mais antiga ({r.dados.total} no total)
        </caption>
        <thead role="rowgroup" className="sr-only md:not-sr-only md:table-header-group">
          <tr role="row" className="md:border-b md:border-border">
            {["Data", "O que foi corrigido", "Antes", "Depois", "Fonte conferida", "Motivo"].map((t) => (
              <th key={t} role="columnheader" scope="col" className="px-3 py-2 font-medium">
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody role="rowgroup" className="block md:table-row-group">
          {itens.map((c) => {
            const perfil = linkPerfil(c);
            return (
              <tr
                key={c.id}
                id={idLinhaCorrecao(c)}
                role="row"
                className="block scroll-mt-20 border-b border-border py-3 target:bg-[var(--realce)] md:table-row md:py-0"
              >
                <th role="rowheader" scope="row" data-rotulo="Data" className={`${CEL} font-medium tabular-nums`}>
                  {formatarData(c.data)}
                </th>
                <td role="cell" data-rotulo="O que foi corrigido" className={CEL}>
                  {c.dado}
                  {c.perfil_nome && (
                    <span className="block text-muted-foreground">
                      {perfil ? (
                        <Link href={perfil} className="underline underline-offset-2">
                          {c.perfil_nome}
                        </Link>
                      ) : (
                        c.perfil_nome
                      )}
                    </span>
                  )}
                </td>
                <td role="cell" data-rotulo="Antes" className={CEL}>
                  {c.antes}
                </td>
                <td role="cell" data-rotulo="Depois" className={CEL}>
                  {c.depois}
                </td>
                <td role="cell" data-rotulo="Fonte conferida" className={CEL}>
                  {c.fonte}
                </td>
                <td role="cell" data-rotulo="Motivo" className={CEL}>
                  {c.motivo}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <BaixarCsv itens={itens} />
      <FonteRodape fonte="conferência da equipe com a fonte oficial de cada dado" atualizadoEm={itens[0].data} semAviso />
    </div>
  );
}
