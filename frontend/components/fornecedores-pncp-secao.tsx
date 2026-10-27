import { FonteRodape } from "@/components/fonte-rodape";
import type { FornecedoresPncp } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

function formatarCnpj(c: string) {
  return c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

/** Consulta pública do CNPJ na Receita Federal (para quando a base não tem o nome). */
function linkCnpj(c: string) {
  return `https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp?cnpj=${c}`;
}

function Fornecedor({
  cnpj,
  nome,
  omitido,
  entePublico,
}: {
  cnpj: string;
  nome: string | null;
  omitido?: boolean;
  entePublico?: boolean;
}) {
  return (
    <>
      <span className="block">
        {nome ?? (omitido ? "MEI (nome omitido por conter CPF)" : "Nome não informado nesta base")}
        {entePublico && (
          <span className="ml-2 whitespace-nowrap rounded-full px-2 py-0.5 text-xs text-muted-foreground ring-1 ring-foreground/20">
            órgão público
          </span>
        )}
      </span>
      <span className="block text-sm text-muted-foreground tabular-nums">
        CNPJ{" "}
        <LinkExterno href={linkCnpj(cnpj)} className="underline underline-offset-2">
          {formatarCnpj(cnpj)}
        </LinkExterno>
      </span>
    </>
  );
}

const VISIVEIS = 5;

function ItemFornecedor({ f }: { f: FornecedoresPncp["itens"][number] }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-2 text-sm">
      <span className="min-w-0">
        <Fornecedor cnpj={f.fornecedor_cnpj} nome={f.fornecedor} omitido={f.nome_omitido} entePublico={f.ente_publico} />
        <span className="block text-sm text-muted-foreground tabular-nums">
          {f.contratos} {f.contratos === 1 ? "contrato" : "contratos"}
        </span>
      </span>
      <span className="shrink-0 tabular-nums">{formatarReais(f.valor, true)}</span>
    </li>
  );
}

/** Maiores fornecedores dos órgãos municipais no PNCP, no ano mais recente com dados. */
export function FornecedoresPncpSecao({ dados, cidade }: { dados: FornecedoresPncp; cidade: string }) {
  if (dados.itens.length === 0) return null;
  return (
    <section aria-labelledby="fornecedores-pncp-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="fornecedores-pncp-titulo" className="text-2xl">
          Maiores contratos de {cidade} em {dados.ano}
        </h2>
        <p className="text-sm text-muted-foreground">
          Empresas com mais valor em contratos publicados no PNCP por órgãos da cidade
        </p>
      </div>
      <ol className="lista-fios flex flex-col">
        {dados.itens.slice(0, VISIVEIS).map((f) => (
          <ItemFornecedor key={f.fornecedor_cnpj} f={f} />
        ))}
      </ol>
      {dados.itens.length > VISIVEIS && (
        <details className="painel">
          <summary className="cursor-pointer font-medium">
            Ver os outros {dados.itens.length - VISIVEIS} contratos
          </summary>
          <ol className="lista-fios mt-3 flex flex-col">
            {dados.itens.slice(VISIVEIS).map((f) => (
              <ItemFornecedor key={f.fornecedor_cnpj} f={f} />
            ))}
          </ol>
        </details>
      )}
      <p className="text-sm text-muted-foreground">
        Soma do valor global dos contratos publicados no PNCP pelos órgãos municipais, sem
        alienações{dados.soma_ate ? `, até ${formatarData(dados.soma_ate)}` : ""}. Não é o valor pago
        (empenhos e pagamentos aparecem na seção sobre quem a cidade pagou), e prefeituras que não
        publicam no PNCP ficam de fora. Aditivos posteriores à publicação não entram na soma.
      </p>
      {dados.itens.some((f) => f.ente_publico) && (
        <p className="text-sm text-muted-foreground">
          &quot;Órgão público&quot; indica um CNPJ que também aparece como órgão contratante no PNCP: o valor
          é de contrato ou repasse entre órgãos públicos, não de compra de uma empresa.
        </p>
      )}
      {dados.suspeitos.length > 0 && (
        <details className="painel" role="note">
          <summary className="cursor-pointer font-medium">
            {dados.suspeitos.length} {dados.suspeitos.length === 1 ? "valor ficou" : "valores ficaram"} de fora
            por parecer{dados.suspeitos.length === 1 ? "" : "em"} erro de digitação
          </summary>
          <p className="mt-3 text-sm text-muted-foreground">
            Estes valores foram informados ao PNCP pelo órgão, mas passam do que a cidade paga num ano
            inteiro (ou de R$ 50 bilhões): provável erro de digitação. Não entram na soma nem na lista
            acima e não foram corrigidos; conferir na fonte.
          </p>
          <ul className="lista-fios flex flex-col">
            {dados.suspeitos.map((s) => (
              <li key={`${s.fornecedor_cnpj}-${s.url}`} className="flex flex-col gap-0.5 py-2 text-sm">
                <Fornecedor cnpj={s.fornecedor_cnpj} nome={s.fornecedor} omitido={s.nome_omitido} />
                <span className="tabular-nums">
                  Valor informado ao PNCP parece incorreto ({formatarReais(s.valor)}); conferir na fonte.{" "}
                  <LinkExterno href={s.url} className="underline underline-offset-2">
                    Ver no PNCP
                  </LinkExterno>
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
