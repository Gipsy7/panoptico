import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { EmendasMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const LIMITE = 10;

export function EmendasMunicipioSecao({ dados }: { dados: EmendasMunicipio }) {
  const cidade = dados.municipio.nome;
  const ultimoAno = dados.por_ano.at(-1)?.ano ?? dados.desde;
  const top = dados.parlamentares.slice(0, LIMITE);
  const maior = Math.max(top[0]?.total ?? 0, dados.outros_autores[0]?.total ?? 0);

  return (
    <section aria-labelledby="emendas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="emendas-titulo" className="text-2xl">
          Dinheiro enviado para {cidade}
        </h2>
        <p className="text-xs text-muted-foreground">
          Emendas parlamentares individuais, orçamentos de {dados.desde} a {ultimoAno}
        </p>
      </div>

      {dados.total === 0 ? (
        <p className="text-muted-foreground">
          Nenhum valor de emenda individual recebido por {cidade} neste período.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3">
            <div className="col-span-2 figura">
              <dt className="text-sm text-muted-foreground">Total recebido</dt>
              <dd className="numero text-4xl">
                {formatarReais(dados.total, true)}
              </dd>
              <dd className="text-sm text-muted-foreground">
                enviado por {dados.numero_autores}{" "}
                {dados.numero_autores === 1 ? "parlamentar" : "parlamentares"}
              </dd>
            </div>
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Prefeitura e fundos municipais</dt>
              <dd className="numero text-2xl">
                {formatarReais(dados.total_prefeitura, true)}
              </dd>
            </div>
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Entidades sem fins lucrativos</dt>
              <dd className="numero text-2xl">
                {formatarReais(dados.total_entidades, true)}
              </dd>
            </div>
          </dl>

          {top.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-medium">Quem mais enviou (em exercício)</h3>
              <ul className="flex flex-col gap-3">
                {top.map(({ parlamentar: p, total, do_estado }) => (
                  <Barra
                    key={p.id}
                    href={`/parlamentar/${p.id}`}
                    rotulo={p.nome_parlamentar}
                    detalhe={
                      [p.partido, p.uf].filter(Boolean).join(" · ") +
                      (do_estado ? "" : " · outro estado")
                    }
                    valor={total}
                    maior={maior}
                  />
                ))}
              </ul>
              {dados.parlamentares.length > LIMITE && (
                <p className="text-sm text-muted-foreground">
                  E mais {dados.parlamentares.length - LIMITE} parlamentares em exercício.
                </p>
              )}
            </div>
          )}

          {dados.outros_autores.length > 0 && (
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

          <p className="text-sm text-muted-foreground">
            Soma o que foi pago à prefeitura, aos fundos municipais e a entidades sem fins
            lucrativos de {cidade}. Não inclui emendas de bancada, de comissão ou de relator, nem
            valores pagos a empresas.
          </p>
        </>
      )}

      <FonteRodape
        fonte={dados.fonte_nome}
        url={dados.fonte_url}
        atualizadoEm={dados.atualizado_em}
      />
    </section>
  );
}

function Barra({
  rotulo,
  detalhe,
  valor,
  maior,
  href,
}: {
  rotulo: string;
  detalhe?: string;
  valor: number;
  maior: number;
  href?: string;
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
      <div className="h-2 w-full rounded-full bg-muted" aria-hidden>
        <div
          className="h-2 rounded-full bg-chart-1 transition-opacity group-hover:opacity-80"
          style={{ width: `${largura}%` }}
        />
      </div>
    </li>
  );
}
