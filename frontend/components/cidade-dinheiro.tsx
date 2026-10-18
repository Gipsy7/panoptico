import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { ContasSecao } from "@/components/contas-secao";
import { EmendasMunicipioSecao } from "@/components/emendas-municipio";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FornecedoresPncpSecao } from "@/components/fornecedores-pncp-secao";
import { FornecedoresSecao } from "@/components/fornecedores-secao";
import { Revelacao } from "@/components/revelacao";
import {
  getContas,
  getEmendasMunicipio,
  getFornecedores,
  getFornecedoresPncp,
  getRepresentantes,
} from "@/lib/api";

// Estados com o Tribunal de Contas carregado (ver backend/ingestion/fontes.toml).
const UF_COM_TCE = ["SP", "RS"];

/** Metadados da página /cidade/[ibge]. */
export async function metadadosCidade(ibge: string): Promise<Metadata> {
  const r = await getRepresentantes({ municipio: ibge });
  if (!r.ok || !r.dados.localizacao.municipio) return { title: "Dinheiro da cidade" };
  const lugar = `${r.dados.localizacao.municipio}-${r.dados.localizacao.uf}`;
  return {
    title: `Para onde foi o dinheiro de ${lugar}`,
    description: `Emendas parlamentares pagas, contas da prefeitura e fornecedores de ${lugar}, com dados oficiais, fonte e data.`,
  };
}

/** Corpo da página /cidade/[ibge]; `params` ainda é uma Promise (cacheComponents). */
export function PaginaCidade({ params }: { params: Promise<{ ibge: string }> }) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o dinheiro da cidade…" secoes={4} />}>
      {params.then(({ ibge }) => (
        <Cidade ibge={ibge} />
      ))}
    </Revelacao>
  );
}

async function Cidade({ ibge }: { ibge: string }) {
  const rep = await getRepresentantes({ municipio: ibge });
  if (!rep.ok) {
    if (rep.status === 404 || rep.status === 422) notFound();
    return <AvisoErro titulo="Não deu para buscar agora" mensagem={rep.mensagem} />;
  }
  const { municipio, uf, estado } = rep.dados.localizacao;
  if (!municipio) notFound();

  const [emendasR, contasR, fornecedoresR, pncpR] = await Promise.all([
    getEmendasMunicipio(ibge),
    getContas(ibge),
    getFornecedores(ibge),
    getFornecedoresPncp(ibge),
  ]);
  const emendas = emendasR.ok ? emendasR.dados : null;
  const contas = contasR.ok ? contasR.dados : null;
  const fornecedores = fornecedoresR.ok ? fornecedoresR.dados : null;
  const pncp = pncpR.ok && pncpR.dados.itens.length > 0 ? pncpR.dados : null;
  const populacao = emendas?.populacao ?? contas?.populacao ?? null;
  const tceCarregado = UF_COM_TCE.includes(uf);

  return (
    <div className="pagina-secoes">
      <div className="flex flex-col gap-1">
        <p className="sobretitulo">Dinheiro público</p>
        <h1 className="titulo-pagina">
          Para onde foi o dinheiro de {municipio}-{uf}
        </h1>
        {populacao != null && (
          <p className="text-muted-foreground">
            <span className="tabular-nums">{populacao.toLocaleString("pt-BR")}</span> habitantes
          </p>
        )}
        <Link
          href={`/representantes?municipio=${ibge}`}
          className="self-start text-sm font-medium text-primary underline underline-offset-4"
        >
          Quem representa {municipio}
        </Link>
      </div>

      <CompartilharWhatsApp
        caminho={`/cidade/${ibge}`}
        texto={`Veja para onde foi o dinheiro de ${municipio}: emendas, contas da prefeitura e fornecedores, com dados oficiais:`}
      />

      {emendas ? (
        <EmendasMunicipioSecao dados={emendas} />
      ) : (
        <SemDado titulo="Dinheiro enviado por emendas" mensagem="Não deu para buscar as emendas desta cidade agora." />
      )}

      {contas ? (
        <ContasSecao dados={contas} cidade={municipio} />
      ) : (
        <SemDado
          titulo={`Contas de ${municipio}`}
          mensagem="As contas anuais desta prefeitura ainda não estão carregadas."
        />
      )}

      {fornecedores ? (
        <FornecedoresSecao dados={fornecedores} cidade={municipio} />
      ) : (
        <SemDado
          titulo={`Para quem ${municipio} pagou`}
          mensagem={
            tceCarregado
              ? `O Tribunal de Contas de ${estado} não trouxe pagamentos desta cidade (a capital paulista, por exemplo, é fiscalizada por um tribunal municipal que ainda não foi carregado).`
              : `Os pagamentos por fornecedor vêm do Tribunal de Contas do estado, e o de ${estado} ainda não foi carregado.`
          }
        />
      )}

      {pncp && <FornecedoresPncpSecao dados={pncp} cidade={municipio} />}

      <section aria-labelledby="fora-titulo" className="flex flex-col gap-2">
        <h2 id="fora-titulo" className="text-2xl">
          O que ficou de fora
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-muted-foreground">
          <li>
            As transferências especiais (&quot;emendas Pix&quot;) e os convênios não trazem o município na
            fonte, então não aparecem nas emendas desta página.
          </li>
          <li>
            Emendas de bancada, de comissão e de relator não estão somadas, e só entra o valor já pago.
          </li>
          <li>
            Só os Tribunais de Contas de São Paulo e do Rio Grande do Sul estão carregados; os dos
            demais estados ainda não.
          </li>
          <li>Prefeituras que não publicam contratos no PNCP não aparecem na lista de contratos.</li>
        </ul>
      </section>
    </div>
  );
}

function SemDado({ titulo, mensagem }: { titulo: string; mensagem: string }) {
  return (
    <section className="flex flex-col gap-1">
      <h2 className="text-2xl">{titulo}</h2>
      <p className="text-sm text-muted-foreground">{mensagem}</p>
    </section>
  );
}
