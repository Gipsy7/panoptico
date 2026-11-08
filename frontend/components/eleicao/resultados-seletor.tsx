import { TabelaResultado } from "@/components/eleicao/tabela-resultado";
import { getEleicoesDisponiveis, getResultadoEleicao } from "@/lib/api";
import { nomeCargo } from "@/lib/eleicao";

const MUNICIPAIS = new Set(["PREFEITO", "VEREADOR"]);
const MAJORITARIOS = new Set(["PRESIDENTE", "GOVERNADOR", "SENADOR"]);
const ORDEM = [
  "PRESIDENTE",
  "GOVERNADOR",
  "SENADOR",
  "DEPUTADO FEDERAL",
  "DEPUTADO ESTADUAL",
  "DEPUTADO DISTRITAL",
  "PREFEITO",
  "VEREADOR",
];

export type EscolhaResultado = {
  ano?: string;
  cargo?: string;
  turno?: string;
  onde?: string;
};

/**
 * Resultado de qualquer eleição carregada (2016 a 2026) para o lugar do CEP, com seletores de
 * ano, cargo, turno e "onde" (só a cidade ou a disputa inteira). Formulário GET: funciona sem
 * JavaScript. É a /segundo-turno generalizada (Frente 5), no mesmo endereço.
 */
export async function ResultadosSeletor({
  acao,
  escondidos,
  uf,
  ibge,
  cidade,
  escolha,
}: {
  acao: string;
  escondidos: Record<string, string>;
  uf: string;
  ibge: string | null;
  cidade: string | null;
  escolha: EscolhaResultado;
}) {
  const disp = await getEleicoesDisponiveis();
  if (!disp.ok || disp.dados.length === 0) return null;
  const lista = disp.dados.filter(
    (d) =>
      ORDEM.includes(d.cargo) &&
      (ibge || !MUNICIPAIS.has(d.cargo)) &&
      !(uf !== "DF" && d.cargo === "DEPUTADO DISTRITAL") &&
      !(uf === "DF" && d.cargo === "DEPUTADO ESTADUAL"),
  );
  const anos = [...new Set(lista.map((d) => d.ano))].sort((a, b) => b - a);
  const ano =
    Number(escolha.ano) && anos.includes(Number(escolha.ano))
      ? Number(escolha.ano)
      : anos[0];
  const cargosDoAno = lista
    .filter((d) => d.ano === ano)
    .sort((a, b) => ORDEM.indexOf(a.cargo) - ORDEM.indexOf(b.cargo));
  const cargo =
    cargosDoAno.find((d) => d.cargo === escolha.cargo?.toUpperCase())?.cargo ??
    cargosDoAno[0]?.cargo;
  if (!cargo) return null;
  const turnos = cargosDoAno.find((d) => d.cargo === cargo)?.turnos ?? [1];
  const turno =
    Number(escolha.turno) && turnos.includes(Number(escolha.turno))
      ? Number(escolha.turno)
      : Math.max(...turnos);
  const soCidade =
    MAJORITARIOS.has(cargo) && ibge !== null && escolha.onde === "cidade";
  const r = await getResultadoEleicao({
    ano,
    cargo,
    turno,
    uf,
    municipio:
      MUNICIPAIS.has(cargo) || soCidade ? (ibge ?? undefined) : undefined,
    limite: 50,
  });

  return (
    <section
      aria-labelledby="resultados-titulo"
      className="flex flex-col gap-4"
    >
      <div>
        <h2 id="resultados-titulo" className="text-2xl">
          Resultado das eleições
        </h2>
        <p className="text-sm text-muted-foreground">
          Escolha a eleição. Os votos de cada candidato, de 2016 a 2026, segundo
          o TSE.
        </p>
      </div>
      <form action={acao} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Object.entries(escondidos).map(([k, v]) => (
          <input key={k} type="hidden" name={k} value={v} />
        ))}
        <label className="flex flex-col gap-1 text-sm">
          Ano
          <select name="ano" defaultValue={ano} className="seletor h-11">
            {anos.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Cargo
          <select name="cargo" defaultValue={cargo} className="seletor h-11">
            {cargosDoAno.map((d) => (
              <option key={d.cargo} value={d.cargo}>
                {nomeCargo(d.cargo)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Turno
          <select name="turno" defaultValue={turno} className="seletor h-11">
            {turnos.map((t) => (
              <option key={t} value={t}>
                {t}º turno
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Onde
          <select
            name="onde"
            defaultValue={soCidade ? "cidade" : "disputa"}
            className="seletor h-11"
            disabled={!ibge}
          >
            <option value="disputa">
              {cargo === "PRESIDENTE"
                ? "No Brasil"
                : MUNICIPAIS.has(cargo)
                  ? (cidade ?? "Na cidade")
                  : "No estado"}
            </option>
            {ibge && MAJORITARIOS.has(cargo) && (
              <option value="cidade">Só em {cidade}</option>
            )}
          </select>
        </label>
        <button type="submit" className="botao-linha col-span-2 sm:col-span-4">
          Ver o resultado
        </button>
      </form>
      {r.ok ? (
        <TabelaResultado r={r.dados} nivelTitulo={3} />
      ) : (
        <p className="text-sm text-muted-foreground">
          O resultado de {nomeCargo(cargo).toLowerCase()} em {ano} ainda não
          está carregado para este lugar.
        </p>
      )}
    </section>
  );
}
