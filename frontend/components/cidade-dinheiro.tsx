import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { ContasSecao } from "@/components/contas-secao";
import { EmendasMunicipioSecao } from "@/components/emendas-municipio";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { FornecedoresPncpSecao } from "@/components/fornecedores-pncp-secao";
import { FornecedoresSecao } from "@/components/fornecedores-secao";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { Revelacao } from "@/components/revelacao";
import {
  type DinheiroFederalMunicipio,
  type EmendasMunicipio,
  getContas,
  getDinheiroFederalMunicipio,
  getEmendasMunicipio,
  getFornecedores,
  getFornecedoresPncp,
  getRepresentantes,
} from "@/lib/api";
import { ANO_PADRAO } from "@/components/dinheiro-federal/formatos";
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";

// Estados com o Tribunal de Contas carregado (ver backend/ingestion/fontes.toml).
const UF_COM_TCE = ["SP", "RS"];

/** Metadados da página /cidade/[ibge]. */
export async function metadadosCidade(ibge: string): Promise<Metadata> {
  const r = await getRepresentantes({ municipio: ibge });
  if (!r.ok || !r.dados.localizacao.municipio) return { title: "Dinheiro da cidade" };
  const lugar = `${r.dados.localizacao.municipio}-${r.dados.localizacao.uf}`;
  return {
    title: `Para onde foi o dinheiro de ${lugar}`,
    description: `Emendas parlamentares pagas, contas da prefeitura e fornecedores de ${lugar}, com dados oficiais, fonte e data.`,
  };
}

/** Corpo da página /cidade/[ibge]; `params` ainda é uma Promise (cacheComponents). */
export function PaginaCidade({ params }: { params: Promise<{ ibge: string }> }) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o dinheiro da cidade…" secoes={4} />}>
      {params.then(({ ibge }) => (
        <Cidade ibge={ibge} />
      ))}
    </Revelacao>
  );
}

function rotuloMedia(municipios: number | null | undefined) {
  return municipios ? `Média dos ${municipios.toLocaleString("pt-BR")} municípios do estado` : "Média dos municípios do estado";
}

