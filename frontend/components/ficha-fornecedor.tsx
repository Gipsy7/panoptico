/**
 * Ficha do fornecedor (/fornecedor/[cnpj]), no padrão dos painéis: cartões no topo e o detalhe
 * em abas (docs/DECISOES.md, 2026-11-14, protótipo 1B). Só somas, contagens e datas, cada bloco
 * com a fonte e o que ficou de fora. Nenhuma frase diz se um pagamento caiu durante uma sanção.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { Revelacao } from "@/components/revelacao";
import { getFornecedor } from "@/lib/api";
import { CASA_CURTA, formatarData, formatarReais } from "@/lib/formato";
import { type FichaFornecedor, digitosDoCnpj, fichaTemDado, formatarCnpj, frasesDaFicha } from "@/lib/fornecedor";

const INTEIRO = new Intl.NumberFormat("pt-BR");
const n = (v: number) => INTEIRO.format(v);
const ORGAO: Record<string, string> = { prefeitura: "Prefeitura", camara: "Câmara", outros: "Outros órgãos" };

export async function metadadosFornecedor(cnpj: string): Promise<Metadata> {
  // Fora dos buscadores por enquanto: página nova, com registros de sanção; o dono decide depois.
  const base: Metadata = { robots: { index: false, follow: true } };
  const d = digitosDoCnpj(cnpj);
  if (!d) return { ...base, title: "Página não encontrada" };
  const r = await getFornecedor(d);
  if (!r.ok) return { ...base, title: r.status === 404 ? "Página não encontrada" : "Fornecedor" };
  const nome = r.dados.nome ?? `CNPJ ${formatarCnpj(d)}`;
  return {
    ...base,
    title: `${nome}: o que os dados públicos registram`,
    description: `Pagamentos de gabinetes, prefeituras e câmaras, contratos no PNCP, emendas e sanções da CGU ligados ao CNPJ ${formatarCnpj(d)}, com fonte e data.`,
  };
}

export function PaginaFornecedor({ params }: { params: Promise<{ cnpj: string }> }) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando a ficha…" secoes={2} />}>
      {params.then(({ cnpj }) => (
        <Ficha cnpj={cnpj} />
      ))}
    </Revelacao>
  );
}

async function Ficha({ cnpj }: { cnpj: string }) {
  const digitos = digitosDoCnpj(cnpj);
  if (!digitos) notFound();
  const r = await getFornecedor(digitos);
  if (!r.ok) {
    if (r.status === 404 || r.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={r.mensagem} />;
  }
  const f = r.dados;
  const frases = frasesDaFicha(f);
  const g = f.gabinetes.por_ano[0];
  const p = f.prefeituras.por_ano[0];
  const c = f.pncp.por_ano[0];
  const e = f.emendas.pagas_por_ano[0];
  const nome = f.nome ?? (f.nome_omitido ? "MEI (nome omitido por conter CPF)" : `CNPJ ${formatarCnpj(f.cnpj)}`);

  const abas: AbaDetalhe[] = [
    ...(g ? [{ id: "gabinetes", rotulo: "Gabinetes", tema: "dinheiro" as const, secoes: [{ id: "gabinetes", titulo: "Pagamentos de gabinetes", conteudo: <Gabinetes f={f} /> }] }] : []),
    ...(p ? [{ id: "prefeituras", rotulo: "Prefeituras", tema: "dinheiro" as const, secoes: [{ id: "prefeituras", titulo: "Pagamentos de prefeituras e câmaras", conteudo: <Prefeituras f={f} /> }] }] : []),
    ...(c ? [{ id: "pncp", rotulo: "Contratos", tema: "obras" as const, secoes: [{ id: "pncp", titulo: "Contratos no PNCP", conteudo: <Pncp f={f} /> }] }] : []),
    ...(e || f.emendas.convenios.quantidade > 0
      ? [{ id: "emendas", rotulo: "Emendas", tema: "dinheiro" as const, secoes: [{ id: "emendas", titulo: "Emendas parlamentares", conteudo: <Emendas f={f} /> }] }]
      : []),
    { id: "sancoes", rotulo: "Sanções", tema: "seguranca" as const, secoes: [{ id: "sancoes", titulo: "Sanções da CGU", conteudo: <Sancoes f={f} /> }] },
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="sobretitulo">Empresa · CNPJ {formatarCnpj(f.cnpj)}</p>
          <h1 className="titulo-pagina">{nome}</h1>
          {(f.nome_fantasia || f.uf || f.situacao) && (
            <p className="text-muted-foreground">
              {[f.nome_fantasia, f.uf, f.situacao && `situação na Receita Federal: ${f.situacao}`].filter(Boolean).join(" · ")}
            </p>
          )}
          <p className="text-sm text-muted-foreground">
            O que os dados que o Panóptico acompanha registram sobre este CNPJ. A ligação é o número do CNPJ, igual ao
            que cada fonte publica; não é feita por nome.
          </p>
        </div>

        {fichaTemDado(f) ? (
          <>
            <GradeCartoes rotulo="Números deste CNPJ">
              {g && (
                <CartaoNumero destino="gabinetes" tema="dinheiro" rotulo={`Gabinetes, ${g.ano}`} valor={formatarReais(g.valor, true)} apoio={frases.gabinetes ?? undefined} />
              )}
              {p && (
                <CartaoNumero destino="prefeituras" tema="dinheiro" rotulo={`Prefeituras e câmaras, ${p.ano}`} valor={formatarReais(p.valor, true)} apoio={frases.prefeituras ?? undefined} />
              )}
              {c && <CartaoNumero destino="pncp" rotulo={`Contratos no PNCP, ${c.ano}`} valor={formatarReais(c.valor, true)} apoio={frases.pncp ?? undefined} />}
              {(e || f.emendas.convenios.quantidade > 0) && (
                <CartaoNumero
                  destino="emendas"
                  rotulo={e ? `Emendas pagas, ${e.ano}` : "Convênios de emendas"}
                  valor={formatarReais(e ? e.valor : f.emendas.convenios.valor_repassado, true)}
                  apoio={frases.emendas ?? undefined}
                />
              )}
              <CartaoNumero destino="sancoes" rotulo="Sanções da CGU" valor={f.sancoes.itens.length === 0 ? "Nenhuma" : n(f.sancoes.itens.length)} apoio={frases.sancoes} />
            </GradeCartoes>
            <p className="text-sm text-muted-foreground">Toque ou clique num número para ver o detalhe, com a fonte e a data.</p>
          </>
        ) : (
          <p className="nota text-sm">
            Este CNPJ está no cadastro, mas não aparece em nenhum dos dados que acompanhamos (gabinetes, prefeituras,
            PNCP, emendas e sanções).
          </p>
        )}
      </div>

      {fichaTemDado(f) && <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />}
    </article>
  );
}

function PorAno({ legenda, colunas, linhas }: { legenda: string; colunas: string[]; linhas: (string | number)[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[18rem] text-sm tabular-nums">
        <caption className="sr-only">{legenda}</caption>
        <thead>
          <tr className="text-left text-muted-foreground">
            {colunas.map((col, i) => (
              <th key={col} scope="col" className={`py-2 font-medium ${i === 0 ? "pr-3" : "pl-3 text-right"}`}>
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={linha[0]} className="border-t">
              {linha.map((v, i) =>
                i === 0 ? (
                  <th key={i} scope="row" className="py-2 pr-3 text-left font-medium">
                    {v}
                  </th>
                ) : (
                  <td key={i} className="py-2 pl-3 text-right">
                    {v}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Rodape({ recorte, fonte, url, atualizadoEm }: { recorte: string; fonte: string; url?: string; atualizadoEm: string | null }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-muted-foreground">
        <span className="font-medium">O que entra e o que fica de fora:</span> {recorte}
      </p>
      <FonteRodape fonte={fonte} url={url} atualizadoEm={atualizadoEm} semAviso />
    </div>
  );
}

function Gabinetes({ f }: { f: FichaFornecedor }) {
  const b = f.gabinetes;
  return (
    <section aria-labelledby="gabinetes-titulo" className="flex flex-col gap-4">
      <h3 id="gabinetes-titulo" className="text-2xl">
        Pagamentos de gabinetes
      </h3>
      <PorAno
        legenda="Pagamentos de gabinetes por ano"
        colunas={["Ano", "Total pago", "Gabinetes", "Lançamentos"]}
        linhas={b.por_ano.map((a) => [a.ano, formatarReais(a.valor, true), n(a.gabinetes), n(a.lancamentos)])}
      />
      {b.maiores.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="font-medium">
            Gabinetes que mais pagaram em {b.ano_da_lista}
            {b.maiores.length === b.limite_da_lista ? ` (os ${b.limite_da_lista} maiores valores)` : ""}
          </h4>
          <ol className="lista-fios flex flex-col">
            {b.maiores.map((m) => (
              <li key={m.parlamentar_id} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="min-w-0">
                  <Link href={`/parlamentar/${m.parlamentar_id}`} className="inline-block min-h-6 font-medium underline underline-offset-2">
                    {m.nome}
                  </Link>{" "}
                  <span className="text-muted-foreground">
                    {CASA_CURTA[m.casa]} · {[m.partido, m.uf].filter(Boolean).join("-")}
                  </span>
                </span>
                <span className="shrink-0 tabular-nums">{formatarReais(m.valor, true)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
      <Rodape recorte={b.recorte} fonte={b.fonte_nome} atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function Prefeituras({ f }: { f: FichaFornecedor }) {
  const b = f.prefeituras;
  return (
    <section aria-labelledby="prefeituras-titulo" className="flex flex-col gap-4">
      <h3 id="prefeituras-titulo" className="text-2xl">
        Pagamentos de prefeituras e câmaras
      </h3>
      <PorAno
        legenda="Pagamentos de prefeituras e câmaras por ano"
        colunas={["Ano", "Total pago", "Cidades"]}
        linhas={b.por_ano.map((a) => [a.ano, formatarReais(a.valor, true), n(a.municipios)])}
      />
      {b.maiores.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="font-medium">Onde, em {b.ano_da_lista}</h4>
          <ol className="lista-fios flex flex-col">
            {b.maiores.map((m) => (
              <li key={`${m.ibge}-${m.orgao}`} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="min-w-0">
                  <Link href={`/cidade/${m.ibge}`} className="inline-block min-h-6 font-medium underline underline-offset-2">
                    {m.municipio}
                  </Link>{" "}
                  <span className="text-muted-foreground">
                    {m.uf} · {ORGAO[m.orgao] ?? m.orgao}
                  </span>
                </span>
                <span className="shrink-0 tabular-nums">{formatarReais(m.valor, true)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
      <Rodape recorte={b.recorte} fonte={b.fonte_nome} atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function Pncp({ f }: { f: FichaFornecedor }) {
  const b = f.pncp;
  return (
    <section aria-labelledby="pncp-titulo" className="flex flex-col gap-4">
      <h3 id="pncp-titulo" className="text-2xl">
        Contratos no PNCP
      </h3>
      <PorAno
        legenda="Contratos no PNCP por ano"
        colunas={["Ano", "Valor dos contratos", "Contratos", "Cidades"]}
        linhas={b.por_ano.map((a) => [a.ano, formatarReais(a.valor, true), n(a.contratos), n(a.municipios)])}
      />
      <Rodape recorte={b.recorte} fonte={b.fonte_nome} url="https://pncp.gov.br/" atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function Emendas({ f }: { f: FichaFornecedor }) {
  const b = f.emendas;
  return (
    <section aria-labelledby="emendas-titulo" className="flex flex-col gap-4">
      <h3 id="emendas-titulo" className="text-2xl">
        Emendas parlamentares
      </h3>
      {b.pagas_por_ano.length > 0 && (
        <PorAno
          legenda="Emendas pagas a este CNPJ por ano"
          colunas={["Ano", "Pago", "Autores"]}
          linhas={b.pagas_por_ano.map((a) => [a.ano, formatarReais(a.valor, true), n(a.autores)])}
        />
      )}
      {b.convenios.quantidade > 0 && (
        <p className="text-sm">
          {n(b.convenios.quantidade)} {b.convenios.quantidade === 1 ? "convênio ou transferência" : "convênios ou transferências"}{" "}
          de emendas em que este CNPJ é o beneficiário, com{" "}
          <strong>{formatarReais(b.convenios.valor_repassado, true)}</strong> repassados.
        </p>
      )}
      <Rodape recorte={b.recorte} fonte={b.fonte_nome} url="https://portaldatransparencia.gov.br/emendas" atualizadoEm={b.atualizado_em} />
    </section>
  );
}

function Sancoes({ f }: { f: FichaFornecedor }) {
  const b = f.sancoes;
  return (
    <section aria-labelledby="sancoes-titulo" className="flex flex-col gap-4">
      <h3 id="sancoes-titulo" className="text-2xl">
        Sanções da CGU
      </h3>
      {b.itens.length === 0 ? (
        <p className="text-sm">Nenhum registro com este CNPJ nos cadastros de sanções da CGU (CEIS e CNEP).</p>
      ) : (
        <>
          <ol className="lista-fios flex flex-col">
            {b.itens.map((s, i) => (
              <li key={i} className="flex flex-col gap-1 py-3 text-sm">
                <span className="font-medium">
                  {s.categoria} <span className="font-normal text-muted-foreground">({s.cadastro})</span>
                </span>
                <span>
                  {s.inicio ? `De ${formatarData(s.inicio)}` : "Início não informado"}
                  {s.fim ? ` a ${formatarData(s.fim)}` : ", sem data de fim informada pela fonte"}
                </span>
                <span className="text-muted-foreground">
                  {[s.orgao && `Órgão: ${s.orgao}`, s.abrangencia && `Vale: ${s.abrangencia}`, s.processo && `Processo ${s.processo}`]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ol>
          <p className="text-sm text-muted-foreground">
            Cada sanção vale para o período e a abrangência escritos acima. Esta página não diz se um pagamento ou
            contrato aconteceu durante uma sanção: os valores das outras abas são somados por ano.
          </p>
        </>
      )}
      <Rodape recorte={b.recorte} fonte={b.fonte_nome} url={b.fonte_url} atualizadoEm={b.atualizado_em} />
    </section>
  );
}
