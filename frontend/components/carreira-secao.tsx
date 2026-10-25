import { FonteRodape } from "@/components/fonte-rodape";
import { getCarreira, type CandidaturaDaCarreira } from "@/lib/api";
import { formatarReais } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

function resultado(c: CandidaturaDaCarreira): string {
  if (c.eleito === true) return "Eleito(a)";
  if (c.eleito === false) return "Não eleito(a)";
  return c.situacao ?? "Resultado não informado";
}

/** Candidaturas da pessoa, eleição a eleição, segundo o TSE. Some quando não há nenhuma. */
export async function CarreiraSecao({ pessoaId }: { pessoaId: number }) {
  const r = await getCarreira(pessoaId);
  if (!r.ok || r.dados.itens.length === 0) return null;
  const d = r.dados;

  return (
    <section aria-labelledby="carreira-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="carreira-titulo" className="text-2xl">
          Eleições que disputou
        </h2>
        <p className="text-sm text-muted-foreground">Candidaturas registradas na Justiça Eleitoral (TSE)</p>
      </div>

      <ul className="lista-fios flex flex-col">
        {d.itens.map((c, i) => {
          const lugar = [c.unidade ?? c.uf, c.municipio && c.municipio !== c.unidade ? c.municipio : null]
            .filter(Boolean)
            .join(" · ");
          return (
            <li key={i} className="flex flex-col gap-0.5 py-3 text-sm">
              <span className="font-medium">
                <span className="tabular-nums">{c.ano}</span> · {c.cargo}
                {lugar ? ` · ${lugar}` : ""}
              </span>
              <span className="text-muted-foreground">
                {[c.partido, c.numero ? `número ${c.numero}` : null].filter(Boolean).join(" · ")}
              </span>
              <span className="tabular-nums">
                {resultado(c)}
                {c.votos !== null ? ` · ${c.votos.toLocaleString("pt-BR")} votos` : ""}
              </span>
              <span className="tabular-nums">
                {c.bens_total !== null
                  ? `Bens declarados: ${formatarReais(c.bens_total, true)}`
                  : "Bens não carregados para este ano"}
              </span>
              {c.fonte_url && (
                <LinkExterno
                  href={c.fonte_url}
                  className="self-start text-muted-foreground underline underline-offset-2"
                >
                  Ver na fonte oficial
                </LinkExterno>
              )}
              {c.ligacao && <span className="text-xs text-muted-foreground">{c.ligacao}</span>}
            </li>
          );
        })}
      </ul>

      <p className="text-sm text-muted-foreground">{d.recorte.texto}</p>
      <p className="text-sm text-muted-foreground">
        Bens como o candidato declarou, sem correção pela inflação, e só para os anos com dado carregado.
      </p>
      <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />
    </section>
  );
}
