import { FonteRodape } from "@/components/fonte-rodape";
import { getContratosDaPessoa, type ContratoPncp } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

const VISIVEIS = 5;
const LIMITE_OBJETO = 220;

function formatarCnpj(c: string) {
  return c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

function resumir(texto: string) {
  return texto.length > LIMITE_OBJETO ? `${texto.slice(0, LIMITE_OBJETO).trimEnd()}…` : texto;
}

/** Contratos públicos de empresas de que a pessoa é sócia (quadro de sócios da Receita +
 * PNCP). Some quando não há nenhum. Fato, não juízo: ser sócio de empresa contratada não é
 * irregularidade. */
export async function ContratosSocioSecao({ pessoaId }: { pessoaId: number }) {
  const resultado = await getContratosDaPessoa(pessoaId);
  if (!resultado.ok || resultado.dados.itens.length === 0) return null;
  const d = resultado.dados;
  const empresas = d.empresas.map((e) =>
    e.nome ?? (e.nome_omitido ? `MEI (nome omitido por conter CPF), CNPJ ${formatarCnpj(e.cnpj)}` : formatarCnpj(e.cnpj)),
  );
  const desde = d.cobertura_desde ? Number(d.cobertura_desde.slice(0, 4)) : null;

  return (
    <section aria-labelledby="contratos-socio-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="contratos-socio-titulo" className="text-2xl">
          Contratos públicos de empresas de que é sócio(a)
        </h2>
        <p className="text-sm text-muted-foreground">
          {empresas.length === 1 ? "Empresa" : "Empresas"}: {empresas.join(", ")}. Total publicado no PNCP:{" "}
          <span className="tabular-nums">{d.total_contratos}</span>{" "}
          {d.total_contratos === 1 ? "contrato" : "contratos"}, somando{" "}
          <span className="tabular-nums">{formatarReais(d.valor_total, true)}</span>
          {d.contratos_suspeitos > 0 &&
            ` (sem ${d.contratos_suspeitos} ${d.contratos_suspeitos === 1 ? "contrato" : "contratos"} com valor que parece incorreto)`}
          .
        </p>
      </div>

      <ul className="lista-fios flex flex-col">
        {d.itens.slice(0, VISIVEIS).map((c, i) => (
          <Contrato key={i} c={c} />
        ))}
      </ul>
      {d.itens.length > VISIVEIS && (
        <details className="painel">
          <summary className="cursor-pointer text-sm font-medium">
            Ver {d.itens.length - VISIVEIS === 1 ? "o outro contrato" : `os outros ${d.itens.length - VISIVEIS} contratos`}
          </summary>
          <ul className="mt-2 lista-fios flex flex-col">
            {d.itens.slice(VISIVEIS).map((c, i) => (
              <Contrato key={i} c={c} />
            ))}
          </ul>
        </details>
      )}
      {d.total_contratos > d.itens.length && (
        <p className="text-sm text-muted-foreground">
          Mostramos os {d.itens.length} mais recentes de {d.total_contratos}.
        </p>
      )}

      <p className="text-sm text-muted-foreground">
        A ligação vem do quadro de sócios da Receita Federal (CPF parcial e nome iguais). Ser sócio
        de uma empresa contratada pelo poder público não é, por si, irregularidade: o dado mostra só
        que o contrato existe. Entram contratos publicados no PNCP{desde ? ` desde ${desde}` : ""},
        sem alienações; órgãos que não publicam no PNCP não aparecem. O valor é o global informado
        no contrato; quando ele passa do que o município paga num ano inteiro (ou de R$ 50 bilhões),
        parece erro de digitação do órgão: o contrato aparece com aviso e não entra no total.
      </p>
      <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />
    </section>
  );
}

function Contrato({ c }: { c: ContratoPncp }) {
  const vigencia =
    c.vigencia_inicio && c.vigencia_fim
      ? `${formatarData(c.vigencia_inicio)} a ${formatarData(c.vigencia_fim)}`
      : c.vigencia_fim
        ? `até ${formatarData(c.vigencia_fim)}`
        : null;
  const orgao = [c.orgao, c.municipio && c.uf ? `${c.municipio}/${c.uf}` : null].filter(Boolean).join(" · ");
  return (
    <li className="flex flex-col gap-1.5 py-3">
      <p className="text-sm text-muted-foreground tabular-nums">Publicado em {formatarData(c.publicado_em)}</p>
      <p className="text-sm">{c.objeto ? resumir(c.objeto) : "Objeto não informado"}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
        {orgao && (
          <>
            <dt className="text-muted-foreground">Órgão</dt>
            <dd>{orgao}</dd>
          </>
        )}
        {(c.fornecedor_nome || c.nome_omitido) && (
          <>
            <dt className="text-muted-foreground">Empresa</dt>
            <dd>
              {c.fornecedor_nome ?? "MEI (nome omitido por conter CPF)"}
              {!c.fornecedor_nome && (
                <span className="block text-sm text-muted-foreground tabular-nums">
                  CNPJ {formatarCnpj(c.fornecedor_cnpj)}
                </span>
              )}
            </dd>
          </>
        )}
        {c.valor !== null && (
          <>
            <dt className="text-muted-foreground">Valor</dt>
            <dd className="tabular-nums">{formatarReais(c.valor)}</dd>
          </>
        )}
        {c.valor_suspeito && c.valor !== null && (
          <>
            <dt className="text-muted-foreground">Atenção</dt>
            <dd role="note">
              Valor informado ao PNCP parece incorreto ({formatarReais(c.valor)}); conferir na fonte. Fica
              fora do total acima.
            </dd>
          </>
        )}
        {vigencia && (
          <>
            <dt className="text-muted-foreground">Vigência</dt>
            <dd className="tabular-nums">{vigencia}</dd>
          </>
        )}
      </dl>
      <p className="text-sm">
        <LinkExterno href={c.url} className="underline underline-offset-2">
          Ver no PNCP
        </LinkExterno>
      </p>
    </li>
  );
}
