import type { ReactNode } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import type { EventoItem, LinhaDoTempo, ProcessoSituacao } from "@/lib/api";
import { formatarData } from "@/lib/formato";

/** Grupos da linha do tempo, na ordem em que aparecem. Tipos novos caem em "Outros
 * registros" até ganharem um grupo aqui. */
const GRUPOS: { titulo: string; detalhe: string; tipos: string[] }[] = [
  { titulo: "Eleições", detalhe: "Justiça Eleitoral (TSE)", tipos: ["eleito"] },
  { titulo: "Cargos em partidos", detalhe: "órgãos partidários registrados no TSE", tipos: ["cargo_partidario"] },
  {
    titulo: "Registro e diploma de candidatura",
    detalhe: "julgamentos e cassações registrados pelo TSE",
    tipos: ["cassacao", "julgamento_candidatura"],
  },
  { titulo: "Processos na Justiça", detalhe: "consultados nos tribunais", tipos: ["processo"] },
  { titulo: "Casos", detalhe: "papel segundo documentos oficiais", tipos: ["caso"] },
  { titulo: "Conselho de Ética", detalhe: "representações na Câmara e no Senado", tipos: ["conselho_etica"] },
  {
    titulo: "Tribunal de Contas da União",
    detalhe: "contas julgadas irregulares e inabilitação para cargo público",
    tipos: ["tcu_contas_irregulares", "tcu_inabilitacao"],
  },
  {
    titulo: "Sanções",
    detalhe: "cadastros da Controladoria-Geral da União (CEIS, CNEP, CEAF)",
    tipos: ["sancao"],
  },
];

const VISIVEIS_POR_GRUPO = 5;
const LIMITE_TEXTO = 280;

/** Linha do tempo da pessoa: fatos de órgãos oficiais, agrupados por tipo, cada um com a
 * situação informada pela fonte, o link e a data em que o dado foi conferido. */
