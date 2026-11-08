import { FonteRodape } from "@/components/fonte-rodape";
import type { EmpregoMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

/**
 * Trabalho formal na aba Economia (IBGE, Cadastro Central de Empresas): pessoas ocupadas,
 * empresas e salário médio mensal com o do estado e o do Brasil no mesmo ano, e onde a cidade
 * trabalha (seções da CNAE; o IBGE só publica para cidades com 50 mil habitantes ou mais).
 */
const num = (n: number) => n.toLocaleString("pt-BR", { maximumFractionDigits: 0 });

export function EmpregoResumo({ dados, cidade, uf }: { dados: EmpregoMunicipio; cidade: string; uf: string }) {
  const ultimo = dados.serie[dados.serie.length - 1];
  if (!ultimo) return null;
  const primeiro = dados.serie[0];
  return (
    <div className="flex flex-col gap-4 border-t border-border pt-4">
      <h3 className="text-base font-semibold">Trabalho com carteira e empresas, {ultimo.ano}</h3>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {ultimo.pessoal_ocupado != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">Pessoas trabalhando em empresas e órgãos</dt>
            <dd className="numero text-2xl">{num(ultimo.pessoal_ocupado)}</dd>
            {primeiro && primeiro.ano !== ultimo.ano && primeiro.pessoal_ocupado != null && (
              <dd className="text-sm text-muted-foreground">
                Eram {num(primeiro.pessoal_ocupado)} em {primeiro.ano}
              </dd>
            )}
          </div>
        )}
        {ultimo.salario_medio != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">Salário médio por mês</dt>
            <dd className="numero text-2xl">{formatarReais(ultimo.salario_medio, true)}</dd>
            <dd className="text-sm text-muted-foreground">
              {[
                ultimo.salario_medio_sm != null &&
                  `${ultimo.salario_medio_sm.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} salários mínimos`,
                ultimo.uf_salario_medio != null && `${uf}: ${formatarReais(ultimo.uf_salario_medio, true)}`,
                ultimo.brasil_salario_medio != null && `Brasil: ${formatarReais(ultimo.brasil_salario_medio, true)}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </dd>
          </div>
        )}
        {ultimo.empresas != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">Empresas e outras organizações</dt>
            <dd className="numero text-2xl">{num(ultimo.empresas)}</dd>
          </div>
        )}
      </dl>
      {dados.setores.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-semibold">
            Onde {cidade} trabalha, {dados.setores_ano}
          </h4>
          <ul className="flex flex-col gap-2.5">
            {dados.setores.map((s) => (
              <li key={s.secao} className="flex flex-col gap-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
                  <span className="min-w-0">{s.nome}</span>
                  <span className="flex flex-wrap gap-x-1 tabular-nums">
                    {s.percentual != null && `${s.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`}
                    <span className="text-muted-foreground">{num(s.pessoal_ocupado)} pessoas</span>
                  </span>
                </div>
                <div aria-hidden className="h-1.5 w-full rounded-[1px] bg-muted">
                  <div
                    className="h-1.5 rounded-[1px]"
                    style={{ width: `${Math.max(1, s.percentual ?? 0)}%`, background: "var(--tema-economia)" }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          O IBGE só publica a divisão por atividade para cidades com 50 mil habitantes ou mais.
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        Só o trabalho em empresas e órgãos com CNPJ; o trabalho informal fica de fora. Termo oficial: pessoal ocupado
        (Cadastro Central de Empresas).
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
