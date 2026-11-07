import { FolhaAtos } from "@/components/custo-mandato-folha";
import { FonteRodape } from "@/components/fonte-rodape";
import { LinkExterno } from "@/components/link-externo";
import { TermoOficial } from "@/components/termo-oficial";
import type { Casa, CustoMandato, ItemCustoMandato, ParlamentarDetalhe } from "@/lib/api";
import { escalaDasBarras, listaNomes, periodoDoUso, segmentos } from "@/lib/custo-mandato";
import { CASA_DA, formatarData, formatarReais } from "@/lib/formato";

/** Tons de cada parcela (tokens do tema; o número escrito na legenda é o que vale). */
const TOM: Record<ItemCustoMandato["item"], string> = {
  subsidio: "bg-chart-1",
  verba_gabinete: "bg-chart-2",
  cota: "bg-chart-3",
  auxilio_moradia: "bg-chart-4",
};
const TERMO: Partial<Record<ItemCustoMandato["item"], string>> = {
  subsidio: "subsidio",
  verba_gabinete: "verba-gabinete",
  cota: "cota",
  auxilio_moradia: "auxilio-moradia",
};
const CASA_NOME: Record<Casa, string> = { camara: "Câmara dos Deputados", senado: "Senado Federal" };
const A_CASA: Record<Casa, string> = { camara: "a Câmara", senado: "o Senado" };

export function RemuneracaoSecao({
  remuneracao,
  casa,
  nome,
}: {
  remuneracao: ParlamentarDetalhe["remuneracao"];
  casa: Casa;
  nome: string;
}) {
  const custo = remuneracao.custo;
  if (!custo) return <SoSalario remuneracao={remuneracao} />;
  return <CustoDoMandato custo={custo} casa={casa} nome={nome} />;
}

function CustoDoMandato({ custo, casa, nome }: { custo: CustoMandato; casa: Casa; nome: string }) {
  const escala = escalaDasBarras(custo);
  const periodo = custo.ano && custo.ultimo_mes ? periodoDoUso(custo.ano, custo.ultimo_mes) : null;
  const comValor = custo.itens.filter((i) => i.valor !== null).map((i) => i.nome);
  const foraDoUso = custo.itens.filter((i) => i.usou === null && i.valor !== null).map((i) => i.nome);

  return (
    <section aria-labelledby="remuneracao-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="remuneracao-titulo" className="text-2xl">
          Quanto custa o mandato
        </h2>
        <p className="text-sm text-muted-foreground">
          Salário e verbas que {A_CASA[casa]} paga para o mandato de {nome} funcionar
        </p>
      </div>

      <div className="figura">
        <p className="text-sm text-muted-foreground">Se usar tudo, por mês</p>
        <p className="numero text-3xl">{formatarReais(custo.total_se_usar_tudo)}</p>
        <p className="text-sm text-muted-foreground">
          Soma de {listaNomes(comValor)}, nos valores de hoje.
          {custo.faltando.length > 0 && (
            <>
              {" "}
              Fica de fora: {listaNomes(custo.faltando)}, porque {A_CASA[casa]} não publica o valor.
            </>
          )}
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <Barra rotulo="Se usar tudo" total={custo.total_se_usar_tudo} pedacos={segmentos(custo.itens, "valor", escala)} />
        <Barra
          rotulo={`${nome} usou`}
          detalhe={`só ${listaNomes(custo.medidos)}`}
          total={custo.usou_total}
          pedacos={segmentos(custo.itens, "usou", escala)}
        />
        <Barra
          rotulo={`Média ${CASA_DA[casa]}`}
          detalhe={`só ${listaNomes(custo.medidos)}`}
          total={custo.media_total}
          pedacos={segmentos(custo.itens, "media_casa", escala)}
        />
        <p className="text-sm text-muted-foreground">
          {periodo ? (
            <>
              Usou e média: {listaNomes(custo.medidos)}, média por mês {periodo}.
            </>
          ) : (
            <>Usou e média: só o salário; os gastos do gabinete ainda não foram carregados.</>
          )}{" "}
          {foraDoUso.length > 0 && <>Sem {listaNomes(foraDoUso)}, que o Panóptico ainda não tem. </>}A média é entre os{" "}
          {casa === "camara" ? "deputados" : "senadores"} em exercício; quem não usou entra com zero.
        </p>
      </div>

      <ul className="border-t border-border">
        {custo.itens.map((i) => (
          <Legenda key={i.item} i={i} casa={casa} />
        ))}
      </ul>

      <FolhaAtos casaNome={CASA_NOME[casa]} itens={custo.itens} />

      <p className="text-sm text-muted-foreground">
        Fora da conta: 13º salário, ajuda de custo no início e no fim do mandato e os encargos dos assessores, que{" "}
        {A_CASA[casa]} paga à parte. Os valores mudam por ato da Casa; a data de cada um está em &ldquo;De onde vem cada
        valor&rdquo;.
      </p>
      <FonteRodape
        fonte={`${CASA_NOME[casa]}: atos oficiais e ${custo.gastos_fonte_nome ? "gastos da cota" : "transparência"}`}
        url={custo.gastos_fonte_url ?? custo.itens[0]?.valor_url ?? undefined}
        atualizadoEm={custo.gastos_atualizado_em}
      />
    </section>
  );
}

