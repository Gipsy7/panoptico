import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { Revelacao } from "@/components/revelacao";
import {
  getDinheiroFederal,
  getDinheiroFederalMunicipio,
  getDinheiroFederalUf,
} from "@/lib/api";
import { UFS } from "@/lib/ufs";

import { ANO_PADRAO, MENSAGEM_CARREGANDO } from "./formatos";
import { PainelDinheiroFederal } from "./painel-dinheiro-federal";

type Entrada = { lugar?: string[]; ano?: string | string[] };

/** Lê o caminho (/SC/4205407) e o ?ano=; devolve null quando a rota não existe. */
export function lerRota({ lugar, ano }: Entrada) {
  if ((lugar?.length ?? 0) > 2) return null;
  const uf = lugar?.[0]?.toUpperCase() ?? null;
  const ibge = lugar?.[1] ?? null;
  if (uf && !UFS.some((u) => u.sigla === uf)) return null;
  if (ibge && !/^\d{7}$/.test(ibge)) return null;
  const bruto = Array.isArray(ano) ? ano[0] : ano;
  const n = bruto && /^\d{4}$/.test(bruto) ? Number(bruto) : ANO_PADRAO;
  return { uf, ibge, ano: n };
}

export async function metadadosDinheiroFederal(entrada: Entrada): Promise<Metadata> {
  const rota = lerRota(entrada);
  const base = "Impostos e repasses: quanto a União arrecada e repassa em cada estado e cidade";
  if (!rota?.uf) {
    return {
      title: base,
      description:
        "Quanto a União arrecadou em cada estado e quanto repassou a governos estaduais e prefeituras, com fonte e data.",
    };
  }
  const nomeUf = UFS.find((u) => u.sigla === rota.uf)?.nome ?? rota.uf;
  if (!rota.ibge) {
    return {
      title: `Impostos e repasses em ${nomeUf}`,
      description: `Quanto a União arrecadou em ${nomeUf} e quanto repassou ao estado e às prefeituras, com fonte e data.`,
    };
  }
  const m = await getDinheiroFederalMunicipio(rota.ibge);
  const nome = m.ok ? m.dados.municipio.nome : "a cidade";
  return {
    title: `Repasses da União para ${nome}-${rota.uf}`,
    description: `Quanto a União repassou à prefeitura de ${nome} (${nomeUf}), de onde vem o dinheiro e quanto pesa na receita, com fonte e data.`,
  };
}

/** Página sem async no topo: os params só são lidos dentro do Suspense (cacheComponents). */
export function PaginaDinheiroFederal({
  params,
  searchParams,
}: {
  params: Promise<{ lugar?: string[] }>;
  searchParams: Promise<{ ano?: string | string[] }>;
}) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando os impostos e repasses…" secoes={3} />}>
      {Promise.all([params, searchParams]).then(([p, s]) => (
        <Dados lugar={p.lugar} ano={s.ano} />
      ))}
    </Revelacao>
  );
}

async function Dados(entrada: Entrada) {
  const rota = lerRota(entrada);
  if (!rota) notFound();
  const { uf, ibge, ano } = rota;
  const [painel, estado, municipio] = await Promise.all([
    getDinheiroFederal(ano),
    uf ? getDinheiroFederalUf(uf, ano) : null,
    ibge ? getDinheiroFederalMunicipio(ibge) : null,
  ]);
  if (!painel.ok) {
    if (painel.status === 404) notFound();
    return <AvisoErro titulo="Não deu para carregar impostos e repasses" mensagem={painel.mensagem} />;
  }
  if (painel.dados.sem_dados) {
    return (
      <div className="flex flex-col gap-3">
        <p className="sobretitulo">Impostos e repasses</p>
        <h1 className="titulo-pagina">Quanto a União arrecada e repassa</h1>
        <p className="text-muted-foreground">{MENSAGEM_CARREGANDO}</p>
      </div>
    );
  }
  if (estado && !estado.ok && estado.status === 404) notFound();
  if (municipio && !municipio.ok && municipio.status === 404) notFound();
  return (
    <PainelDinheiroFederal
      inicial={{
        uf,
        ibge,
        ano,
        painel: painel.dados,
        estado: estado?.ok ? estado.dados : null,
        municipio: municipio?.ok ? municipio.dados : null,
      }}
    />
  );
}
