import { FonteRodape } from "@/components/fonte-rodape";
import { getServicoFederal } from "@/lib/api";
import { formatarReais, MESES } from "@/lib/formato";

function mes(valor: string | null): string {
  const m = valor ? /^(\d{4})-(\d{2})/.exec(valor) : null;
  return m ? `${MESES[Number(m[2]) - 1]}/${m[1]}` : "";
}

function periodo(a: string | null, b: string | null): string {
  const inicio = mes(a);
  const fim = mes(b);
  if (inicio && fim && inicio !== fim) return `${inicio} a ${fim}`;
  return inicio || fim || "período não informado";
}

/** Cargos federais, viagens a serviço e cartão corporativo da pessoa, do Portal da
 * Transparência. Some quando não há nada. */
export async function ServicoFederalSecao({ pessoaId }: { pessoaId: number }) {
  const resultado = await getServicoFederal(pessoaId);
  if (!resultado.ok) return null;
  const d = resultado.dados;
  if (d.cargos.length === 0 && d.viagens_por_ano.length === 0 && d.cartao_por_ano_e_orgao.length === 0) {
    return null;
  }
  const casa = d.media_da_casa;

  return (
    <section aria-labelledby="servico-federal-titulo" className="revelar flex flex-col gap-6">
      <div>
        <h2 id="servico-federal-titulo" className="text-2xl">
          Trabalho no governo federal
        </h2>
        <p className="text-sm text-muted-foreground">
          Cargos, viagens a serviço e cartão corporativo, no Portal da Transparência
        </p>
      </div>

      {d.cargos.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Cargos e funções</h3>
          <ul className="lista-fios flex flex-col">
            {d.cargos.map((c, i) => (
              <li key={i} className="flex flex-col gap-0.5 py-3 text-sm">
                <span className="font-medium">
                  {c.funcao ?? "Função não informada"}
                  {c.sigla ? ` (${c.sigla}${c.nivel ? ` ${c.nivel}` : ""})` : ""}
                </span>
                {c.orgao && <span>{c.orgao}</span>}
                <span className="text-muted-foreground tabular-nums">
                  {periodo(c.primeiro_mes, c.ultimo_mes)}
                  {c.origem ? ` · segundo o ${c.origem}` : ""}
                </span>
                {c.consta_no_cadastro_mais_recente && (
                  <span className="text-muted-foreground">Consta no cadastro de servidores mais recente.</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {d.viagens_por_ano.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">
            Viagens a serviço
            <span className="block text-sm font-normal text-muted-foreground">
              valor = diárias + passagens + outros gastos da viagem
            </span>
          </h3>
          <ul className="lista-fios flex flex-col">
            {d.viagens_por_ano.map((v) => {
              const valor = v.diarias + v.passagens + v.outros;
              return (
                <li key={v.ano} className="flex flex-col gap-0.5 py-3 text-sm">
                  <span className="font-medium tabular-nums">{v.ano}</span>
                  <span className="tabular-nums">
                    {v.viagens} {v.viagens === 1 ? "viagem" : "viagens"} · {formatarReais(valor, true)}
                  </span>
                  {v.media_casa_viagens !== null && v.media_casa_valor !== null && (
                    <span className="text-muted-foreground tabular-nums">
                      Média da Casa: {v.media_casa_viagens.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}{" "}
                      {v.media_casa_viagens === 1 ? "viagem" : "viagens"} · {formatarReais(v.media_casa_valor, true)}
                    </span>
                  )}
                  {v.devolucao > 0 && (
                    <span className="text-muted-foreground tabular-nums">
                      Devolvido: {formatarReais(v.devolucao, true)}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {d.cartao_por_ano_e_orgao.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">
            Cartão corporativo
            <span className="block text-sm font-normal text-muted-foreground">
              Cartão de Pagamento do Governo Federal (CPGF), usado para despesas do órgão
            </span>
          </h3>
          <ul className="lista-fios flex flex-col">
            {d.cartao_por_ano_e_orgao.map((c, i) => (
              <li key={i} className="flex flex-col gap-0.5 py-3 text-sm">
                <span className="font-medium tabular-nums">
                  {c.ano}
                  {c.orgao ? <span className="font-normal"> · {c.orgao}</span> : null}
                </span>
                <span className="tabular-nums">
                  {formatarReais(c.total, true)} em {c.transacoes} {c.transacoes === 1 ? "compra" : "compras"}
                  {c.saques > 0 ? ` · saques: ${formatarReais(c.saques, true)}` : ""}
                </span>
                {c.media_casa_total !== null && ultimoDoAno(d.cartao_por_ano_e_orgao, i) && (
                  <span className="text-muted-foreground tabular-nums">
                    {linhasDoAno(d.cartao_por_ano_e_orgao, c.ano) > 1
                      ? `Total no ano, somando os órgãos: ${formatarReais(totalDoAno(d.cartao_por_ano_e_orgao, c.ano), true)} · `
                      : ""}
                    Média da Casa no ano: {formatarReais(c.media_casa_total, true)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {casa && (
        <p className="text-sm text-muted-foreground">
          {casa.descricao} ({casa.parlamentares_em_exercicio} parlamentares em exercício).
        </p>
      )}
      {d.ligacao && <p className="text-xs text-muted-foreground">{d.ligacao}</p>}
      <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />
    </section>
  );
}

type LinhaCartao = { ano: number; total: number };

/** A média da Casa do cartão é o total do ano somando os órgãos; ela vai ao lado do total do
 * ano da pessoa, não de cada órgão. */
function linhasDoAno(linhas: LinhaCartao[], ano: number) {
  return linhas.filter((l) => l.ano === ano).length;
}

function totalDoAno(linhas: LinhaCartao[], ano: number) {
  return linhas.filter((l) => l.ano === ano).reduce((soma, l) => soma + l.total, 0);
}

function ultimoDoAno(linhas: LinhaCartao[], i: number) {
  return i === linhas.length - 1 || linhas[i + 1].ano !== linhas[i].ano;
}