function Barra({
  rotulo,
  detalhe,
  total,
  pedacos,
}: {
  rotulo: string;
  detalhe?: string;
  total: number;
  pedacos: ReturnType<typeof segmentos>;
}) {
  const descricao = pedacos.map((p) => `${p.nome} ${formatarReais(p.valor)}`).join(", ");
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3 text-base">
        <span className="min-w-0">
          {rotulo}
          {detalhe && <span className="block text-sm text-muted-foreground">{detalhe}</span>}
        </span>
        <b className="numero shrink-0 font-medium">{formatarReais(total)}</b>
      </div>
      <div
        role="img"
        aria-label={`${rotulo}${detalhe ? ` (${detalhe})` : ""}: ${formatarReais(total)} por mês. ${descricao}.`}
        className="flex h-4 w-full gap-px overflow-hidden rounded-[2px] bg-muted"
      >
        {pedacos.map((p) => (
          <i key={p.item} className={`block h-full ${TOM[p.item]}`} style={{ width: `${p.largura}%` }} />
        ))}
      </div>
    </div>
  );
}

function Legenda({ i, casa }: { i: ItemCustoMandato; casa: Casa }) {
  const termo = TERMO[i.item];
  // O termo oficial é o trecho antes da primeira vírgula; o resto ("limite de SC") fica fora do link.
  const corte = i.oficial.indexOf(", ");
  const [oficial, resto] = corte > 0 ? [i.oficial.slice(0, corte), i.oficial.slice(corte)] : [i.oficial, ""];
  return (
    <li className="grid grid-cols-[auto_1fr_auto] items-baseline gap-x-3 border-b border-border py-3">
      <span aria-hidden className={`size-3 translate-y-0.5 rounded-[1px] border border-foreground/30 ${TOM[i.item]}`} />
      <span className="text-base">{i.nome}</span>
      <span className="numero text-base">{i.valor === null ? "não publicado" : formatarReais(i.valor)}</span>
      <small className="col-start-2 col-end-4 text-sm text-muted-foreground">
        {termo && i.item !== "subsidio" ? <TermoOficial id={termo}>{oficial}</TermoOficial> : oficial}
        {resto}
        {" · "}
        <Uso i={i} casa={casa} />
      </small>
    </li>
  );
}

function Uso({ i, casa }: { i: ItemCustoMandato; casa: Casa }) {
  switch (i.usou_situacao) {
    case "fixo":
      return <>igual para todos os deputados federais e senadores</>;
    case "carregado":
      return (
        <>
          usou {formatarReais(i.usou ?? 0)} por mês; média {CASA_DA[casa]} {formatarReais(i.media_casa ?? 0)}
        </>
      );
    case "na_pagina_da_casa":
      return i.usou_url ? (
        <>
          o valor usado está na{" "}
          <LinkExterno href={i.usou_url} className="underline underline-offset-2">
            página do deputado na Câmara
          </LinkExterno>
        </>
      ) : (
        <>o valor usado está na página do deputado na Câmara</>
      );
    case "nao_carregado":
      return i.usou_url ? (
        <>
          quem recebe está na{" "}
          <LinkExterno href={i.usou_url} className="underline underline-offset-2">
            página de transparência do Senado
          </LinkExterno>
        </>
      ) : (
        <>o valor usado ainda não foi carregado</>
      );
    case "nao_publicado":
      return <>{A_CASA[casa]} não publica o valor; o Panóptico vai pedir pela Lei de Acesso à Informação</>;
  }
}

/** Versão antiga (API sem `custo`): só o salário. */
function SoSalario({ remuneracao }: { remuneracao: ParlamentarDetalhe["remuneracao"] }) {
  return (
    <section aria-labelledby="remuneracao-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="remuneracao-titulo" className="text-2xl">
          Salário
        </h2>
        <p className="text-sm text-muted-foreground">
          <TermoOficial id="subsidio">Subsídio</TermoOficial> mensal dos membros do Congresso
        </p>
      </div>
      <div className="figura">
        <p className="text-sm text-muted-foreground">Valor bruto por mês</p>
        <p className="numero text-3xl">{formatarReais(remuneracao.subsidio_mensal)}</p>
        <p className="text-sm text-muted-foreground">Desde {formatarData(remuneracao.vigente_desde)}</p>
      </div>
      <FonteRodape fonte={remuneracao.fonte_nome} url={remuneracao.fonte_url} />
    </section>
  );
}