async function Cidade({ ibge }: { ibge: string }) {
  const rep = await getRepresentantes({ municipio: ibge });
  if (!rep.ok) {
    if (rep.status === 404 || rep.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={rep.mensagem} />;
  }
  const { municipio, uf, estado } = rep.dados.localizacao;
  if (!municipio) notFound();

  const [emendasR, contasR, fornecedoresR, pncpR, federalR] = await Promise.all([
    getEmendasMunicipio(ibge),
    getContas(ibge),
    getFornecedores(ibge),
    getFornecedoresPncp(ibge),
    getDinheiroFederalMunicipio(ibge),
  ]);
  const federal = federalR.ok ? federalR.dados : null;
  const emendas = emendasR.ok ? emendasR.dados : null;
  const contas = contasR.ok ? contasR.dados : null;
  const fornecedores = fornecedoresR.ok ? fornecedoresR.dados : null;
  const pncp = pncpR.ok && pncpR.dados.itens.length > 0 ? pncpR.dados : null;
  const populacao = emendas?.populacao ?? contas?.populacao ?? null;
  const tceCarregado = UF_COM_TCE.includes(uf);
  const capitalComTcm = (uf === "SP" && municipio === "São Paulo") || (uf === "RJ" && municipio === "Rio de Janeiro");

  const maiorAutor = maiorValorDeAutor(emendas);
  const maiorPncp = pncp?.itens.find((f) => !f.ente_publico) ?? null;
  const totalTce = fornecedores ? fornecedores.orgaos.reduce((soma, o) => soma + o.total_pago, 0) : 0;
  // Total de todos os tipos quando a API traz; senão, só as individuais (API antiga).
  const totalEmendas = emendas ? (emendas.total_geral ?? emendas.total) : 0;
  const porHabEmendas = emendas ? (emendas.total_geral != null ? emendas.por_habitante_geral : emendas.por_habitante) : null;
  const mediaEmendas = emendas
    ? emendas.total_geral != null
      ? emendas.media_uf_por_habitante_geral
      : emendas.media_uf_por_habitante
    : null;
  const rotuloPeriodo = emendas
    ? emendas.periodo?.inicio != null && emendas.periodo.fim != null && emendas.periodo.inicio !== emendas.periodo.fim
      ? `de ${emendas.periodo.inicio} a ${emendas.periodo.fim}`
      : `desde ${emendas.periodo?.inicio ?? emendas.desde}`
    : "";
  const temEmendas = totalEmendas > 0;
  const gastoInformado = Boolean(contas && contas.despesa_paga && contas.despesa_por_habitante != null);
  const temCartoes = temEmendas || Boolean(contas) || Boolean(maiorPncp) || totalTce > 0;

  // Cada seção aparece UMA vez, dentro de uma aba; o cartão do topo abre a mesma seção em gaveta.
  const abas: AbaDetalhe[] = [
    {
      id: "entrou",
      rotulo: "Entrou",
      secoes: [
        {
          id: "emendas",
          titulo: "Dinheiro enviado por emendas",
          conteudo: emendas ? (
            <EmendasMunicipioSecao dados={emendas} />
          ) : (
            <SemDado titulo="Dinheiro enviado por emendas" mensagem="Não deu para buscar as emendas desta cidade agora." />
          ),
        },
      ],
    },
    {
      id: "gastou",
      rotulo: "Gastou",
      secoes: [
        {
          id: "contas",
          titulo: `Contas de ${municipio}`,
          conteudo: contas ? (
            <ContasSecao dados={contas} cidade={municipio} />
          ) : (
            <SemDado
              titulo={`Contas de ${municipio}`}
              mensagem="As contas anuais desta prefeitura ainda não estão carregadas."
            />
          ),
        },
      ],
    },
    {
      id: "recebeu",
      rotulo: "Quem recebeu",
      secoes: [
        {
          id: "fornecedores",
          titulo: `Para quem ${municipio} pagou`,
          conteudo: fornecedores ? (
            <FornecedoresSecao dados={fornecedores} cidade={municipio} />
          ) : (
            <SemDado
              titulo={`Para quem ${municipio} pagou`}
              mensagem={
                capitalComTcm
                  ? `${municipio} é fiscalizada pelo Tribunal de Contas do Município (TCM-${uf}), que ainda não foi carregado. O Tribunal de Contas do Estado (TCE-${uf}) não traz os pagamentos desta cidade.`
                  : tceCarregado
                    ? `O Tribunal de Contas do Estado (TCE-${uf}) não trouxe pagamentos desta cidade.`
                    : `Os pagamentos por fornecedor vêm do Tribunal de Contas do Estado, e o de ${estado} ainda não foi carregado.`
              }
            />
          ),
        },
        {
          id: "pncp",
          titulo: "Contratos no PNCP",
          conteudo: pncp && <FornecedoresPncpSecao dados={pncp} cidade={municipio} />,
        },
      ],
    },
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <p className="sobretitulo">Dinheiro público</p>
          <h1 className="titulo-pagina">
            Para onde foi o dinheiro de {municipio}-{uf}
          </h1>
          {populacao != null && (
            <p className="text-muted-foreground">
              <span className="tabular-nums">{populacao.toLocaleString("pt-BR")}</span> habitantes
            </p>
          )}
          <Link
            href={`/representantes?municipio=${ibge}`}
            className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
          >
            Quem representa {municipio}
          </Link>
        </div>

        {temCartoes && (
          <>
            <GradeCartoes rotulo={`Números do dinheiro de ${municipio}`}>
              {emendas && temEmendas && (
                <CartaoNumero
                  destino="emendas"
                  rotulo={`Emendas pagas ${rotuloPeriodo}`}
                  valor={formatarReaisCompacto(totalEmendas)}
                  apoio={emendas.total_geral != null ? "Todos os tipos de emenda" : undefined}
                  largo
                  comparacao={
                    porHabEmendas != null && mediaEmendas != null
                      ? {
                          pessoa: { rotulo: `${municipio}, por morador`, valor: porHabEmendas },
                          media: {
                            rotulo: rotuloMedia(emendas.municipios_na_media),
                            valor: mediaEmendas,
                          },
                          formato: "reais",
                        }
                      : undefined
                  }
                />
              )}
              {contas && (
                <CartaoNumero
                  destino="contas"
                  rotulo={`Prefeitura gastou por morador em ${contas.ano}`}
                  valor={gastoInformado ? formatarReais(contas.despesa_por_habitante!, true) : "Não informado pela fonte"}
                  largo
                  apoio={gastoInformado ? undefined : "O Tesouro Nacional não traz a despesa paga desta prefeitura"}
                  comparacao={
                    gastoInformado && contas.media_uf_despesa_por_habitante != null
                      ? {
                          pessoa: { rotulo: municipio, valor: contas.despesa_por_habitante! },
                          media: {
                            rotulo: rotuloMedia(contas.municipios_na_media),
                            valor: contas.media_uf_despesa_por_habitante,
                          },
                          formato: "reais",
                        }
                      : undefined
                  }
                />
              )}
              {maiorAutor && emendas && (
                <CartaoNumero
                  destino="emendas"
                  rotulo="Maior valor enviado por um parlamentar"
                  valor={formatarReaisCompacto(maiorAutor.total)}
                  apoio={`${maiorAutor.nome}, entre ${emendas.numero_autores} ${emendas.numero_autores === 1 ? "autor" : "autores"}`}
                />
              )}
              {maiorPncp && pncp && (
                <CartaoNumero
                  destino="pncp"
                  rotulo={`Maior contrato no PNCP em ${pncp.ano}`}
                  valor={formatarReaisCompacto(maiorPncp.valor)}
                  apoio={maiorPncp.fornecedor ?? (maiorPncp.nome_omitido ? `MEI (nome omitido por conter CPF) · CNPJ ${maiorPncp.fornecedor_cnpj}` : "Empresa sem nome informado")}
                />
              )}
              {fornecedores && totalTce > 0 && (
                <CartaoNumero
                  destino="fornecedores"
                  rotulo={`Pagamentos a fornecedores em ${fornecedores.ano}`}
                  valor={formatarReaisCompacto(totalTce)}
                  apoio="Segundo o Tribunal de Contas"
                />
              )}
            </GradeCartoes>
            <p className="text-sm text-muted-foreground">Toque num número para ver o detalhe, com a fonte e a data.</p>
          </>
        )}

        {federal && <DinheiroFederalCartao dados={federal} ibge={ibge} uf={uf} municipio={municipio} />}

        <CompartilharWhatsApp
          caminho={`/cidade/${ibge}`}
          texto={`Veja para onde foi o dinheiro de ${municipio}: emendas, contas da prefeitura e fornecedores, com dados oficiais:`}
        />
      </div>

      <ListaPerguntas titulo="Para entender os números">
        {emendas && porHabEmendas != null && mediaEmendas != null && (
          <Pergunta
            id="entender-media-uf"
            pergunta={`Como ${municipio} é comparada com a média dos municípios do estado de ${estado}?`}
            resposta="Cada município conta um, grande ou pequeno"
          >
            <p>
              {municipio} recebeu {formatarReais(porHabEmendas, true)} em emendas por morador. A média dos{" "}
              {emendas.municipios_na_media?.toLocaleString("pt-BR")} municípios de {estado} é{" "}
              {formatarReais(mediaEmendas, true)}.
            </p>
            <BarraComparacao
              pessoa={{ rotulo: municipio, valor: porHabEmendas }}
              media={{ rotulo: "Média dos municípios do estado", valor: mediaEmendas }}
              formato="reais"
            />
            <p>
              É uma média simples: calculamos o valor por morador de cada município e dividimos pelo número de
              municípios, sem pesar pela população. Por isso, uma cidade pequena que recebeu muito para poucos
              moradores puxa a média para cima, e o resultado pode ficar longe do que a maioria das cidades recebeu.
              Não é o total do estado dividido pelos moradores do estado.
            </p>
            <FonteRodape fonte={emendas.fonte_nome} url={emendas.fonte_url} atualizadoEm={emendas.atualizado_em} />
          </Pergunta>
        )}
        {emendas && temEmendas && (
          <Pergunta
            id="entender-destino"
            pergunta="A emenda vai para a prefeitura?"
            resposta={`${formatarReaisCompacto(emendas.total_prefeitura)} para a prefeitura e ${formatarReaisCompacto(emendas.total_entidades)} para entidades`}
          >
            <p>
              Uma parte das emendas é paga à prefeitura e aos fundos municipais; outra parte é paga a entidades sem
              fins lucrativos que atuam na cidade. {emendas.total_geral != null
                ? "Os dois valores contam só as emendas individuais; bancada, comissão e relator ficam de fora desta divisão."
                : `Os dois valores somam o total pago desde ${emendas.desde}.`}
            </p>
            <ComposicaoDestino prefeitura={emendas.total_prefeitura} entidades={emendas.total_entidades} />
            <FonteRodape fonte={emendas.fonte_nome} url={emendas.fonte_url} atualizadoEm={emendas.atualizado_em} />
          </Pergunta>
        )}
        <Pergunta
          id="entender-fora"
          pergunta="O que ficou de fora?"
          resposta="Alguns tipos de emenda e de contrato não entram"
        >
          <ul className="flex list-disc flex-col gap-1 pl-5 text-muted-foreground">
            {emendas?.total_geral != null ? (
              <>
                <li>
                  Pagamentos em que a fonte não identifica o município não entram no total. Os pagamentos sem
                  código de emenda e sem autor entram no total, mas não são atribuídos a nenhum parlamentar.
                </li>
                <li>
                  {emendas.estaduais
                    ? "Emendas de deputados estaduais aparecem à parte, só convênios e termos de fomento; repasses às prefeituras ainda ficam de fora."
                    : "Emendas estaduais (das assembleias legislativas) ainda não foram carregadas."}
                </li>
                <li>
                  O que está previsto e ainda sem pagamento, e os convênios, aparecem separados e nunca somados ao
                  valor pago.
                </li>
              </>
            ) : (
              <>
                <li>
                  As transferências especiais (&quot;emendas Pix&quot;) e os convênios não trazem o município na
                  fonte, então não aparecem nas emendas desta página.
                </li>
                <li>Emendas de bancada, de comissão e de relator não estão somadas, e só entra o valor já pago.</li>
              </>
            )}
            <li>
              Só os Tribunais de Contas de São Paulo e do Rio Grande do Sul estão carregados; os dos demais estados
              ainda não.
            </li>
            <li>Prefeituras que não publicam contratos no PNCP não aparecem na lista de contratos.</li>
          </ul>
        </Pergunta>
        {(emendas?.media_uf_descricao || contas?.media_uf_descricao) && (
          <Pergunta
            id="entender-media"
            pergunta="Como é calculada a média do estado?"
            resposta="Média simples entre os municípios"
          >
            {emendas?.media_uf_descricao && (
              <p>
                <span className="font-medium">Emendas: </span>
                {emendas.media_uf_descricao}
              </p>
            )}
            {contas?.media_uf_descricao && (
              <p>
                <span className="font-medium">Contas da prefeitura: </span>
                {contas.media_uf_descricao}
              </p>
            )}
            <p className="text-muted-foreground">
              A média dá o contexto; não é meta nem nota. Nos gráficos, bronze é sempre esta cidade e cinza é sempre a
              média.
            </p>
          </Pergunta>
        )}
      </ListaPerguntas>

      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />
    </article>
  );
}

/** Maior valor individual: entre os parlamentares em exercício e os outros autores. */
function maiorValorDeAutor(emendas: EmendasMunicipio | null) {
  if (!emendas) return null;
  const a = emendas.parlamentares[0];
  const b = emendas.outros_autores[0];
  if (a && (!b || a.total >= b.total)) return { nome: a.parlamentar.nome_parlamentar, total: a.total };
  if (b) return { nome: b.autor_nome, total: b.total };
  return null;
}

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** Uma barra dividida entre prefeitura e entidades; os valores ficam na legenda. */
function ComposicaoDestino({ prefeitura, entidades }: { prefeitura: number; entidades: number }) {
  const total = prefeitura + entidades;
  if (total <= 0) return null;
  const partes = [
    { rotulo: "Prefeitura e fundos municipais", valor: prefeitura, cor: "bg-bronze" },
    { rotulo: "Entidades sem fins lucrativos", valor: entidades, cor: "bg-chart-2" },
  ].filter((x) => x.valor > 0);
  return (
    <div className="flex flex-col gap-2">
      <div aria-hidden className="flex h-3 w-full gap-px overflow-hidden rounded-[2px] ring-1 ring-border">
        {partes.map((x) => (
          <span key={x.rotulo} className={`${x.cor} h-full`} style={{ flexGrow: x.valor }} />
        ))}
      </div>
      <ul className="flex flex-col gap-1">
        {partes.map((x) => (
          <li key={x.rotulo} className="flex items-center gap-2">
            <span aria-hidden className={`${x.cor} size-3 shrink-0 rounded-[2px] ring-1 ring-border`} />
            <span className="min-w-0 flex-1">{x.rotulo}</span>
            <span className="tabular-nums">
              {formatarReais(x.valor, true)} ({PCT.format((x.valor / total) * 100)}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SemDado({ titulo, mensagem }: { titulo: string; mensagem: string }) {
  return (
    <section className="flex flex-col gap-1">
      <h2 className="text-2xl">{titulo}</h2>
      <p className="text-sm text-muted-foreground">{mensagem}</p>
    </section>
  );
}

/** Cartão com o último ano completo da série de repasses federais, e o link para o mapa. */
function DinheiroFederalCartao({
  dados,
  ibge,
  uf,
  municipio,
}: {
  dados: DinheiroFederalMunicipio;
  ibge: string;
  uf: string;
  municipio: string;
}) {
  // Último ano fechado (o ano em curso soma só os meses já publicados); sem ele, o mais recente.
  const ultimo = dados.serie.filter((s) => s.ano <= ANO_PADRAO).at(-1) ?? dados.serie.at(-1);
  if (!ultimo) return null;
  const fonte = dados.fontes[0];
  const datas = dados.fontes.map((f) => f.atualizado_em).filter((d): d is string => Boolean(d)).sort();
  return (
    <section aria-labelledby="federal-titulo" className="flex flex-col gap-2 rounded-[2px] border border-border bg-card p-4">
      <h2 id="federal-titulo" className="text-xl">
        Repasses da União nesta cidade
      </h2>
      <p className="text-sm text-muted-foreground">Repasses da União à prefeitura de {municipio} em {ultimo.ano}.</p>
      <dl className="grid grid-cols-2 gap-4">
        <div>
          <dt className="text-sm text-muted-foreground">Repassado em {ultimo.ano}</dt>
          <dd className="numero text-2xl">{formatarReaisCompacto(ultimo.repasse)}</dd>
        </div>
        {ultimo.por_habitante != null && (
          <div>
            <dt className="text-sm text-muted-foreground">Por morador</dt>
            <dd className="numero text-2xl">{formatarReais(ultimo.por_habitante, true)}</dd>
            {ultimo.media_estado_por_habitante != null && (
              <dd className="text-sm text-muted-foreground">
                Média de {uf}: <span className="tabular-nums">{formatarReais(ultimo.media_estado_por_habitante, true)}</span>
              </dd>
            )}
          </div>
        )}
      </dl>
      <Link
        href={`/impostos-e-repasses/${uf}/${ibge}`}
        className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
      >
        Ver no mapa
      </Link>
      {fonte && <FonteRodape fonte={fonte.nome} url={fonte.url} atualizadoEm={datas[0] ?? null} />}
    </section>
  );
}
