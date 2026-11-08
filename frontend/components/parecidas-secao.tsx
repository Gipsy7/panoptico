import Link from "next/link";

import type { CidadesParecidas, Vocacoes } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

/**
 * Comparar com cidades parecidas e vocações (redesenho, etapa 6). Só números já mostrados em
 * outras abas, lado a lado: não é ranking (a ordem é a da população) e não há cor de "melhor".
 */
const num = (n: number) => n.toLocaleString("pt-BR");
const um = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function ParecidasSecao({ dados, cidade }: { dados: CidadesParecidas; cidade: string }) {
  if (dados.cidades.length < 2) return null;
  const ano = (k: "pib_ano" | "ideb_ano" | "salario_ano") =>
    dados.cidades.find((c) => c.esta)?.[k] ?? dados.cidades.find((c) => c[k] != null)?.[k];
  return (
    <div className="flex flex-col gap-3">
      <p className="text-lg leading-snug">
        As cidades do Brasil com o número de moradores mais perto do de {cidade}, lado a lado. A ordem é a da população,
        não um ranking.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-left text-sm tabular-nums">
          <caption className="sr-only">Cidades com população parecida com a de {cidade}</caption>
          <thead>
            <tr className="border-b border-foreground">
              <th scope="col" className="py-2 pr-3 font-medium">Cidade</th>
              <th scope="col" className="py-2 pr-3 font-medium">Moradores ({dados.ano_populacao})</th>
              <th scope="col" className="py-2 pr-3 font-medium">PIB por morador ({ano("pib_ano")})</th>
              <th scope="col" className="py-2 pr-3 font-medium">IDEB anos iniciais, rede pública ({ano("ideb_ano")})</th>
              <th scope="col" className="py-2 pr-3 font-medium">Salário médio ({ano("salario_ano")})</th>
            </tr>
          </thead>
          <tbody>
            {dados.cidades.map((c) => (
              <tr
                key={c.ibge}
                className={`border-b border-border ${c.esta ? "bg-card" : ""}`}
                style={c.esta ? { boxShadow: "inset 4px 0 0 var(--bronze)" } : undefined}
              >
                <th scope="row" className={`py-2 pr-3 pl-2 ${c.esta ? "font-semibold" : "font-normal"}`}>
                  {c.esta ? (
                    `${c.nome}, ${c.uf}`
                  ) : (
                    <Link href={`/cidade/${c.ibge}`} className="underline underline-offset-4">
                      {c.nome}, {c.uf}
                    </Link>
                  )}
                </th>
                <td className="py-2 pr-3">{num(c.populacao)}</td>
                <td className="py-2 pr-3">{c.pib_por_morador != null ? formatarReais(c.pib_por_morador, true) : "–"}</td>
                <td className="py-2 pr-3">{c.ideb != null ? um(c.ideb) : "–"}</td>
                <td className="py-2 pr-3">{c.salario_medio != null ? formatarReais(c.salario_medio, true) : "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        PIB por morador calculado com a população do IBGE no mesmo ano; IDEB do INEP; salário médio do Cadastro Central de
        Empresas (IBGE). Cada número tem a fonte e a data na aba do seu assunto. &ldquo;–&rdquo; é sem dado publicado.
      </p>
    </div>
  );
}

/** Onde a cidade concentra mais que o Brasil: o peso de cada atividade aqui e no país. */
export function VocacoesSecao({ dados, cidade }: { dados: Vocacoes; cidade: string }) {
  const destaque = dados.emprego.filter((v) => (v.razao ?? 0) >= 1.2).slice(0, 5);
  if (dados.pib.length === 0 && destaque.length === 0) return null;
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-4">
      <h3 className="text-base font-semibold">No que {cidade} concentra mais que o Brasil</h3>
      {destaque.length > 0 && (
        <ul className="flex flex-col gap-1.5 text-sm">
          {destaque.map((v) => (
            <li key={v.atividade}>
              <span className="font-medium">{v.atividade}</span>: {um(v.percentual)}% das pessoas ocupadas aqui,{" "}
              {um(v.percentual_brasil)}% no Brasil
              {v.razao != null && <span className="text-muted-foreground"> ({um(v.razao)} vezes o peso no país)</span>}
            </li>
          ))}
        </ul>
      )}
      {dados.pib.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[22rem] text-left text-sm tabular-nums">
            <caption className="mb-1 text-left text-sm text-muted-foreground">
              Peso de cada atividade na riqueza produzida, {dados.pib_ano}
            </caption>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="py-1 pr-3 font-medium">Atividade</th>
                <th scope="col" className="py-1 pr-3 font-medium">{cidade}</th>
                <th scope="col" className="py-1 pr-3 font-medium">Brasil</th>
              </tr>
            </thead>
            <tbody>
              {dados.pib.map((v) => (
                <tr key={v.atividade} className="border-b border-border">
                  <th scope="row" className="py-1 pr-3 font-normal">{v.atividade}</th>
                  <td className="py-1 pr-3">{um(v.percentual)}%</td>
                  <td className="py-1 pr-3">{um(v.percentual_brasil)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        A comparação é do peso de cada atividade, não do tamanho: uma razão acima de 1 quer dizer que a atividade pesa mais
        aqui do que no país (termo técnico: quociente locacional). Pessoas ocupadas por atividade: só para cidades com 50
        mil habitantes ou mais, como o IBGE publica.
      </p>
    </div>
  );
}
