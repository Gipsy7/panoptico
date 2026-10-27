import type { ReactNode } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import { getSancoes, type SancaoItem } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

const ROTULO_TIPO: Record<string, string> = {
  sancao: "Sanção em cadastro da CGU",
  tcu_contas_irregulares: "Contas julgadas irregulares pelo TCU",
  tcu_inabilitacao: "Inabilitação para cargo público pelo TCU",
};

/** O que é um registro nos cadastros da CGU e do TCU (também usado na pergunta do perfil). */
export const TEXTO_REGISTRO =
  "Um registro nestes cadastros é a informação do órgão que o mantém; a situação de cada um é a que a fonte informa, e pode ter mudado depois da data de atualização.";

/** Sanções (CEIS, CNEP, CEAF) e decisões do TCU ligadas à pessoa por dado seguro. Sem
 * adjetivo: o fato, o órgão, a data e a situação que a fonte informa. */
export async function SancoesSecao({
  pessoaId,
  explicacao,
}: {
  pessoaId: number;
  /** Âncora de uma pergunta que já explica o que é um registro; troca o parágrafo por um link. */
  explicacao?: string;
}) {
  const resultado = await getSancoes(pessoaId);
  if (!resultado.ok) return null;
  const d = resultado.dados;

  return (
    <section aria-labelledby="sancoes-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="sancoes-titulo" className="text-2xl">
          Punições e contas reprovadas
        </h2>
        <p className="text-sm text-muted-foreground">
          Sanções (CEIS/CNEP/CEAF) e contas julgadas irregulares pelo TCU
        </p>
      </div>

      {d.itens.length === 0 ? (
        <p className="text-sm">
          Nada encontrado nos cadastros da CGU e do TCU
          {d.atualizado_em ? ` até ${formatarData(d.atualizado_em)}` : ""}.
        </p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground tabular-nums">
            {d.itens.length} {d.itens.length === 1 ? "registro" : "registros"} nos cadastros da CGU e do TCU.
          </p>
          <ul className="lista-fios flex flex-col">
            {d.itens.map((item, i) => (
              <Item key={i} item={item} />
            ))}
          </ul>
        </>
      )}

      {explicacao ? (
        <p className="text-sm">
          <a href={explicacao} className="alvo-link underline underline-offset-2">
            O que é um registro nestes cadastros
          </a>
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          {TEXTO_REGISTRO}
        </p>
      )}
      <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />
    </section>
  );
}

function Item({ item }: { item: SancaoItem }) {
  return (
    <li className="flex flex-col gap-1.5 py-3">
      <p className="text-sm text-muted-foreground tabular-nums">
        {item.data ? formatarData(item.data) : "Data não informada pela fonte"}
      </p>
      <p className="font-medium">{ROTULO_TIPO[item.tipo] ?? "Registro oficial"}</p>
      <Descricao texto={item.descricao} />
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
        {item.orgao && <Campo rotulo="Órgão">{item.orgao}</Campo>}
        {item.situacao && <Campo rotulo="Situação">{item.situacao}</Campo>}
        {item.numero_processo && (
          <Campo rotulo="Processo">
            <span className="break-all tabular-nums">{item.numero_processo}</span>
          </Campo>
        )}
      </dl>
      {item.fonte_url && (
        <p className="text-sm text-muted-foreground">
          <LinkExterno href={item.fonte_url} className="underline underline-offset-2">
            Ver na fonte oficial
          </LinkExterno>
        </p>
      )}
      {item.ligacao && <p className="text-sm text-muted-foreground">{item.ligacao}</p>}
    </li>
  );
}

/** A CGU junta ao fato o fundamento legal inteiro, em caixa alta. O fato fica à vista; o
 * fundamento, sem mudar uma letra, abre sob demanda. */
function Descricao({ texto }: { texto: string | null }) {
  if (!texto) return null;
  const i = texto.indexOf(" Fundamento:");
  if (i < 0) return <p className="text-sm break-words">{texto}</p>;
  const fato = texto.slice(0, i);
  const resto = texto.slice(i + 1);
  return (
    <>
      <p className="text-sm break-words">{fato}</p>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground underline underline-offset-2">
          Ver o fundamento legal informado pela fonte
        </summary>
        <p className="mt-1 break-words text-muted-foreground">{resto}</p>
      </details>
    </>
  );
}

function Campo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{rotulo}</dt>
      <dd className="min-w-0">{children}</dd>
    </>
  );
}
