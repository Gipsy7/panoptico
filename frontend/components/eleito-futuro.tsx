import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { EleitoFuturo, EleitosFuturos } from "@/lib/api";
import { formatarData, formatarPosse } from "@/lib/formato";

const CARGO_COM_GENERO: Record<string, string> = {
  "Deputado federal": "deputado(a) federal",
  "Deputado estadual": "deputado(a) estadual",
  "Deputado distrital": "deputado(a) distrital",
  Senador: "senador(a)",
  Governador: "governador(a)",
  Presidente: "presidente",
};

function cargoTexto(cargo: string): string {
  return CARGO_COM_GENERO[cargo] ?? cargo.toLowerCase();
}

/** A frase do selo: o que o TSE registra e quando é a posse, sem juízo. */
export function fraseEleitoFuturo(e: EleitoFuturo): string {
  if (e.segundo_turno) {
    const quando = e.data_segundo_turno ? ` em ${formatarData(e.data_segundo_turno)}` : "";
    return `Disputa o 2º turno${quando} para ${cargoTexto(e.cargo)}. Se for eleito(a), a posse é em ${formatarPosse(e.posse)}.`;
  }
  return `Eleito(a) ${cargoTexto(e.cargo)} em ${e.ano_eleicao} — posse em ${formatarPosse(e.posse)}.`;
}

/** Selo no perfil: separado do cargo de hoje, que continua sendo o que o perfil mostra. */
export function SeloEleitoFuturo({ eleito, atualizadoEm }: { eleito: EleitoFuturo; atualizadoEm: string | null }) {
  return (
    <aside aria-label={`Eleição de ${eleito.ano_eleicao}`} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <p className="font-medium">{fraseEleitoFuturo(eleito)}</p>
      <p className="mt-1 text-sm text-muted-foreground">
        {[eleito.partido, eleito.unidade].filter(Boolean).join(" · ")}
        {eleito.situacao && !eleito.segundo_turno && <> · {eleito.situacao}</>}
        {eleito.ja_no_cargo && <> · Segue no mandato de hoje até a posse.</>}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Fonte:{" "}
        <a
          href={`https://dadosabertos.tse.jus.br/dataset/candidatos-${eleito.ano_eleicao}`}
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2"
        >
          Tribunal Superior Eleitoral
        </a>
        {atualizadoEm && <> · atualizado em {formatarData(atualizadoEm)}</>}
      </p>
    </aside>
  );
}

function Lista({ itens }: { itens: EleitoFuturo[] }) {
  return (
    <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
      {itens.map((e) => (
        <li key={e.id} className="border-b border-border">
          <Link
            href={e.parlamentar_id ? `/parlamentar/${e.parlamentar_id}` : `/eleito/${e.id}`}
            className="flex flex-col py-3 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
          >
            <span className="truncate text-base font-semibold">{e.nome_urna}</span>
            <span className="text-sm text-muted-foreground">
              {[e.partido, e.uf].filter(Boolean).join(" · ")}
              {e.vice && <> · vice: {e.vice}</>}
            </span>
            <span className="text-xs text-muted-foreground">
              {e.segundo_turno
                ? `Disputa o 2º turno${e.data_segundo_turno ? ` em ${formatarData(e.data_segundo_turno)}` : ""}`
                : e.situacao}
              {e.ja_no_cargo && " · segue no mandato de hoje até a posse"}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Grupo({ titulo, itens, recolher = false }: { titulo: string; itens: EleitoFuturo[]; recolher?: boolean }) {
  if (itens.length === 0) return null;
  if (recolher) {
    return (
      <details className="painel">
        <summary className="cursor-pointer font-medium">
          {titulo} ({itens.length})
        </summary>
        <div className="mt-3">
          <Lista itens={itens} />
        </div>
      </details>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-lg font-medium">
        {titulo} <span className="text-muted-foreground">({itens.length})</span>
      </h3>
      <Lista itens={itens} />
    </div>
  );
}

/** Eleitos da eleição mais recente que ainda não tomaram posse, à parte de quem está no cargo. */
export function EleitosFuturosSecao({ dados, estado }: { dados: EleitosFuturos; estado: string }) {
  const todos = [
    ...dados.presidente,
    ...dados.governador,
    ...dados.senadores,
    ...dados.deputados_federais,
    ...dados.deputados_estaduais,
  ];
  if (todos.length === 0 || !dados.ano_eleicao) return null;
  const segundoTurno = todos.find((e) => e.segundo_turno);
  const posseFederal = todos.find((e) => e.cargo !== "Presidente" && e.cargo !== "Governador");
  const posseExecutivo = todos.find((e) => e.cargo === "Presidente" || e.cargo === "Governador");
  const posses = [
    posseExecutivo && `presidente e governadores em ${formatarPosse(posseExecutivo.posse)}`,
    posseFederal && `senadores e deputados em ${formatarPosse(posseFederal.posse)}`,
  ].filter(Boolean);
  return (
    <section aria-labelledby="eleitos-futuros-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="eleitos-futuros-titulo" className="text-2xl">
          Eleitos em {dados.ano_eleicao} (posse em {dados.ano_eleicao + 1})
        </h2>
        <p className="text-sm text-muted-foreground">
          Resultado da eleição de {dados.ano_eleicao} para {estado}, segundo o TSE. Quem aparece aqui ainda não tomou
          posse: quem está no cargo hoje é quem aparece nas seções acima. Posse: {posses.join("; ")}.
        </p>
        {segundoTurno && (
          <p className="mt-1 text-sm text-muted-foreground">
            Onde o cargo está marcado como 2º turno, a votação é
            {segundoTurno.data_segundo_turno ? ` em ${formatarData(segundoTurno.data_segundo_turno)}` : " em outra data"}
            {" "}e o resultado ainda não saiu.
          </p>
        )}
      </div>
      <Grupo titulo="Presidente da República" itens={dados.presidente} />
      <Grupo titulo={`Governador de ${estado}`} itens={dados.governador} />
      <Grupo titulo="Senadores" itens={dados.senadores} />
      <Grupo titulo="Deputados federais" itens={dados.deputados_federais} recolher />
      <Grupo titulo="Deputados estaduais" itens={dados.deputados_estaduais} recolher />
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
