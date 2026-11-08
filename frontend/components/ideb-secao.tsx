import { FonteRodape } from "@/components/fonte-rodape";
import type { IdebMunicipio, IdebPonto, IdebRede } from "@/lib/api";

/**
 * IDEB da cidade (INEP), escola pública, com o do estado e o do Brasil na mesma rede.
 * Gráfico de linha (dataviz): escala fixa de 0 a 10, a do próprio índice, para não exagerar
 * diferenças; a cidade em bronze (a cor de "esta cidade" no site), estado em cinza contínuo e
 * Brasil em cinza tracejado (identidade nunca só pela cor), legenda, rótulo direto no último
 * ponto, dica nativa em cada ponto e a tabela com todos os números.
 */

const REDE: Record<string, string> = {
  municipal: "rede municipal",
  estadual: "rede estadual",
  publica: "escolas públicas (municipais, estaduais e federais)",
  federal: "rede federal",
};

const nota = (v: number) => v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const ultimo = (s: IdebPonto[]) => (s.length ? s[s.length - 1] : null);

/** A rede comparada: as escolas públicas juntas, que existem nos três níveis (cidade, estado, país). */
export function redeComparada(redes: IdebRede[]): IdebRede | null {
  return redes.find((r) => r.rede === "publica") ?? redes[0] ?? null;
}

const L = 44;
const R = 84;
const T = 12;
const B = 28;
const W = 560;
const H = 220;

/** Faixa de um mandato no fundo da série: só situa no tempo, não atribui o número a ninguém. */
export type FaixaMandato = { inicio: number; fim: number; rotulo: string };

