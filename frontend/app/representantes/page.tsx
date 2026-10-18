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
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaResumida } from "@/components/painel/lista-resumida";
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
import { formatarCep, formatarReais, formatarReaisCompacto } from "@/lib/formato";

export const metadata: Metadata = { title: "Seus representantes" };

type Busca = { cep?: string; uf?: string; municipio?: string };

/** Quantos aparecem de cara em cada lista; o resto fica em "Ver todos". */
const LIMITE_LISTA = 8;

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
  const cidade = localizacao.municipio;
  const nomeEstado = localizacao.estado;
  const lugar = cidade ? `${cidade}/${localizacao.uf}` : nomeEstado;

  const nExecutivo = executivo
    ? [executivo.presidente, executivo.governador, cidade ? executivo.prefeito : null].filter(Boolean).length
    : 0;
  const nEleitos2026 = eleitos2026?.ano_eleicao
    ? eleitos2026.presidente.length +
      eleitos2026.governador.length +
      eleitos2026.senadores.length +
      eleitos2026.deputados_federais.length +
      eleitos2026.deputados_estaduais.length
    : 0;
  const nAssembleia = assembleia?.itens.length ?? estaduais?.itens.length ?? 0;
  const nVereadores = camara?.itens.length ?? vereadores?.itens.length ?? 0;
  const nomeAssembleia = localizacao.uf === "DF" ? "Câmara Legislativa" : "Assembleia";
  const tituloEstaduais = localizacao.uf === "DF" ? "Deputados distritais" : `Deputados estaduais de ${nomeEstado}`;
  const contagem = (n: number, um: string, varios: string) => ({
    valor: n.toLocaleString("pt-BR"),
    complemento: n === 1 ? um : varios,
  });

  // Cada lista aparece UMA vez, dentro de uma aba; o cartão do topo abre a mesma lista em gaveta.
  const abas: AbaDetalhe[] = [
    {
      id: "executivo",
      rotulo: "Executivo",
      secoes: [
        {
          id: "executivo",
          titulo: "Executivo",
          conteudo: executivo && <ExecutivoSecao dados={executivo} estado={nomeEstado} cidade={cidade} />,
        },
      ],
    },
    {
      id: "senado",
      rotulo: "Senado",
      secoes: [
        {
          id: "senado",
          titulo: "Senadores",
          conteudo: (
            <Secao
              titulo="Senadores"
              explicacao="Cada estado elege 3 senadores."
              parlamentares={senadores}
              emendas={emendas}
            />
          ),
        },
      ],
    },
    {
      id: "deputados-federais",
      rotulo: "Câmara dos Deputados",
      secoes: [
        {
          id: "deputados",
          titulo: "Deputados federais",
          conteudo: (
            <Secao
              titulo="Deputados federais"
              explicacao={`${nomeEstado} tem ${deputados.length} deputados federais na Câmara.`}
              parlamentares={deputados}
              emendas={emendas}
              limite={LIMITE_LISTA}
            />
          ),
        },
      ],
    },
    {
      id: "assembleia",
      rotulo: nomeAssembleia,
      secoes: [
        {
          id: "assembleia",
          titulo: `${nomeAssembleia} de ${nomeEstado}`,
          conteudo: assembleia && (
            <CamaraSecao
              dados={assembleia}
              casa="assembleia"
              nome={`${nomeAssembleia} de ${nomeEstado}`}
              limite={LIMITE_LISTA}
            />
          ),
        },
        {
          id: "estaduais",
          titulo: tituloEstaduais,
          conteudo: estaduais && estaduais.itens.length > 0 && (
            <EleitosSecao
              recolhido={Boolean(assembleia)}
              id="estaduais-titulo"
              titulo={tituloEstaduais}
              explicacao={`Eleitos em ${estaduais.ano_eleicao} para a ${localizacao.uf === "DF" ? "Câmara Legislativa" : "Assembleia Legislativa"}, segundo o TSE. Quem hoje está em outro cargo aparece indicado.`}
              dados={estaduais}
              limite={LIMITE_LISTA}
            />
          ),
        },
      ],
    },
  ];
  if (cidade) {
    abas.push({
      id: "municipal",
      rotulo: "Câmara municipal",
      secoes: [
        {
          id: "camara",
          titulo: `Câmara de ${cidade}`,
          conteudo: camara && <CamaraSecao dados={camara} nome={`Câmara de ${cidade}`} limite={LIMITE_LISTA} />,
        },
        {
          id: "vereadores",
          titulo: `Vereadores de ${cidade}`,
          conteudo: vereadores && vereadores.itens.length > 0 && (
            <EleitosSecao
              recolhido={Boolean(camara)}
              id="vereadores-titulo"
              titulo={`Vereadores de ${cidade}`}
              explicacao={`Eleitos em ${vereadores.ano_eleicao} para a câmara municipal, segundo o TSE. Um suplente pode ter assumido alguma vaga depois.`}
              dados={vereadores}
              limite={LIMITE_LISTA}
            />
          ),
        },
        { id: "canais", titulo: "Canais oficiais", conteudo: <CanaisSecao canais={canais} cidade={cidade} /> },
      ],
    });
  }
  if (nEleitos2026 > 0 && eleitos2026) {
    abas.push({
      id: "eleitos",
      rotulo: `Eleitos ${eleitos2026.ano_eleicao}`,
      secoes: [
        {
          id: "eleitos-2026",
          titulo: `Eleitos em ${eleitos2026.ano_eleicao}`,
          conteudo: <EleitosFuturosSecao dados={eleitos2026} estado={nomeEstado} />,
        },
      ],
    });
  }

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <p className="sobretitulo">
            {localizacao.cep
              ? `CEP ${formatarCep(localizacao.cep)}`
              : cidade
                ? "Busca por cidade"
                : "Busca por estado"}
          </p>
          <h1 className="titulo-pagina">Você está em {lugar}</h1>
          <p className="text-muted-foreground">
            Quem governa e quem representa {lugar}, do Executivo à câmara municipal:
          </p>
        </div>

        <GradeCartoes rotulo={`Quem representa ${lugar}`}>
          {nExecutivo > 0 && (
            <CartaoNumero
              destino="executivo"
              rotulo="Quem governa"
              {...contagem(nExecutivo, "cargo", "cargos")}
              apoio={cidade ? "Presidente, governador e prefeito" : "Presidente e governador"}
            />
          )}
          <CartaoNumero
            destino="senado"
            rotulo={`Senadores de ${nomeEstado}`}
            {...contagem(senadores.length, "senador", "senadores")}
          />
          <CartaoNumero
            destino="deputados"
            rotulo="Câmara dos Deputados"
            {...contagem(deputados.length, "deputado", "deputados")}
          />
          {nAssembleia > 0 && (
            <CartaoNumero
              destino={assembleia ? "assembleia" : "estaduais"}
              rotulo={`${nomeAssembleia} de ${nomeEstado}`}
              {...contagem(nAssembleia, "deputado", "deputados")}
            />
          )}
          {cidade && nVereadores > 0 && (
            <CartaoNumero
              destino={camara ? "camara" : "vereadores"}
              rotulo={`Câmara de ${cidade}`}
              {...contagem(nVereadores, "vereador", "vereadores")}
            />
          )}
          {nEleitos2026 > 0 && eleitos2026 && (
            <CartaoNumero
              destino="eleitos-2026"
              rotulo={`Eleitos em ${eleitos2026.ano_eleicao}`}
              {...contagem(nEleitos2026, "eleito", "eleitos")}
              apoio={`Posse em ${(eleitos2026.ano_eleicao ?? 0) + 1}`}
            />
          )}
        </GradeCartoes>
        <p className="text-sm text-muted-foreground">Toque num cartão para ver quem são, com a fonte e a data.</p>

        <CompartilharWhatsApp
          caminho={
            localizacao.codigo_ibge
              ? `/representantes?municipio=${localizacao.codigo_ibge}`
              : `/representantes?uf=${localizacao.uf}`
          }
          texto={`Veja quem representa ${lugar} no Congresso e para onde foi o dinheiro da cidade:`}
        />
      </div>

      {localizacao.codigo_ibge && cidade && (
        <DinheiroDaCidade
          ibge={localizacao.codigo_ibge}
          cidade={cidade}
          uf={localizacao.uf}
          emendas={emendas}
          contas={contas}
          fornecedores={fornecedores}
          fornecedoresPncp={fornecedoresPncp}
        />
      )}

      <AbasDetalhe titulo="Quem são, esfera por esfera" abas={abas} />

      <Link
        href={`/parlamentares?uf=${localizacao.uf}`}
        className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
      >
        Comparar os números de todos de {nomeEstado}
      </Link>

      <FonteRodape fonte="Dados Abertos da Câmara e do Senado" atualizadoEm={atualizado_em} />
    </article>
  );
}

