import type { Metadata } from "next";
import Link from "next/link";

import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { AvisoErro } from "@/components/aviso-erro";
import { Revelacao } from "@/components/revelacao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { CamaraSecao } from "@/components/camara-secao";
import { CanaisSecao } from "@/components/canais-secao";
import { EleitosSecao } from "@/components/eleitos-secao";
import { EleitosFuturosSecao } from "@/components/eleito-futuro";
import { ExecutivoSecao } from "@/components/executivo-secao";
import { ParlamentarCard } from "@/components/parlamentar-card";
import {
  type ContasMunicipio,
  type EmendasMunicipio,
  type Fornecedores,
  type FornecedoresPncp,
  type ParlamentarResumo,
  getDeputadosEstaduais,
  getEleitos2026,
  getAssembleia,
  getCamara,
  getCanais,
  getContas,
  getFornecedores,
  getFornecedoresPncp,
  getExecutivo,
  getEmendasMunicipio,
  getVereadores,
  getRepresentantes,
} from "@/lib/api";
import { formatarCep, formatarReais } from "@/lib/formato";

export const metadata: Metadata = { title: "Seus representantes" };

type Busca = { cep?: string; uf?: string; municipio?: string };

export default function RepresentantesPage({ searchParams }: PageProps<"/representantes">) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando representantes…" secoes={4} />}>
      {searchParams.then((sp) => (
        <Lista
          cep={primeiro(sp.cep)}
          uf={primeiro(sp.uf)}
          municipio={primeiro(sp.municipio)}
        />
      ))}
    </Revelacao>
  );
}

function primeiro(valor: string | string[] | undefined) {
  return Array.isArray(valor) ? valor[0] : valor;
}

