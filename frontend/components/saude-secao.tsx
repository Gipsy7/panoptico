import { FonteRodape } from "@/components/fonte-rodape";
import type { SaudeLugar, SaudeMunicipio } from "@/lib/api";
import { MESES_NOME } from "@/lib/calendario-votacoes";

/**
 * Saúde em "Por dentro" (CNES/DATASUS), no mês mais recente: leitos de internação por mil moradores
 * e quantos são do SUS, leitos de UTI e intermediários, unidades básicas e hospitais, com o estado e
 * o Brasil contados do mesmo jeito.
 */
const um = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const num = (n: number) => n.toLocaleString("pt-BR");

function comparar(dados: SaudeMunicipio, uf: string, campo: keyof SaudeLugar) {
  const e = dados.estado?.[campo];
  const b = dados.brasil?.[campo];
  return [e != null && `${uf}: ${um(e)}`, b != null && `Brasil: ${um(b)}`].filter(Boolean).join(" · ");
}

const pct = (parte: number, todo: number) => (todo > 0 ? ` (${Math.round((100 * parte) / todo)}%)` : "");

export function SaudeResumo({ dados, cidade, uf }: { dados: SaudeMunicipio; cidade: string; uf: string }) {
  const c = dados.cidade;
  if (!c || dados.ano == null || dados.mes == null) return null;
  const quando = `${MESES_NOME[dados.mes - 1]?.toLowerCase() ?? dados.mes} de ${dados.ano}`;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">Leitos de internação, {quando}</dt>
          <dd className="numero text-2xl">{num(c.leitos)}</dd>
          {c.leitos_por_mil != null && (
            <dd className="text-sm">
              {um(c.leitos_por_mil)} a cada mil moradores
              <span className="block text-muted-foreground">{comparar(dados, uf, "leitos_por_mil")}</span>
            </dd>
          )}
          <dd className="text-sm text-muted-foreground">
            {num(c.leitos_sus)} do SUS{pct(c.leitos_sus, c.leitos)}
          </dd>
        </div>
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">Leitos de UTI e cuidados intermediários</dt>
          <dd className="numero text-2xl">{num(c.leitos_complementares)}</dd>
          {c.complementares_por_100_mil != null && (
            <dd className="text-sm">
              {um(c.complementares_por_100_mil)} a cada 100 mil moradores
              <span className="block text-muted-foreground">{comparar(dados, uf, "complementares_por_100_mil")}</span>
            </dd>
          )}
          <dd className="text-sm text-muted-foreground">
            {num(c.leitos_complementares_sus)} do SUS{pct(c.leitos_complementares_sus, c.leitos_complementares)}
          </dd>
        </div>
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">Postos e unidades básicas de saúde</dt>
          <dd className="numero text-2xl">{num(c.ubs)}</dd>
          {c.ubs_por_10_mil != null && (
            <dd className="text-sm">
              {um(c.ubs_por_10_mil)} a cada 10 mil moradores
              <span className="block text-muted-foreground">{comparar(dados, uf, "ubs_por_10_mil")}</span>
            </dd>
          )}
        </div>
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">Hospitais</dt>
          <dd className="numero text-2xl">{num(c.hospitais)}</dd>
          <dd className="text-sm text-muted-foreground">públicos e privados</dd>
        </div>
      </dl>
      <p className="text-sm text-muted-foreground">
        Conta os leitos e as unidades de saúde que ficam em {cidade}, públicos e privados, como estão no cadastro do
        Ministério da Saúde.{c.hospitais === 0 && " Sem hospital aqui, a internação é feita em outra cidade."} Termos oficiais: leitos de
        internação existentes; leitos complementares; centro de saúde/unidade básica e posto de saúde; hospital geral,
        especializado e unidade mista.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
