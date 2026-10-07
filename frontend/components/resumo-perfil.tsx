import type { Gastos, Presenca, Projetos } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

type Item = { rotulo: string; valor: string; detalhe: string; ancora: string };

export function ResumoPerfil({
  gastos,
  presenca,
  projetos,
  subsidio,
}: {
  gastos?: Gastos;
  presenca?: Presenca;
  projetos?: Projetos;
  subsidio: number;
}) {
  const itens: Item[] = [];
  if (gastos) {
    itens.push({
      rotulo: `Gastos do gabinete em ${gastos.ano}`,
      valor: formatarReais(gastos.total, true),
      detalhe: `Média: ${formatarReais(gastos.media_casa, true)}`,
      ancora: "#gastos-titulo",
    });
  }
  if (presenca && presenca.percentual !== null) {
    itens.push({
      rotulo: `Votou em ${presenca.ano}`,
      valor: `${PCT.format(presenca.percentual)}%`,
      detalhe:
        presenca.media_casa_percentual === null
          ? `${presenca.votou} de ${presenca.total_votacoes}`
          : `Média: ${PCT.format(presenca.media_casa_percentual)}%`,
      ancora: "#presenca-titulo",
    });
  }
  if (projetos) {
    itens.push({
      rotulo: "Projetos como autor principal",
      valor: String(projetos.primeiro_autor),
      detalhe: `Média: ${projetos.media_casa_primeiro_autor.toLocaleString("pt-BR")}`,
      ancora: "#projetos-titulo",
    });
  }
  itens.push({
    rotulo: "Salário bruto mensal",
    valor: formatarReais(subsidio, true),
    detalhe: "Igual para todos",
    ancora: "#remuneracao-titulo",
  });

  return (
    <nav aria-label="Resumo do perfil">
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {itens.map((i) => (
          <li key={i.ancora}>
            <a
              href={i.ancora}
              className="flex h-full flex-col gap-0.5 rounded-xl bg-card p-3 border border-border/80 transition-colors hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              <span className="text-xs text-muted-foreground">{i.rotulo}</span>
              <span className="text-xl font-bold tabular-nums">{i.valor}</span>
              <span className="text-xs text-muted-foreground">{i.detalhe}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
