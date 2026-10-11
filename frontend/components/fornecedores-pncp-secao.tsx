import { FonteRodape } from "@/components/fonte-rodape";
import type { FornecedoresPncp } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";

function formatarCnpj(c: string) {
  return c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

/** Consulta pública do CNPJ na Receita Federal (para quando a base não tem o nome). */
function linkCnpj(c: string) {
  return `https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp?cnpj=${c}`;
}

function Fornecedor({ cnpj, nome }: { cnpj: string; nome: string | null }) {
  return (
    <>
      <span className="block">{nome ?? "Nome não informado nesta base"}</span>
      <span className="block text-xs text-muted-foreground tabular-nums">
        CNPJ{" "}
        <a href={linkCnpj(cnpj)} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
          {formatarCnpj(cnpj)}
        </a>
      </span>
    </>
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
        <p className="text-xs text-muted-foreground">
          Empresas com mais valor em contratos publicados no PNCP por órgãos da cidade
        </p>
      </div>
      <ol className="lista-fios flex flex-col">
        {dados.itens.map((f) => (
          <li key={f.fornecedor_cnpj} className="flex items-baseline justify-between gap-3 py-2 text-sm">
            <span className="min-w-0">
              <Fornecedor cnpj={f.fornecedor_cnpj} nome={f.fornecedor} />
              <span className="block text-xs text-muted-foreground tabular-nums">
                {f.contratos} {f.contratos === 1 ? "contrato" : "contratos"}
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
      {dados.suspeitos.length > 0 && (
        <div className="painel flex flex-col gap-2" role="note">
          <p className="text-sm font-medium">Valores que parecem incorretos ficaram de fora</p>
          <p className="text-xs text-muted-foreground">
            Estes valores foram informados ao PNCP pelo órgão, mas passam do que a cidade paga num ano
            inteiro (ou de R$ 50 bilhões): provável erro de digitação. Não entram na soma nem na lista
            acima e não foram corrigidos; conferir na fonte.
          </p>
          <ul className="lista-fios flex flex-col">
            {dados.suspeitos.map((s) => (
              <li key={`${s.fornecedor_cnpj}-${s.url}`} className="flex flex-col gap-0.5 py-2 text-sm">
                <Fornecedor cnpj={s.fornecedor_cnpj} nome={s.fornecedor} />
                <span className="tabular-nums">
                  Valor informado ao PNCP parece incorreto ({formatarReais(s.valor)}); conferir na fonte.{" "}
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                    Ver no PNCP
                  </a>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
