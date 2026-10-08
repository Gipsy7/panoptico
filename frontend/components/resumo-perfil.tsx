import type { Gastos, Presenca, Projetos } from "@/lib/api";
import { formatarGastos, formatarReais } from "@/lib/formato";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

export type ItemResumo = { rotulo: string; valor: string; detalhe: string; ancora: string };
type Item = ItemResumo;

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
      valor: formatarGastos(gastos.total, true),
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

  return <ResumoNumeros itens={itens} />;
}

/** Os números-chave do topo do perfil, cada um levando à seção com o detalhe. */
export function ResumoNumeros({ itens }: { itens: ItemResumo[] }) {
  if (itens.length === 0) return null;
  return (
    <nav aria-label="Resumo do perfil">
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {itens.map((i) => (
          <li key={i.ancora}>
            <a
              href={i.ancora}
              className="figura flex h-full flex-col gap-0.5 transition-colors duration-300 hover:border-bronze focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
            >
              <span className="text-xs text-muted-foreground">{i.rotulo}</span>
              <span className="numero text-2xl">{i.valor}</span>
              <span className="text-xs text-muted-foreground">{i.detalhe}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