async function Lista({ cep, uf, municipio }: Busca) {
  if (!cep && !uf && !municipio) {
    return <AvisoErro titulo="Faltou o CEP" mensagem="Digite um CEP para ver seus representantes." />;
  }

  const resultado = await getRepresentantes({ cep, uf, municipio });
  if (!resultado.ok) {
    const titulo =
      resultado.status === 404
        ? municipio
          ? "Não encontramos essa cidade"
          : "Não encontramos esse CEP"
        : resultado.status === 422
          ? "CEP inválido"
          : "Não deu para buscar agora";
    return <AvisoErro titulo={titulo} mensagem={resultado.mensagem} />;
  }

  const { localizacao, deputados, senadores, atualizado_em } = resultado.dados;
  const [emendasResultado, vereadoresResultado, estaduaisResultado, executivoResultado, canaisResultado, contasResultado, camaraResultado, fornecedoresResultado, fornecedoresPncpResultado, assembleiaResultado, eleitos2026Resultado] = await Promise.all([
    localizacao.codigo_ibge ? getEmendasMunicipio(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getVereadores(localizacao.codigo_ibge) : null,
    getDeputadosEstaduais(localizacao.uf),
    getExecutivo(localizacao.uf, localizacao.codigo_ibge),
    localizacao.codigo_ibge ? getCanais(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getContas(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getCamara(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getFornecedores(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getFornecedoresPncp(localizacao.codigo_ibge) : null,
    getAssembleia(localizacao.uf),
    getEleitos2026(localizacao.uf),
  ]);
  const eleitos2026 = eleitos2026Resultado.ok ? eleitos2026Resultado.dados : null;
  const assembleia = assembleiaResultado.ok ? assembleiaResultado.dados : null;
  const fornecedores = fornecedoresResultado?.ok ? fornecedoresResultado.dados : null;
  const fornecedoresPncp = fornecedoresPncpResultado?.ok ? fornecedoresPncpResultado.dados : null;
  const camara = camaraResultado?.ok ? camaraResultado.dados : null;
  const contas = contasResultado?.ok ? contasResultado.dados : null;
  const canais = canaisResultado?.ok ? canaisResultado.dados.itens : [];
  const executivo = executivoResultado.ok ? executivoResultado.dados : null;
  const vereadores = vereadoresResultado?.ok ? vereadoresResultado.dados : null;
  const estaduais = estaduaisResultado.ok ? estaduaisResultado.dados : null;
  const emendas = emendasResultado?.ok ? emendasResultado.dados : null;
  const lugar = localizacao.municipio
    ? `${localizacao.municipio}/${localizacao.uf}`
    : localizacao.estado;

  return (
    <div className="pagina-secoes">
      <div className="flex flex-col gap-1">
        <p className="sobretitulo">
          {localizacao.cep
            ? `CEP ${formatarCep(localizacao.cep)}`
            : localizacao.municipio
              ? "Busca por cidade"
              : "Busca por estado"}
        </p>
        <h1 className="titulo-pagina">Você está em {lugar}</h1>
        <p className="text-muted-foreground">
          Quem governa e quem representa {lugar}, do Executivo à câmara municipal:
        </p>
      </div>

      <CompartilharWhatsApp
        caminho={
          localizacao.codigo_ibge
            ? `/representantes?municipio=${localizacao.codigo_ibge}`
            : `/representantes?uf=${localizacao.uf}`
        }
        texto={`Veja quem representa ${lugar} no Congresso e para onde foi o dinheiro da cidade:`}
      />

      {executivo && (
        <ExecutivoSecao dados={executivo} estado={localizacao.estado} cidade={localizacao.municipio} />
      )}

      <Secao
        titulo="Senadores"
        explicacao="Cada estado elege 3 senadores."
        parlamentares={senadores}
        emendas={emendas}
      />
      <Secao
        titulo="Deputados federais"
        explicacao={`${localizacao.estado} tem ${deputados.length} deputados federais na Câmara.`}
        parlamentares={deputados}
        emendas={emendas}
      />

      {eleitos2026 && eleitos2026.ano_eleicao && (
        <EleitosFuturosSecao dados={eleitos2026} estado={localizacao.estado} />
      )}

      {localizacao.codigo_ibge && localizacao.municipio && (
        <DinheiroDaCidade
          ibge={localizacao.codigo_ibge}
          cidade={localizacao.municipio}
          emendas={emendas}
          contas={contas}
          fornecedores={fornecedores}
          fornecedoresPncp={fornecedoresPncp}
        />
      )}

      {camara && localizacao.municipio && <CamaraSecao dados={camara} nome={`Câmara de ${localizacao.municipio}`} />}

      {vereadores && vereadores.itens.length > 0 && (
        <EleitosSecao
          recolhido={Boolean(camara)}
          id="vereadores-titulo"
          titulo={`Vereadores de ${localizacao.municipio}`}
          explicacao={`Eleitos em ${vereadores.ano_eleicao} para a câmara municipal, segundo o TSE. Um suplente pode ter assumido alguma vaga depois.`}
          dados={vereadores}
        />
      )}

      {localizacao.municipio && <CanaisSecao canais={canais} cidade={localizacao.municipio} />}

      {assembleia && (
        <CamaraSecao dados={assembleia} casa="assembleia" nome={`Assembleia de ${localizacao.estado}`} />
      )}

      {estaduais && estaduais.itens.length > 0 && (
        <EleitosSecao
          recolhido={Boolean(assembleia)}
          id="estaduais-titulo"
          titulo={localizacao.uf === "DF" ? "Deputados distritais" : `Deputados estaduais de ${localizacao.estado}`}
          explicacao={`Eleitos em ${estaduais.ano_eleicao} para a ${localizacao.uf === "DF" ? "Câmara Legislativa" : "Assembleia Legislativa"}, segundo o TSE. Quem hoje está em outro cargo aparece indicado.`}
          dados={estaduais}
        />
      )}

      <Link
        href={`/parlamentares?uf=${localizacao.uf}`}
        className="self-start text-sm font-medium text-primary underline underline-offset-4"
      >
        Comparar os números de todos de {localizacao.estado}
      </Link>

      <FonteRodape fonte="Dados Abertos da Câmara e do Senado" atualizadoEm={atualizado_em} />
    </div>
  );
}

function Secao({
  titulo,
  explicacao,
  parlamentares,
  emendas,
}: {
  titulo: string;
  explicacao: string;
  parlamentares: ParlamentarResumo[];
  emendas: EmendasMunicipio | null;
}) {
  const enviado = new Map(emendas?.parlamentares.map((e) => [e.parlamentar.id, e.total]));
  const destaque = (id: number) => {
    const valor = enviado.get(id);
    return valor && emendas
      ? `Enviou ${formatarReais(valor, true)} para ${emendas.municipio.nome}`
      : undefined;
  };
  return (
    <section className="flex flex-col gap-3" aria-labelledby={`secao-${titulo}`}>
      <div>
        <h2 id={`secao-${titulo}`} className="text-2xl">
          {titulo} <span className="text-muted-foreground">({parlamentares.length})</span>
        </h2>
        <p className="text-sm text-muted-foreground">{explicacao}</p>
      </div>
      {parlamentares.length === 0 ? (
        <p className="text-muted-foreground">Nenhum dado carregado ainda.</p>
      ) : (
        <ul className="grid grid-cols-[minmax(0,1fr)] border-t border-border sm:grid-cols-2 sm:gap-x-10">
          {parlamentares.map((p) => (
            <li key={p.id} className="border-b border-border">
              <ParlamentarCard parlamentar={p} destaque={destaque(p.id)} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Data mais antiga entre as informadas (a mais conservadora). */
function dataMaisAntiga(datas: (string | null | undefined)[]) {
  const validas = datas.filter((d): d is string => Boolean(d)).sort();
  return validas[0] ?? null;
}

function DinheiroDaCidade({
  ibge,
  cidade,
  emendas,
  contas,
  fornecedores,
  fornecedoresPncp,
}: {
  ibge: string;
  cidade: string;
  emendas: EmendasMunicipio | null;
  contas: ContasMunicipio | null;
  fornecedores: Fornecedores | null;
  fornecedoresPncp: FornecedoresPncp | null;
}) {
  // Maior fornecedor nomeado: o maior valor pago pelo TCE; sem ele, o maior contrato do PNCP.
  const tce = (fornecedores?.orgaos ?? [])
    .flatMap((o) => o.itens)
    .filter((f) => f.documento)
    .sort((a, b) => b.valor_pago - a.valor_pago)[0];
  const pncp = fornecedoresPncp?.itens.find((f) => !f.ente_publico && f.fornecedor);
  const maior = tce
    ? { nome: tce.fornecedor, valor: tce.valor_pago, ano: fornecedores!.ano, fonte: "pago, segundo o Tribunal de Contas" }
    : pncp
      ? { nome: pncp.fornecedor!, valor: pncp.valor, ano: fornecedoresPncp!.ano, fonte: "em contratos, segundo o PNCP" }
      : null;
  const gastoInformado = contas && contas.despesa_paga && contas.despesa_por_habitante != null;
  const temEmendas = emendas && emendas.total > 0;
  if (!temEmendas && !gastoInformado && !maior) return null;
  return (
    <section aria-labelledby="dinheiro-titulo" className="flex flex-col gap-3">
      <h2 id="dinheiro-titulo" className="text-2xl">
        Dinheiro de {cidade}
      </h2>
      <dl className="grid gap-3 sm:grid-cols-3">
        {temEmendas && (
          <div className="figura min-w-0">
            <dt className="text-sm text-muted-foreground">Emendas pagas desde {emendas.desde}</dt>
            <dd className="numero text-2xl break-words">{formatarReais(emendas.total, true)}</dd>
          </div>
        )}
        {gastoInformado && contas && (
          <div className="figura min-w-0">
            <dt className="text-sm text-muted-foreground">Gasto da prefeitura por habitante em {contas.ano}</dt>
            <dd className="numero text-2xl break-words">{formatarReais(contas.despesa_por_habitante!, true)}</dd>
            {contas.media_uf_despesa_por_habitante != null && (
              <dd className="text-xs text-muted-foreground">
                Média dos municípios do estado: {formatarReais(contas.media_uf_despesa_por_habitante, true)}
              </dd>
            )}
          </div>
        )}
        {maior && (
          <div className="figura min-w-0">
            <dt className="text-sm text-muted-foreground">Maior fornecedor em {maior.ano}</dt>
            <dd className="numero text-2xl break-words">{formatarReais(maior.valor, true)}</dd>
            <dd className="text-xs text-muted-foreground">
              {maior.nome}, {maior.fonte}
            </dd>
          </div>
        )}
      </dl>
      <Link
        href={`/cidade/${ibge}`}
        className="self-start text-sm font-medium text-primary underline underline-offset-4"
      >
        Para onde foi o dinheiro de {cidade}
      </Link>
      <FonteRodape
        fonte="Portal da Transparência, Tesouro Nacional, Tribunais de Contas e PNCP"
        url="/sobre-as-fontes"
        atualizadoEm={dataMaisAntiga([
          temEmendas ? emendas?.atualizado_em : null,
          gastoInformado ? contas?.atualizado_em : null,
          maior ? (tce ? fornecedores?.atualizado_em : fornecedoresPncp?.atualizado_em) : null,
        ])}
      />
    </section>
  );
}
