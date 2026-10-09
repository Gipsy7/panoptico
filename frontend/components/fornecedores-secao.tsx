import { FonteRodape } from "@/components/fonte-rodape";
import type { Fornecedores } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const ROTULOS: Record<string, string> = {
  prefeitura: "Prefeitura",
  camara: "Câmara municipal",
  outros: "Autarquias e fundos municipais",
};

function formatarCnpj(c: string | null) {
  if (!c) return null;
  return c.length === 14 ? c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5") : c;
}

/** Para quem a prefeitura e a câmara pagaram no ano (Tribunal de Contas do estado). */
export function FornecedoresSecao({ dados, cidade }: { dados: Fornecedores; cidade: string }) {
  return (
    <section aria-labelledby="fornecedores-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="fornecedores-titulo" className="text-2xl">
          Para quem {cidade} pagou em {dados.ano}
        </h2>
        <p className="text-xs text-muted-foreground">
          Valores pagos, como a cidade informou ao Tribunal de Contas do estado
        </p>
      </div>
      {dados.orgaos.map((o) => (
        <details key={o.orgao} className="painel" open={o.orgao === "camara"}>
          <summary className="cursor-pointer font-medium">
            {ROTULOS[o.orgao] ?? o.orgao}:{" "}
            <span className="numero">{formatarReais(o.total_pago, true)}</span> pagos
          </summary>
          <ul className="mt-3 lista-fios flex flex-col">
            {o.itens.map((f, i) => (
              <li key={i} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="min-w-0">
                  <span className="block">{f.fornecedor}</span>
                  <span className="block text-xs text-muted-foreground">
                    {[formatarCnpj(f.documento) && `CNPJ ${formatarCnpj(f.documento)}`, `${f.pagamentos} pagamentos`]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </span>
                <span className="shrink-0 tabular-nums">{formatarReais(f.valor_pago, true)}</span>
              </li>
            ))}
          </ul>
        </details>
      ))}
      <p className="text-xs text-muted-foreground">
        Os maiores fornecedores de cada órgão; o restante aparece somado. Pagamentos a pessoas
        físicas (servidores, autônomos, beneficiários) aparecem somados, sem nomes, e a folha de
        salários aparece separada. Por enquanto, só para cidades de São Paulo (exceto a capital,
        fiscalizada pelo Tribunal de Contas do Município) e do Rio Grande do Sul.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