function Secao({
  titulo,
  explicacao,
  parlamentares,
  emendas,
  limite,
}: {
  titulo: string;
  explicacao: string;
  parlamentares: ParlamentarResumo[];
  emendas: EmendasMunicipio | null;
  limite?: number;
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
        <ListaResumida
          limite={limite}
          itens={parlamentares.map((p) => (
            <li key={p.id} className="border-b border-border">
              <ParlamentarCard parlamentar={p} destaque={destaque(p.id)} />
            </li>
          ))}
        />
      )}
    </section>
  );
}

/** Data mais antiga entre as informadas (a mais conservadora). */
function dataMaisAntiga(datas: (string | null | undefined)[]) {
  const validas = datas.filter((d): d is string => Boolean(d)).sort();
  return validas[0] ?? null;
}

/** Resumo do dinheiro da cidade em cartões; cada um leva à página /cidade/[ibge]. */
function DinheiroDaCidade({
  ibge,
  cidade,
  uf,
  emendas,
  contas,
  fornecedores,
  fornecedoresPncp,
}: {
  ibge: string;
  cidade: string;
  uf: string;
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
    ? { nome: tce.fornecedor, valor: tce.valor_pago, ano: fornecedores!.ano, fonte: "Pago, segundo o Tribunal de Contas" }
    : pncp
      ? { nome: pncp.fornecedor!, valor: pncp.valor, ano: fornecedoresPncp!.ano, fonte: "Em contratos, segundo o PNCP" }
      : null;
  const gastoInformado = contas && contas.despesa_paga && contas.despesa_por_habitante != null;
  const temEmendas = emendas && emendas.total > 0;
  if (!temEmendas && !gastoInformado && !maior) return null;
  const href = `/cidade/${ibge}`;
  return (
    <section aria-labelledby="dinheiro-titulo" className="flex flex-col gap-3">
      <h2 id="dinheiro-titulo" className="text-2xl">
        Dinheiro de {cidade}
      </h2>
      <GradeCartoes rotulo={`Dinheiro de ${cidade}`}>
        {temEmendas && (
          <CartaoNumero
            destino="emendas"
            href={href}
            rotulo={`Emendas pagas desde ${emendas.desde}`}
            valor={formatarReaisCompacto(emendas.total)}
            apoio={
              emendas.por_habitante != null && emendas.media_uf_por_habitante != null
                ? `${formatarReais(emendas.por_habitante, true)} por morador · média de ${uf}: ${formatarReais(emendas.media_uf_por_habitante, true)}`
                : undefined
            }
          />
        )}
        {gastoInformado && contas && (
          <CartaoNumero
            destino="contas"
            href={href}
            rotulo={`Prefeitura gastou por morador em ${contas.ano}`}
            valor={formatarReais(contas.despesa_por_habitante!, true)}
            apoio={
              contas.media_uf_despesa_por_habitante != null
                ? `Média dos municípios de ${uf}: ${formatarReais(contas.media_uf_despesa_por_habitante, true)}`
                : undefined
            }
          />
        )}
        {maior && (
          <CartaoNumero
            destino="fornecedores"
            href={href}
            rotulo={`Maior fornecedor em ${maior.ano}`}
            valor={formatarReaisCompacto(maior.valor)}
            apoio={`${maior.nome}. ${maior.fonte}`}
          />
        )}
      </GradeCartoes>
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
