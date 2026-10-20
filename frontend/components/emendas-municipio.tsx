import Link from "next/link";

import { EmendasEstaduaisCidade } from "@/components/emendas-estaduais";
import { FonteRodape } from "@/components/fonte-rodape";
import type { EmendasMunicipio } from "@/lib/api";
import { formatarReais, MESES } from "@/lib/formato";

const LIMITE = 5;

export function EmendasMunicipioSecao({ dados }: { dados: EmendasMunicipio }) {
  const cidade = dados.municipio.nome;
  const novo = dados.total_geral != null;
  const total = dados.total_geral ?? dados.total;
  const porHabitante = novo ? dados.por_habitante_geral : dados.por_habitante;
  const mediaUf = novo ? dados.media_uf_por_habitante_geral : dados.media_uf_por_habitante;
  const inicio = dados.periodo?.inicio ?? dados.desde;
  const fim = dados.periodo?.fim ?? dados.por_ano.at(-1)?.ano ?? dados.desde;
  const periodo = inicio === fim ? `${inicio}` : `de ${inicio} a ${fim}`;
  const tipos = (dados.tipos ?? []).filter((t) => t.total > 0);
  const colegiados = dados.colegiados ?? [];
  const nAutores = novo
    ? (dados.autores_com_mandato ?? 0) + (dados.autores_sem_mandato ?? 0)
    : dados.numero_autores;

  // Autores com e sem mandato atual numa lista só, do maior valor para o menor.
  const autores: AutorLinha[] = [
    ...dados.parlamentares.map((x) => ({
      chave: `p${x.parlamentar.id}`,
      rotulo: x.parlamentar.nome_parlamentar,
      detalhe: [x.parlamentar.partido, x.parlamentar.uf].filter(Boolean).join(" · ") + (x.do_estado ? "" : " · outro estado"),
      total: x.total,
      href: `/parlamentar/${x.parlamentar.id}`,
      semMandato: false,
    })),
    ...(novo ? dados.outros_autores : []).map((a) => ({
      chave: `o${a.autor_nome}`,
      rotulo: nomeProprio(a.autor_nome),
      detalhe: undefined,
      total: a.total,
      href: a.parlamentar_id ? `/parlamentar/${a.parlamentar_id}` : undefined,
      semMandato: a.com_mandato_atual === false,
    })),
  ].sort((a, b) => b.total - a.total);
  const top = autores.slice(0, LIMITE);
  const resto = autores.slice(LIMITE);
  const maior = Math.max(autores[0]?.total ?? 0, dados.outros_autores[0]?.total ?? 0);
  // O bloco aparece com previsto sem pagamento ou só com planos impedidos (que nunca somam).
  const previsto =
    dados.previsto && (dados.previsto.valor_sem_pagamento > 0 || (dados.previsto.impedidos?.planos ?? 0) > 0)
      ? dados.previsto
      : null;
  const semId = dados.sem_identificacao && dados.sem_identificacao.total > 0 ? dados.sem_identificacao : null;
  const convenios = dados.convenios && dados.convenios.quantidade > 0 ? dados.convenios : null;

  return (
    <section aria-labelledby="emendas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="emendas-titulo" className="text-2xl">
          Dinheiro enviado para {cidade}
        </h2>
        <p className="text-xs text-muted-foreground">
          {novo
            ? `Emendas parlamentares de todos os tipos, pagas ${periodo}`
            : `Emendas parlamentares individuais, orçamentos de ${dados.desde} a ${fim}`}
        </p>
      </div>

      {total === 0 && !previsto && !convenios ? (
        <p className="text-muted-foreground">
          Nenhum valor de emenda recebido por {cidade} neste período.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3">
            <div className="col-span-2 figura">
              <dt className="text-sm text-muted-foreground">Total pago à cidade</dt>
              <dd className="numero text-4xl">
                {formatarReais(total, true)}
              </dd>
              <dd className="text-sm text-muted-foreground">
                {novo ? `pagos ${periodo}` : `pagos desde ${dados.desde}`}, enviados por {nAutores}{" "}
                {nAutores === 1 ? "parlamentar" : "parlamentares"}
                {novo && colegiados.length > 0 && " e por bancadas, comissões ou relatores"}
              </dd>
            </div>
            {porHabitante != null && (
              <div className="col-span-2 figura">
                <dt className="text-sm text-muted-foreground">Por habitante</dt>
                <dd className="numero text-2xl">{formatarReais(porHabitante, true)}</dd>
                {mediaUf != null && (
                  <dd className="text-sm text-muted-foreground">
                    Média dos {dados.municipios_na_media?.toLocaleString("pt-BR")} municípios de{" "}
                    {dados.municipio.uf}: {formatarReais(mediaUf, true)} por habitante
                    {dados.media_uf_descricao && (
                      <span className="block text-xs">{dados.media_uf_descricao}</span>
                    )}
                  </dd>
                )}
              </div>
            )}
          </dl>

          {tipos.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-medium">Por tipo de emenda</h3>
              <ul className="flex flex-col gap-3">
                {tipos.map((t) => (
                  <Barra
                    key={t.tipo}
                    rotulo={t.rotulo}
                    detalhe={t.rotulo_oficial}
                    valor={t.total}
                    maior={tipos[0].total}
                    nota={
                      (t.sem_codigo_total ?? 0) > 0
                        ? `inclui ${formatarReais(t.sem_codigo_total ?? 0, true)} sem autor informado pela fonte`
                        : undefined
                    }
                  />
                ))}
              </ul>
            </div>
          )}

          <dl className="grid grid-cols-2 gap-3">
            <div className="figura">
              <dt className="text-sm text-muted-foreground">
                Prefeitura e fundos municipais{novo && " (só emendas individuais)"}
              </dt>
              <dd className="numero text-2xl">
                {formatarReais(dados.total_prefeitura, true)}
              </dd>
            </div>
            <div className="figura">
              <dt className="text-sm text-muted-foreground">
                Entidades sem fins lucrativos{novo && " (só emendas individuais)"}
              </dt>
              <dd className="numero text-2xl">
                {formatarReais(dados.total_entidades, true)}
              </dd>
            </div>
          </dl>

          {top.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-medium">
                {novo
                  ? "Maiores valores enviados por parlamentares (emendas individuais)"
                  : "Maiores valores enviados (parlamentares em exercício)"}
              </h3>
              <ul className="flex flex-col gap-3">
                {top.map((x) => (
                  <BarraAutor key={x.chave} x={x} maior={maior} />
                ))}
              </ul>
              {resto.length > 0 && (
                <details className="painel">
                  <summary className="cursor-pointer font-medium">
                    Ver todos os {autores.length} (mais {resto.length})
                  </summary>
                  <ul className="mt-3 flex flex-col gap-3">
                    {resto.map((x) => (
                      <BarraAutor key={x.chave} x={x} maior={maior} />
                    ))}
                  </ul>
                </details>
              )}
              {semId && (
                <p className="painel flex flex-col gap-1 text-sm">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 font-medium">Autor não informado pela fonte (CGU)</span>
                    <span className="shrink-0 font-medium tabular-nums">{formatarReais(semId.total, true)}</span>
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {semId.pagamentos} {semId.pagamentos === 1 ? "pagamento" : "pagamentos"}
                    {periodoMes(semId.primeiro_pagamento, semId.ultimo_pagamento)}. A fonte publica esses
                    pagamentos sem o código da emenda e sem o nome do autor; o valor está no total, mas não é
                    atribuído a ninguém.
                  </span>
                </p>
              )}
              {novo && (dados.autores_sem_mandato ?? 0) > 0 && (
                <p className="text-xs text-muted-foreground">
                  &quot;Sem mandato atual&quot; indica quem enviou o dinheiro em anos anteriores e hoje não exerce
                  mandato de deputado ou senador.
                </p>
              )}
            </div>
          )}

          {!novo && dados.outros_autores.length > 0 && (
            <details className="painel">
              <summary className="cursor-pointer font-medium">
                Outros autores (fora de exercício ou não identificados)
              </summary>
              <ul className="mt-3 flex flex-col gap-3">
                {dados.outros_autores.map((a) => (
                  <Barra key={a.autor_nome} rotulo={a.autor_nome} valor={a.total} maior={maior} />
                ))}
              </ul>
            </details>
          )}

          {colegiados.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-medium">Bancadas, comissões e relatores</h3>
              <p className="text-xs text-muted-foreground">
                Nestes tipos o autor é um grupo, não um parlamentar.
              </p>
              <ul className="flex flex-col gap-3">
                {colegiados.map((c) => (
                  <Barra
                    key={`${c.tipo}-${c.autor_nome}`}
                    rotulo={nomeProprio(c.autor_nome)}
                    detalhe={c.rotulo}
                    valor={c.total}
                    maior={colegiados[0].total}
                  />
                ))}
              </ul>
            </div>
          )}

          {previsto && (
            <div className="painel flex flex-col gap-2">
              <h3 className="font-medium">Previsto, ainda sem pagamento registrado</h3>
              {previsto.valor_sem_pagamento > 0 ? (
                <>
                  <p className="numero text-2xl">{formatarReais(previsto.valor_sem_pagamento, true)}</p>
                  <p className="text-sm text-muted-foreground">
                    {previsto.planos_sem_pagamento}{" "}
                    {previsto.planos_sem_pagamento === 1 ? "plano de trabalho" : "planos de trabalho"} de
                    transferência especial (&quot;emenda Pix&quot;). Este valor não está somado ao total pago acima.
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Nenhum plano de transferência especial (&quot;emenda Pix&quot;) válido sem pagamento registrado.
                </p>
              )}
              {previsto.descricao && <p className="text-xs text-muted-foreground">{previsto.descricao}</p>}
              {previsto.impedidos && (
                <p className="text-xs text-muted-foreground">
                  Fora desta conta: {previsto.impedidos.planos}{" "}
                  {previsto.impedidos.planos === 1 ? "plano" : "planos"} (
                  {formatarReais(previsto.impedidos.valor, true)}) que o TransfereGov marca como
                  impedidos ({previsto.impedidos.motivos.map((m) => m.situacao.toLowerCase()).join("; ")}).
                </p>
              )}
              {previsto.sem_pagamento.length > 0 && (
                <details>
                  <summary className="cursor-pointer text-sm font-medium">Ver os planos</summary>
                  <ul className="lista-fios mt-2 flex flex-col">
                    {previsto.sem_pagamento.map((p) => (
                      <li key={p.identificador} className="flex flex-col gap-1 py-3">
                        <div className="flex items-baseline justify-between gap-3">
                          <span className="min-w-0 text-sm font-medium">
                            {p.autor_nome ? nomeProprio(p.autor_nome) : "Autor não identificado"}
                          </span>
                          <span className="shrink-0 text-sm font-medium tabular-nums">
                            {formatarReais(p.valor, true)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Plano de {p.ano}
                          {p.autor_nome && !p.com_mandato_atual && " · sem mandato atual"}
                          {p.beneficiario && ` · ${p.beneficiario}`}
                          {p.situacao && ` · ${p.situacao}`}
                        </p>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              <FonteRodape
                fonte={previsto.fonte_nome}
                url={previsto.fonte_url}
                atualizadoEm={previsto.atualizado_em}
              />
            </div>
          )}

          {convenios && (
            <div className="painel flex flex-col gap-2">
              <h3 className="font-medium">Convênios ligados a emendas</h3>
              <p className="numero text-2xl">{formatarReais(convenios.valor_total, true)}</p>
              <p className="text-sm text-muted-foreground">
                {convenios.quantidade} {convenios.quantidade === 1 ? "convênio" : "convênios"}, dos quais{" "}
                {formatarReais(convenios.valor_liberado, true)} já liberados. Convênio é um acordo com o governo
                federal para uma obra ou serviço; os valores não estão somados ao total pago acima.
              </p>
              {convenios.descricao && <p className="text-xs text-muted-foreground">{convenios.descricao}</p>}
              <FonteRodape
                fonte={convenios.fonte_nome}
                url={convenios.fonte_url}
                atualizadoEm={convenios.atualizado_em}
              />
            </div>
          )}

          {(dados.por_area ?? []).length > 0 && (
            <details className="painel">
              <summary className="cursor-pointer font-medium">Para quais áreas</summary>
              <ul className="mt-3 flex flex-col gap-3">
                {dados.por_area.map((a) => (
                  <Barra
                    key={a.area}
                    rotulo={a.area}
                    detalhe={`${a.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`}
                    valor={a.total}
                    maior={dados.por_area[0].total}
                  />
                ))}
              </ul>
              <p className="mt-3 text-xs text-muted-foreground">
                Área é a função do orçamento a que a emenda pertence.
                {dados.por_area.some((a) => a.area === "Encargos especiais") &&
                  " \"Encargos especiais\" reúne, entre outras, as transferências especiais (as \"emendas Pix\"), em que o dinheiro vai direto para o caixa da prefeitura sem área definida."}
              </p>
            </details>
          )}

          {(dados.favorecidos ?? []).length > 0 && (
            <details className="painel">
              <summary className="cursor-pointer font-medium">
                Quem recebeu: os {dados.favorecidos.length} maiores
              </summary>
              <ul className="lista-fios mt-3 flex flex-col">
                {dados.favorecidos.map((f) => (
                  <li key={f.cnpj} className="flex flex-col gap-1 py-3">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="min-w-0 text-sm font-medium">{f.nome}</span>
                      <span className="shrink-0 text-sm font-medium tabular-nums">
                        {formatarReais(f.total, true)}
                      </span>
                    </div>
                    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                      <span className="pilula">{f.grupo === "entidade" ? "Entidade" : "Prefeitura ou fundo"}</span>
                      <span className="tabular-nums">CNPJ {formatarCnpj(f.cnpj)}</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Enviado por{" "}
                      {f.autores.map((a, i) => (
                        <span key={a.autor_nome}>
                          {i > 0 && (i === f.autores.length - 1 ? " e " : ", ")}
                          {a.parlamentar_id ? (
                            <Link href={`/parlamentar/${a.parlamentar_id}`} className="underline underline-offset-2">
                              {nomeProprio(a.autor_nome)}
                            </Link>
                          ) : (
                            nomeProprio(a.autor_nome)
                          )}
                        </span>
                      ))}
                    </p>
                  </li>
                ))}
              </ul>
              {dados.numero_favorecidos > dados.favorecidos.length && (
                <p className="text-sm text-muted-foreground">
                  E mais {dados.numero_favorecidos - dados.favorecidos.length} que receberam valores menores.
                </p>
              )}
            </details>
          )}

          {novo ? (
            <p className="text-sm text-muted-foreground">
              O total soma só o que foi pago, de todos os tipos de emenda. O que está previsto e os convênios
              aparecem à parte. Os pagamentos sem código de emenda na fonte (sem autor informado) entram no
              total, mas não em nome de nenhum parlamentar. Ficam de fora: pagamentos em que a fonte não
              identifica o município
              {dados.estaduais
                ? ". As emendas de deputados estaduais aparecem à parte, abaixo, e nunca são somadas."
                : " e emendas estaduais, que ainda não foram carregadas."}
              {!semId && dados.sem_codigo_descricao && ` ${dados.sem_codigo_descricao}`}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Soma o que foi pago à prefeitura, aos fundos municipais e a entidades sem fins
              lucrativos de {cidade}. Não inclui emendas de bancada, de comissão ou de relator, nem
              valores pagos a empresas. Só o que já foi pago, não o que foi prometido (empenhado).
            </p>
          )}
        </>
      )}

      <FonteRodape
        fonte={dados.fonte_nome}
        url={dados.fonte_url}
        atualizadoEm={dados.atualizado_em}
      />

      {dados.estaduais && <EmendasEstaduaisCidade dados={dados.estaduais} cidade={cidade} />}
    </section>
  );
}

type AutorLinha = {
  chave: string;
  rotulo: string;
  detalhe?: string;
  total: number;
  href?: string;
  semMandato: boolean;
};

function BarraAutor({ x, maior }: { x: AutorLinha; maior: number }) {
  const detalhe = [x.detalhe, x.semMandato ? "sem mandato atual" : null].filter(Boolean).join(" · ");
  return <Barra href={x.href} rotulo={x.rotulo} detalhe={detalhe || undefined} valor={x.total} maior={maior} />;
}

function periodoMes(ini: number | null, fim: number | null) {
  const f = (v: number) => `${MESES[(v % 100) - 1] ?? ""}/${Math.floor(v / 100)}`;
  if (!ini || !fim) return "";
  return ini === fim ? `, em ${f(ini)}` : `, de ${f(ini)} a ${f(fim)}`;
}

function formatarCnpj(c: string) {
  const d = c.replace(/\D/g, "");
  return d.length === 14 ? d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5") : c;
}

// Os nomes dos autores vêm em maiúsculas da fonte ("FULANO DE TAL").
function nomeProprio(nome: string) {
  if (nome !== nome.toUpperCase()) return nome;
  return nome
    .toLowerCase()
    .replace(/(^|[\s-])(\p{L})/gu, (_, sep: string, letra: string) => sep + letra.toUpperCase())
    .replace(/\b(De|Da|Do|Das|Dos|E)\b/g, (p) => p.toLowerCase());
}

function Barra({
  rotulo,
  detalhe,
  valor,
  maior,
  href,
  nota,
}: {
  rotulo: string;
  detalhe?: string;
  valor: number;
  maior: number;
  href?: string;
  nota?: string;
}) {
  const largura = maior > 0 ? Math.max(1, (valor / maior) * 100) : 0;
  return (
    <li className="group flex flex-col gap-1" title={`${rotulo}: ${formatarReais(valor)}`}>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="min-w-0">
          {href ? (
            <Link href={href} className="font-medium underline-offset-2 hover:underline">
              {rotulo}
            </Link>
          ) : (
            <span className="font-medium">{rotulo}</span>
          )}
          {detalhe && <span className="ml-1 text-xs text-muted-foreground">{detalhe}</span>}
        </span>
        <span className="shrink-0 font-medium tabular-nums">{formatarReais(valor, true)}</span>
      </div>
      {nota && <p className="text-xs text-muted-foreground">{nota}</p>}
      <div className="h-2 w-full rounded-full bg-muted" aria-hidden>
        <div
          className="h-2 rounded-full bg-chart-1 transition-opacity group-hover:opacity-80"
          style={{ width: `${largura}%` }}
        />
      </div>
    </li>
  );
}
