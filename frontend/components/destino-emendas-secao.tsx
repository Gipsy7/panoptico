import { TabelaRolavel } from "@/components/ui/tabela-rolavel";
import { FonteRodape } from "@/components/fonte-rodape";
import type { DestinoEmendaItem, DestinoEmendas } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

const TIPO: Record<string, string> = {
  convenio: "Convênio",
  especial: "Transferência especial",
};

export function DestinoEmendasSecao({ dados }: { dados: DestinoEmendas }) {
  const convenios = dados.por_situacao.filter((s) => s.tipo === "convenio");
  const especiais = dados.por_situacao.filter((s) => s.tipo === "especial");

  return (
    <section aria-labelledby="destino-emendas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="destino-emendas-titulo" className="text-2xl">
          O que aconteceu com o dinheiro das emendas
        </h2>
        <p className="text-xs text-muted-foreground">
          Convênios e transferências especiais ligados às emendas individuais deste parlamentar, de{" "}
          {dados.desde} em diante
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Numero rotulo="Convênios e transferências" valor={String(dados.quantidade)} />
        <Numero rotulo="Valor previsto" valor={formatarReais(dados.valor_total, true)} />
        <Numero rotulo="Já liberado ou empenhado" valor={formatarReais(dados.valor_repassado, true)} />
      </dl>

      {convenios.length > 0 && (
        <TabelaSituacoes
          titulo="Convênios, por situação"
          linhas={convenios.map((s) => ({
            rotulo: s.situacao ?? "Sem situação informada",
            quantidade: s.quantidade,
            valor: s.valor_total,
          }))}
        />
      )}
      {especiais.length > 0 && (
        <TabelaSituacoes
          titulo="Transferências especiais, por situação do plano de ação"
          linhas={especiais.map((s) => ({
            rotulo: s.situacao ?? "Sem situação informada",
            quantidade: s.quantidade,
            valor: s.valor_total,
          }))}
        />
      )}
      {dados.relatorios_de_gestao.some((r) => r.situacao) && (
        <TabelaSituacoes
          titulo="Transferências especiais, por relatório de gestão do beneficiário"
          linhas={dados.relatorios_de_gestao.map((r) => ({
            rotulo: r.situacao ?? "Sem relatório de gestão ainda",
            quantidade: r.quantidade,
          }))}
        />
      )}

      <p className="text-sm text-muted-foreground">
        As situações são as que constam nos sistemas do governo federal (por exemplo, “em
        execução” ou “prestação de contas em análise”) e descrevem o andamento administrativo do
        convênio. Um convênio pode reunir recursos de mais de uma emenda, e o valor mostrado é o do
        convênio inteiro.
      </p>

      <details className="painel">
        <summary className="cursor-pointer font-medium">
          Ver os {dados.itens.length}
          {dados.quantidade > dados.itens.length ? " maiores" : ""} convênios e transferências
        </summary>
        <ul className="mt-3 flex flex-col gap-4">
          {dados.itens.map((i) => (
            <Item key={`${i.tipo}-${i.identificador}-${i.emenda_codigo}`} item={i} />
          ))}
        </ul>
      </details>

      <FonteRodape
        fonte={dados.fonte_nome}
        url={dados.fonte_url}
        atualizadoEm={dados.atualizado_em}
      />
    </section>
  );
}

function Numero({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <dd className="text-xl font-semibold tabular-nums">{valor}</dd>
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
    </div>
  );
}

function TabelaSituacoes({
  titulo,
  linhas,
}: {
  titulo: string;
  linhas: { rotulo: string; quantidade: number; valor?: number }[];
}) {
  return (
    <TabelaRolavel larguraMinima="28rem" rotulo={`${titulo}, tabela com rolagem lateral`}>
    <table className="w-full text-left text-sm">
      <caption className="pb-1 text-left font-medium">{titulo}</caption>
      <thead className="sr-only">
        <tr>
          <th scope="col">Situação</th>
          <th scope="col">Quantidade</th>
          {linhas.some((l) => l.valor !== undefined) && <th scope="col">Valor</th>}
        </tr>
      </thead>
      <tbody>
        {linhas.map((l) => (
          <tr key={l.rotulo} className="border-t">
            <th scope="row" className="py-2 pr-3 font-normal">
              {l.rotulo}
            </th>
            <td className="py-2 pr-3 text-right tabular-nums">{l.quantidade}</td>
            {l.valor !== undefined && (
              <td className="py-2 text-right tabular-nums">{formatarReais(l.valor, true)}</td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
    </TabelaRolavel>
  );
}

function Item({ item }: { item: DestinoEmendaItem }) {
  const vigencia =
    item.inicio_vigencia && item.fim_vigencia
      ? `${formatarData(item.inicio_vigencia)} a ${formatarData(item.fim_vigencia)}`
      : null;
  return (
    <li className="flex flex-col gap-1 border-t pt-3 text-sm">
      <p className="font-medium">
        {item.beneficiario ?? (item.nome_omitido ? "MEI (nome omitido por conter CPF)" : "Beneficiário não informado")}
        {item.uf && <span className="font-normal text-muted-foreground"> · {item.uf}</span>}
        {!item.beneficiario && item.nome_omitido && item.beneficiario_cnpj && (
          <span className="block text-sm font-normal text-muted-foreground tabular-nums">
            CNPJ {item.beneficiario_cnpj}
          </span>
        )}
      </p>
      {item.objeto && <p>{item.objeto}</p>}
      <p className="text-muted-foreground">
        {TIPO[item.tipo] ?? item.tipo} {item.identificador} · emenda {item.emenda_codigo}
        {item.orgao_concedente && <> · {item.orgao_concedente}</>}
      </p>
      <p>
        Situação: <strong className="font-medium">{item.situacao ?? "não informada"}</strong>
        {item.relatorio_gestao && <> · relatório de gestão: {item.relatorio_gestao.toLowerCase()}</>}
      </p>
      <p className="tabular-nums">
        {item.valor_total !== null && <>Valor previsto {formatarReais(item.valor_total)}</>}
        {item.valor_repassado !== null && (
          <>
            {" "}
            · {item.tipo === "especial" ? "empenhado" : "liberado"}{" "}
            {formatarReais(item.valor_repassado)}
          </>
        )}
        {vigencia && <> · vigência {vigencia}</>}
      </p>
      <LinkExterno
        href={item.fonte_url}
        className="w-fit underline underline-offset-2"
      >
        {item.tipo === "especial"
          ? "Ver o registro oficial (TransfereGov)"
          : "Consultar o convênio no Portal da Transparência"}
      </LinkExterno>
    </li>
  );
}
