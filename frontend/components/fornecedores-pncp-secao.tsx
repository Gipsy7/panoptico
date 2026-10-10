import { FonteRodape } from "@/components/fonte-rodape";
import type { FornecedoresPncp } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";

function formatarCnpj(c: string) {
  return c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
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
        <p className="text-xs text-muted-foreground">
          Empresas com mais valor em contratos publicados no PNCP por órgãos da cidade
        </p>
      </div>
      <ol className="lista-fios flex flex-col">
        {dados.itens.map((f) => (
          <li key={f.fornecedor_cnpj} className="flex items-baseline justify-between gap-3 py-2 text-sm">
            <span className="min-w-0">
              <span className="block">{f.fornecedor ?? `CNPJ ${formatarCnpj(f.fornecedor_cnpj)}`}</span>
              <span className="block text-xs text-muted-foreground tabular-nums">
                CNPJ {formatarCnpj(f.fornecedor_cnpj)} · {f.contratos} {f.contratos === 1 ? "contrato" : "contratos"}
              </span>
            </span>
            <span className="shrink-0 tabular-nums">{formatarReais(f.valor, true)}</span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">
        Soma do valor global dos contratos publicados no PNCP pelos órgãos municipais, sem
        alienações{dados.soma_ate ? `, até ${formatarData(dados.soma_ate)}` : ""}. Não é o valor pago
        (empenhos e pagamentos aparecem na seção sobre quem a cidade pagou), e prefeituras que não
        publicam no PNCP ficam de fora. Aditivos posteriores à publicação não entram na soma.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