function SerieIdeb({
  rede,
  cidade,
  uf,
  faixas = [],
}: {
  rede: IdebRede;
  cidade: string;
  uf: string;
  faixas?: FaixaMandato[];
}) {
  const anos = [...new Set([...rede.serie, ...rede.uf, ...rede.brasil].map((p) => p.ano))].sort((a, b) => a - b);
  if (anos.length < 2) return null;
  const x = (ano: number) => L + ((ano - anos[0]) / (anos[anos.length - 1] - anos[0])) * (W - L - R);
  const y = (v: number) => T + (1 - v / 10) * (H - T - B);
  const linhas = [
    { nome: cidade, pontos: rede.serie, cor: "var(--bronze)", traco: undefined, largura: 2.5, marcador: true },
    { nome: uf, pontos: rede.uf, cor: "var(--tema-eleicoes)", traco: undefined, largura: 2, marcador: false },
    { nome: "Brasil", pontos: rede.brasil, cor: "var(--tema-eleicoes)", traco: "6 4", largura: 2, marcador: false },
  ].filter((l) => l.pontos.length > 0);
  // Rótulos do último ponto sem se sobrepor: em ordem de altura, ao menos 14 px um do outro.
  const rotulos = linhas
    .map((l) => ({ nome: l.nome, u: ultimo(l.pontos)!, y: y(ultimo(l.pontos)!.valor) + 4 }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < rotulos.length; i++) {
    rotulos[i].y = Math.max(rotulos[i].y, rotulos[i - 1].y + 14);
  }
  const resumo = linhas
    .map((l) => {
      const u = ultimo(l.pontos);
      return u ? `${l.nome}: ${nota(u.valor)} em ${u.ano}` : "";
    })
    .filter(Boolean)
    .join("; ");

  return (
    <figure className="flex flex-col gap-2">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-hidden>
        {linhas.map((l) => (
          <li key={l.nome} className="flex items-center gap-1.5">
            <svg width="22" height="8" aria-hidden>
              <line x1="0" y1="4" x2="22" y2="4" stroke={l.cor} strokeWidth={l.largura} strokeDasharray={l.traco} />
            </svg>
            {l.nome}
          </li>
        ))}
      </ul>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`IDEB de ${anos[0]} a ${anos[anos.length - 1]}, escala de 0 a 10. ${resumo}.`}
        className="h-auto w-full max-w-2xl"
      >
        {faixas
          .filter((f) => f.fim >= anos[0] && f.inicio <= anos[anos.length - 1])
          .map((f, i) => {
            const a = x(Math.max(f.inicio - 0.5, anos[0]));
            const b = x(Math.min(f.fim + 0.5, anos[anos.length - 1]));
            return (
              <g key={`${f.inicio}-${f.rotulo}`}>
                <rect x={a} y={T} width={Math.max(0, b - a)} height={H - T - B} fill={i % 2 ? "transparent" : "var(--muted)"} />
                <text x={a + 4} y={T + (i % 2 ? 24 : 12)} fontSize="10" fill="var(--muted-foreground)">
                  {/* ~5,5 px por letra a 10 px: o nome inteiro só quando cabe na faixa */}
                  {f.rotulo.length * 5.5 + 8 <= Math.max(b - a, 70) ? f.rotulo : f.rotulo.split(" ").at(-1)}
                  <title>{`${f.rotulo}: ${f.inicio} a ${f.fim}`}</title>
                </text>
              </g>
            );
          })}
        {[0, 2, 4, 6, 8, 10].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--border)" strokeWidth={1} />
            <text x={L - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--muted-foreground)">
              {v}
            </text>
          </g>
        ))}
        {anos.map((a, i) =>
          i % 2 === 0 || i === anos.length - 1 ? (
            <text key={a} x={x(a)} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--muted-foreground)">
              {a}
            </text>
          ) : null,
        )}
        {linhas.map((l) => {
          const u = ultimo(l.pontos)!;
          const rotulo = rotulos.find((r) => r.nome === l.nome)!;
          return (
            <g key={l.nome}>
              <polyline
                points={l.pontos.map((p) => `${x(p.ano)},${y(p.valor)}`).join(" ")}
                fill="none"
                stroke={l.cor}
                strokeWidth={l.largura}
                strokeDasharray={l.traco}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {l.pontos.map((p) => (
                <circle
                  key={p.ano}
                  cx={x(p.ano)}
                  cy={y(p.valor)}
                  r={l.marcador ? 4 : 8}
                  fill={l.marcador ? l.cor : "transparent"}
                  stroke={l.marcador ? "var(--card)" : "none"}
                  strokeWidth={2}
                >
                  <title>{`${l.nome}, ${p.ano}: ${nota(p.valor)}`}</title>
                </circle>
              ))}
              <text x={x(u.ano) + 10} y={rotulo.y} fontSize="12" fill="var(--foreground)">
                {nota(u.valor)} <tspan fill="var(--muted-foreground)">{l.nome === cidade ? "" : l.nome}</tspan>
              </text>
            </g>
          );
        })}
      </svg>
      <details className="text-sm">
        <summary className="cursor-pointer underline underline-offset-4">Ver os números ano a ano</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left tabular-nums">
            <thead>
              <tr className="border-b border-border">
                <th className="py-1 pr-3 font-medium">Ano</th>
                {linhas.map((l) => (
                  <th key={l.nome} className="py-1 pr-3 font-medium">
                    {l.nome}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {anos.map((a) => (
                <tr key={a} className="border-b border-border">
                  <td className="py-1 pr-3">{a}</td>
                  {linhas.map((l) => {
                    const p = l.pontos.find((q) => q.ano === a);
                    return (
                      <td key={l.nome} className="py-1 pr-3">
                        {p ? nota(p.valor) : "–"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** Resumo da aba Educação do Raio-X: o número mais recente de cada etapa e a série da primeira. */
export function IdebResumo({
  dados,
  cidade,
  uf,
  faixas = [],
}: {
  dados: IdebMunicipio;
  cidade: string;
  uf: string;
  faixas?: FaixaMandato[];
}) {
  const principal = dados.etapas[0];
  const redePrincipal = principal ? redeComparada(principal.redes) : null;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {dados.etapas.map((e) => {
          const r = redeComparada(e.redes);
          const u = r && ultimo(r.serie);
          if (!r || !u) return null;
          const ufU = r.uf.find((p) => p.ano === u.ano);
          const brU = r.brasil.find((p) => p.ano === u.ano);
          return (
            <div key={e.etapa} className="border-t-2 border-foreground pt-2">
              <dt className="text-sm text-muted-foreground">
                IDEB {u.ano}, {e.rotulo.toLowerCase()}
              </dt>
              <dd className="numero text-2xl">{nota(u.valor)}</dd>
              <dd className="text-sm text-muted-foreground">
                {[ufU && `${uf}: ${nota(ufU.valor)}`, brU && `Brasil: ${nota(brU.valor)}`].filter(Boolean).join(" · ")}
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="text-sm text-muted-foreground">
        IDEB das {REDE.publica}, de 0 a 10: junta a aprovação e a nota da prova do Saeb. Comparado com o estado e o
        Brasil na mesma rede.
      </p>
      {principal && redePrincipal && (
        <div className="flex flex-col gap-1">
          <h3 className="text-base font-semibold">{principal.rotulo}, desde {redePrincipal.serie[0]?.ano}</h3>
          <SerieIdeb rede={redePrincipal} cidade={cidade} uf={uf} faixas={faixas} />
          {faixas.length > 0 && (
            <p className="text-xs text-muted-foreground">
              No fundo, o prefeito eleito de cada período (TSE):{" "}
              {faixas.map((f) => `${f.rotulo} (${f.inicio} a ${f.fim})`).join(", ")}. As faixas só situam no tempo: a nota
              depende de muitos fatores, e as escolas estaduais são do governo do estado.
            </p>
          )}
        </div>
      )}
      <p className="text-sm">
        <a href="#ver-ideb" className="underline underline-offset-4">
          IDEB por etapa e rede de ensino
        </a>
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}

/** Seção completa ("Tudo sobre"): cada etapa com cada rede que a cidade tem. */
export function IdebSecao({ dados, cidade, uf }: { dados: IdebMunicipio; cidade: string; uf: string }) {
  if (dados.etapas.length === 0) return null;
  return (
    <section aria-labelledby="ideb-titulo" className="flex flex-col gap-4">
      <div>
        <h2 id="ideb-titulo" className="text-2xl">
          IDEB das escolas de {cidade}
        </h2>
        <p className="text-sm text-muted-foreground">
          Índice de Desenvolvimento da Educação Básica, de 0 a 10, a cada dois anos. Cada rede ao lado do estado e do
          Brasil na mesma rede, quando o INEP publica.
        </p>
      </div>
      {dados.etapas.map((e) => (
        <div key={e.etapa} className="flex flex-col gap-3">
          <h3 className="text-lg font-semibold">{e.rotulo}</h3>
          {e.redes.map((r) => (
            <div key={r.rede} className="flex flex-col gap-1">
              <h4 className="text-sm font-medium">{REDE[r.rede] ?? r.rede}</h4>
              <SerieIdeb rede={r} cidade={cidade} uf={uf} />
            </div>
          ))}
        </div>
      ))}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