export function LinhaDoTempoSecao({ dados }: { dados: LinhaDoTempo }) {
  const conhecidos = new Set(GRUPOS.flatMap((g) => g.tipos));
  const grupos = [
    ...GRUPOS.map((g) => ({ ...g, itens: dados.itens.filter((i) => g.tipos.includes(i.tipo)) })),
    {
      titulo: "Outros registros",
      detalhe: "órgãos oficiais",
      tipos: [],
      itens: dados.itens.filter((i) => !conhecidos.has(i.tipo)),
    },
  ].filter((g) => g.itens.length > 0);
  if (grupos.length === 0) return null;

  const soEleicoes = dados.itens.every((i) => i.tipo === "eleito");
  const conferido = dados.itens
    .map((i) => i.conferido_em)
    .filter((d): d is string => Boolean(d))
    .sort()
    .at(-1);

  return (
    <section aria-labelledby="linha-do-tempo-titulo" className="revelar flex flex-col gap-6">
      <div>
        <h2 id="linha-do-tempo-titulo" className="text-2xl">
          Linha do tempo
        </h2>
        <p className="text-xs text-muted-foreground">
          {soEleicoes
            ? "Eleições vencidas, segundo a Justiça Eleitoral (TSE)"
            : "Registros de órgãos oficiais sobre esta pessoa, com a situação que cada fonte informa"}
        </p>
      </div>

      {grupos.map((g) => (
        <div key={g.titulo} className="flex flex-col gap-2">
          <h3 className="font-medium">
            {g.titulo} <span className="text-sm font-normal text-muted-foreground tabular-nums">({g.itens.length})</span>
            <span className="block text-xs font-normal text-muted-foreground">{g.detalhe}</span>
          </h3>
          <ul className="lista-fios flex flex-col">
            {g.itens.slice(0, VISIVEIS_POR_GRUPO).map((item, i) => (
              <Item key={i} item={item} />
            ))}
          </ul>
          {g.itens.length > VISIVEIS_POR_GRUPO && (
            <details className="painel">
              <summary className="cursor-pointer text-sm font-medium">
                Ver {g.itens.length - VISIVEIS_POR_GRUPO === 1 ? "o outro registro" : `os outros ${g.itens.length - VISIVEIS_POR_GRUPO}`}
              </summary>
              <ul className="mt-2 lista-fios flex flex-col">
                {g.itens.slice(VISIVEIS_POR_GRUPO).map((item, i) => (
                  <Item key={i} item={item} />
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}

      {!soEleicoes && (
        <p className="text-xs text-muted-foreground">
          Uma representação, um julgamento ou um processo registrado não é, por si, uma condenação:
          a situação de cada um é a informada pela fonte, que pode ter mudado depois da data de
          conferência. Só entram registros ligados a esta pessoa por dado seguro (CPF, título de
          eleitor ou conferência manual). Processos sob sigilo não são detalhados, e o STF e o STJ
          não permitem consulta automática.
        </p>
      )}

      <FonteRodape fonte="TSE, CGU, TCU, Câmara, Senado e DataJud (CNJ)" atualizadoEm={conferido} />
    </section>
  );
}

function Item({ item }: { item: EventoItem }) {
  const eleicao = item.tipo === "eleito";
  const situacao = eleicao ? situacaoEleicao(item.situacao) : item.situacao;
  return (
    <li className="flex flex-col gap-1.5 py-3">
      <p className="text-xs text-muted-foreground tabular-nums">
        {item.data ? formatarData(item.data) : "Data não informada pela fonte"}
      </p>
      <Descricao texto={item.descricao} />
      {!eleicao && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
          {item.orgao && <Campo rotulo="Órgão">{item.orgao}</Campo>}
          {item.numero_processo && (
            <Campo rotulo="Número">
              <span className="break-all tabular-nums">{item.numero_processo}</span>
            </Campo>
          )}
          {situacao && <Campo rotulo="Situação">{situacao}</Campo>}
          {item.processo && <Campo rotulo="No tribunal">{textoProcesso(item.processo)}</Campo>}
        </dl>
      )}
      {eleicao && situacao && <p className="text-sm text-muted-foreground">{situacao}</p>}
      <p className="text-xs text-muted-foreground">
        {item.fonte_url && (
          <a href={item.fonte_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
            Ver na fonte oficial
          </a>
        )}
        {item.fonte_url && item.conferido_em && " · "}
        {item.conferido_em && `conferido em ${formatarData(item.conferido_em)}`}
      </p>
    </li>
  );
}

function Campo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{rotulo}</dt>
      <dd className="min-w-0">{children}</dd>
    </>
  );
}

/** Textos oficiais longos (fundamentos de sanções citam a lei inteira): o começo à vista e
 * o resto a um toque. */
function Descricao({ texto }: { texto: string }) {
  if (texto.length <= LIMITE_TEXTO) return <p className="text-sm">{texto}</p>;
  const corte = texto.lastIndexOf(" ", LIMITE_TEXTO);
  return (
    <details className="text-sm">
      <summary className="cursor-pointer list-none">
        {texto.slice(0, corte > 0 ? corte : LIMITE_TEXTO)}…{" "}
        <span className="underline underline-offset-2">ler o texto completo</span>
      </summary>
      <p className="mt-1">{texto}</p>
    </details>
  );
}

function textoProcesso(p: ProcessoSituacao): string {
  const onde = p.tribunal ? ` no ${p.tribunal}` : "";
  const consulta = `consulta ao DataJud (CNJ) em ${formatarData(p.consultado_em)}`;
  if (p.sigiloso) return `Processo sob sigilo${onde}; os detalhes não são divulgados (${consulta}).`;
  const partes = [p.classe ? `${p.classe}${onde}` : onde.trim()];
  if (p.ultimo_andamento) {
    partes.push(
      `último andamento${p.data_ultimo_andamento ? ` em ${formatarData(p.data_ultimo_andamento)}` : ""}: ${p.ultimo_andamento}`,
    );
  }
  return `${partes.filter(Boolean).join("; ")} (${consulta}).`;
}

/** "ELEITO POR QP" → "Eleito pelo quociente partidário". */
function situacaoEleicao(situacao: string | null): string | null {
  if (situacao === "ELEITO POR QP") return "Pelo quociente partidário (votos do partido ou federação)";
  if (situacao === "ELEITO POR MÉDIA") return "Pela distribuição das sobras de vagas (média)";
  return null;
}
