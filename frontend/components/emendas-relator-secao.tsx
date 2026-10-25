import { TabelaRolavel } from "@/components/ui/tabela-rolavel";
import { FonteRodape } from "@/components/fonte-rodape";
import type { EmendasRelator } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

export function EmendasRelatorSecao({ dados }: { dados: EmendasRelator }) {
  return (
    <section aria-labelledby="emendas-relator-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="emendas-relator-titulo" className="text-2xl">
          Indicações de emendas de relator (RP9)
        </h2>
        <p className="text-xs text-muted-foreground">
          Pedidos de recursos registrados em nome deste parlamentar na planilha oficial do
          Congresso, orçamento de {dados.ano}
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Numero rotulo="Indicações registradas" valor={String(dados.quantidade)} />
        <Numero rotulo="Valor indicado" valor={formatarReais(dados.valor_solicitado, true)} />
        <Numero rotulo="Beneficiários diferentes" valor={String(dados.beneficiarios)} />
      </dl>

      <TabelaRolavel larguraMinima="28rem">
      <table className="w-full text-left text-sm">
        <caption className="pb-1 text-left font-medium">Por órgão que executaria o recurso</caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Órgão</th>
            <th scope="col">Indicações</th>
            <th scope="col">Valor indicado</th>
          </tr>
        </thead>
        <tbody>
          {dados.por_orgao.map((o) => (
            <tr key={o.orgao} className="border-t">
              <th scope="row" className="py-2 pr-3 font-normal">
                {o.orgao}
              </th>
              <td className="py-2 pr-3 text-right tabular-nums">{o.quantidade}</td>
              <td className="py-2 text-right tabular-nums">{formatarReais(o.valor, true)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </TabelaRolavel>

      <p className="text-sm text-muted-foreground">
        Emenda de relator-geral (RP9) foi uma modalidade de emenda ao orçamento federal usada de
        2020 a 2022, conhecida como “orçamento secreto”. No orçamento, o autor aparece como “relator
        geral”, e não como o parlamentar que pediu o dinheiro. A planilha acima é o registro que o
        Congresso publicou depois da decisão do Supremo Tribunal Federal (ADPF 850, 851 e 854), e
        mostra o valor <strong className="font-medium">indicado</strong>, não o que foi empenhado ou
        pago. O Supremo declarou essa modalidade inconstitucional em dezembro de 2022. O registro
        publicado cobre só as indicações feitas em 2022 e pode estar incompleto: pedidos feitos
        por outros meios, ou em 2020 e 2021, não aparecem aqui, e a ausência de indicações não
        significa que o parlamentar não tenha pedido recursos dessa forma. Esta seção apenas
        reproduz o que consta no registro oficial.
      </p>

      <details className="painel">
        <summary className="cursor-pointer font-medium">
          Ver as {dados.itens.length}
          {dados.quantidade > dados.itens.length ? " maiores" : ""} indicações
        </summary>
        <ul className="mt-3 flex flex-col gap-4">
          {dados.itens.map((i) => (
            <li key={i.numero} className="flex flex-col gap-1 border-t pt-3 text-sm">
              <p className="font-medium">
                {i.beneficiario}
                {i.uf && <span className="font-normal text-muted-foreground"> · {i.uf}</span>}
              </p>
              {i.objeto && <p>{i.objeto}</p>}
              <p className="text-muted-foreground">
                {i.orgao ?? "Órgão não informado"} · registro nº {i.numero}
                {i.data_cadastro && <> · cadastrado em {formatarData(i.data_cadastro)}</>}
              </p>
              <p className="tabular-nums">Valor indicado {formatarReais(i.valor_solicitado)}</p>
            </li>
          ))}
        </ul>
      </details>

      <p className="text-sm">
        <LinkExterno
          href={dados.arquivo_url}
          className="underline underline-offset-2"
        >
          Baixar a planilha oficial (xlsx)
        </LinkExterno>
      </p>

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
