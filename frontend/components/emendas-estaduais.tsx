import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import type { EmendasDeputadoEstadual, EmendasEstaduaisMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

/** "FULANO DE TAL" vira "Fulano de Tal" quando a fonte manda tudo em maiúsculas. */
function nomeProprio(nome: string) {
  if (nome !== nome.toUpperCase()) return nome;
  return nome
    .toLowerCase()
    .replace(/(^|[\s-])(\p{L})/gu, (_, sep: string, letra: string) => sep + letra.toUpperCase())
    .replace(/\b(De|Da|Do|Das|Dos|E)\b/g, (p) => p.toLowerCase());
}

const RECORTE_SIMPLES =
  "Aparecem só as emendas pagas por convênio ou termo de fomento, quase todas a entidades sem fins lucrativos (hospitais, APAEs, clubes, associações). Os repasses diretos às prefeituras e os da saúde de fundo a fundo ainda não entram.";

/** Emendas de deputados estaduais numa cidade: outra esfera, separada das federais e nunca somada. */
export function EmendasEstaduaisCidade({ dados, cidade }: { dados: EmendasEstaduaisMunicipio; cidade: string }) {
  const autores = dados.por_autor.filter((a) => a.pago > 0 || a.previsto > 0).slice(0, 5);
  const maior = autores[0]?.pago ?? 0;
  return (
    <section aria-labelledby="emendas-estaduais-titulo" className="revelar painel flex flex-col gap-3">
      <div>
        <h3 id="emendas-estaduais-titulo" className="text-xl">
          Emendas de deputados estaduais
        </h3>
        <p className="text-sm text-muted-foreground">
          {dados.casa}. Dinheiro do orçamento do Estado, não da União: não está somado às emendas federais acima.
        </p>
      </div>
      {dados.emendas === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhuma emenda estadual dentro do recorte abaixo foi registrada para {cidade}.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3">
            <div className="figura min-w-0">
              <dt className="text-sm text-muted-foreground">Pago pelo Estado</dt>
              <dd className="numero text-2xl break-words sm:text-3xl">{formatarReais(dados.total_pago, true)}</dd>
            </div>
            <div className="figura min-w-0">
              <dt className="text-sm text-muted-foreground">Previsto no orçamento</dt>
              <dd className="numero text-2xl break-words sm:text-3xl">{formatarReais(dados.total_previsto, true)}</dd>
            </div>
          </dl>
          <p className="text-sm text-muted-foreground">
            {dados.emendas} {dados.emendas === 1 ? "emenda" : "emendas"}. Empenhado (reservado no orçamento):{" "}
            <span className="tabular-nums">{formatarReais(dados.total_empenhado, true)}</span>. Previsto, empenhado e
            pago são etapas diferentes e não se somam.
          </p>
          {autores.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="font-medium">Quem indicou</h4>
              <ul className="flex flex-col gap-3">
                {autores.map((a) => {
                  const largura = maior > 0 ? Math.max(1, (a.pago / maior) * 100) : 0;
                  const nome = nomeProprio(a.autor_nome);
                  return (
                    <li key={`${a.autor_nome}-${a.tipo}`} className="flex flex-col gap-1">
                      <div className="flex items-baseline justify-between gap-3 text-sm">
                        <span className="min-w-0">
                          {a.mandato_id ? (
                            <Link
                              href={`/deputado-estadual/${a.mandato_id}`}
                              className="font-medium underline-offset-2 hover:underline"
                            >
                              {nome}
                            </Link>
                          ) : (
                            <span className="font-medium">{nome}</span>
                          )}
                          <span className="ml-1 text-sm text-muted-foreground">
                            {a.tipo === "bancada" ? "bancada" : a.em_exercicio ? "" : "sem mandato atual"}
                          </span>
                        </span>
                        <span className="shrink-0 font-medium tabular-nums">{formatarReais(a.pago, true)}</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted" aria-hidden>
                        <div className="h-2 rounded-full bg-chart-1" style={{ width: `${largura}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          {dados.favorecidos.length > 0 && (
            <details>
              <summary className="cursor-pointer text-sm font-medium">
                Quem recebeu: os {dados.favorecidos.length} maiores
              </summary>
              <ul className="lista-fios mt-2 flex flex-col">
                {dados.favorecidos.map((f) => (
                  <li key={`${f.nome}-${f.cnpj}`} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                    <span className="min-w-0">{f.nome}</span>
                    <span className="shrink-0 tabular-nums">{formatarReais(f.pago, true)}</span>
                  </li>
                ))}
              </ul>
              {dados.numero_favorecidos > dados.favorecidos.length && (
                <p className="text-sm text-muted-foreground">
                  E mais {dados.numero_favorecidos - dados.favorecidos.length} com valores menores.
                </p>
              )}
            </details>
          )}
        </>
      )}
      <p className="text-sm text-muted-foreground">{RECORTE_SIMPLES}</p>
      <p className="text-sm text-muted-foreground">{dados.recorte}</p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

/** Emendas estaduais de um deputado estadual: total pago com a média da Casa e a lista por município. */
export function EmendasDoDeputadoEstadual({ dados }: { dados: EmendasDeputadoEstadual }) {
  const periodo =
    dados.periodo.inicio != null && dados.periodo.fim != null
      ? dados.periodo.inicio === dados.periodo.fim
        ? `em ${dados.periodo.inicio}`
        : `de ${dados.periodo.inicio} a ${dados.periodo.fim}`
      : "no período coberto";
  return (
    <section aria-labelledby="emendas-estaduais-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="emendas-estaduais-titulo" className="text-2xl">
          Emendas ao orçamento do Estado
        </h2>
        <p className="text-sm text-muted-foreground">
          Dinheiro que o deputado indicou, pago pelo Estado {periodo}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        <div className="figura min-w-0">
          <dt className="text-sm text-muted-foreground">Total pago</dt>
          <dd className="numero text-2xl break-words sm:text-3xl">{formatarReais(dados.total_pago, true)}</dd>
          <dd className="text-sm text-muted-foreground">
            {dados.emendas} {dados.emendas === 1 ? "emenda" : "emendas"}
          </dd>
        </div>
        <div className="figura min-w-0">
          <dt className="text-sm text-muted-foreground">Previsto no orçamento</dt>
          <dd className="numero text-2xl break-words sm:text-3xl">{formatarReais(dados.total_previsto, true)}</dd>
          <dd className="text-sm text-muted-foreground">Empenhado: {formatarReais(dados.total_empenhado, true)}</dd>
        </div>
      </dl>
      {dados.media_casa_pago != null && (
        <div className="flex flex-col gap-1">
          <BarraComparacao
            pessoa={{ rotulo: dados.nome, valor: dados.total_pago }}
            media={{ rotulo: "Média da Assembleia", valor: dados.media_casa_pago }}
            formato="reais"
          />
          <p className="text-sm text-muted-foreground">{dados.media_descricao}</p>
        </div>
      )}
      {dados.por_municipio.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Para onde foi</h3>
          <ul className="lista-fios flex flex-col">
            {dados.por_municipio.map((m) => (
              <li key={`${m.ibge}-${m.nome}`} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="min-w-0">
                  {m.ibge ? (
                    <Link href={`/cidade/${m.ibge}`} className="underline underline-offset-2">
                      {m.nome}
                    </Link>
                  ) : (
                    m.nome
                  )}
                  <span className="block text-sm text-muted-foreground">
                    {m.emendas} {m.emendas === 1 ? "emenda" : "emendas"}
                  </span>
                </span>
                <span className="shrink-0 tabular-nums">{formatarReais(m.pago, true)}</span>
              </li>
            ))}
          </ul>
          {dados.numero_municipios > dados.por_municipio.length && (
            <p className="text-sm text-muted-foreground">
              E mais {dados.numero_municipios - dados.por_municipio.length} municípios com valores menores.
            </p>
          )}
        </div>
      )}
      {dados.itens.length > 0 && (
        <details className="painel">
          <summary className="cursor-pointer font-medium">Quem recebeu: as {dados.itens.length} mais recentes</summary>
          <ul className="lista-fios mt-2 flex flex-col">
            {dados.itens.map((i) => (
              <li key={`${i.codigo}-${i.favorecido}-${i.ano}`} className="flex flex-col gap-1 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="min-w-0 text-sm font-medium">{i.favorecido}</span>
                  <span className="shrink-0 text-sm font-medium tabular-nums">{formatarReais(i.pago, true)}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {[i.ano, i.municipio_nome, i.situacao].filter(Boolean).join(" · ")}
                </p>
                {i.objeto && <p className="text-sm text-muted-foreground">{i.objeto}</p>}
              </li>
            ))}
          </ul>
          {dados.numero_itens > dados.itens.length && (
            <p className="text-sm text-muted-foreground">
              Mostrando {dados.itens.length} de {dados.numero_itens}.
            </p>
          )}
        </details>
      )}
      <p className="text-sm text-muted-foreground">
        {RECORTE_SIMPLES} Previsto, empenhado e pago são etapas diferentes e não se somam. Não está somado às emendas
        federais.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
