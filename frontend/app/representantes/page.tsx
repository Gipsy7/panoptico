import type { Metadata } from "next";
import Link from "next/link";

import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { AvisoErro } from "@/components/aviso-erro";
import { AvisoSegundoTurno } from "@/components/aviso-segundo-turno";
import { CepForm } from "@/components/cep-form";
import { Revelacao } from "@/components/revelacao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { CamaraSecao } from "@/components/camara-secao";
import { CanaisSecao } from "@/components/canais-secao";
import { EleitosSecao } from "@/components/eleitos-secao";
import { EleitosFuturosSecao } from "@/components/eleito-futuro";
import { ExecutivoSecao } from "@/components/executivo-secao";
import { ParlamentarCard } from "@/components/parlamentar-card";
import { PrediosRepresentantes, type PredioDados, type PessoaPredio } from "@/components/predios-representantes";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaResumida } from "@/components/painel/lista-resumida";
import {
  type Camara,
  type Chapa,
  type Executivo,
  type ContasMunicipio,
  type EmendasMunicipio,
  type Fornecedores,
  type FornecedoresPncp,
  type ListaEleitos,
  type ParlamentarResumo,
  urlFotoDe,
  urlFotoTse,
  getDeputadosEstaduais,
  getEleitos2026,
  getAssembleia,
  getCamara,
  getCanais,
  getContas,
  getDinheiroFederal,
  getFornecedores,
  getFornecedoresPncp,
  getExecutivo,
  getEmendasMunicipio,
  getVereadores,
  getRepresentantes,
} from "@/lib/api";
import { formatarCep, formatarReais, formatarReaisCompacto } from "@/lib/formato";
import { type PredioId, contagem, faixaEstado } from "@/lib/predios";
import { doEstado } from "@/lib/ufs";

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
  if (!resultado.ok && resultado.status === 404 && cep && !municipio) {
    // CEP que os Correios não têm: em geral o "CEP geral" (final 000) de cidade que usa CEP por rua.
    const geral = cep.replace(/\D/g, "").endsWith("000");
    return (
      <div className="flex flex-col gap-6">
        <AvisoErro
          titulo="Não encontramos esse CEP"
          mensagem={
            geral
              ? "Os Correios não têm esse CEP. Cidades com CEP por rua não usam o CEP terminado em 000: digite o CEP da sua rua ou escolha o estado e a cidade abaixo."
              : "Os Correios não têm esse CEP. Confira os números ou escolha o estado e a cidade abaixo."
          }
        />
        <div className="painel max-w-md">
          <CepForm semCepInicial />
        </div>
      </div>
    );
  }
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
  const [emendasResultado, vereadoresResultado, estaduaisResultado, executivoResultado, canaisResultado, contasResultado, camaraResultado, fornecedoresResultado, fornecedoresPncpResultado, assembleiaResultado, eleitos2026Resultado, federalResultado] = await Promise.all([
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
    getDinheiroFederal(),
  ]);
  const federal = federalResultado.ok ? federalResultado.dados : null;
  const federalUf = federal?.ufs.find((u) => u.uf === localizacao.uf) ?? null;
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

  const nEleitos2026 = eleitos2026?.ano_eleicao
    ? eleitos2026.presidente.length +
      eleitos2026.governador.length +
      eleitos2026.senadores.length +
      eleitos2026.deputados_federais.length +
      eleitos2026.deputados_estaduais.length
    : 0;
  const nomeAssembleia = localizacao.uf === "DF" ? "Câmara Legislativa" : "Assembleia";
  const tituloEstaduais = localizacao.uf === "DF" ? "Deputados distritais" : `Deputados estaduais de ${nomeEstado}`;
  const eDF = localizacao.uf === "DF";
  const temCidade = Boolean(cidade) && !eDF;
  const predios = montarPredios({
    uf: localizacao.uf,
    nomeEstado,
    cidade: temCidade ? cidade : null,
    nomeAssembleia,
    executivo,
    senadores,
    deputados,
    atualizadoCongresso: atualizado_em,
    assembleia,
    estaduais,
    camara,
    vereadores,
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
          titulo: `${nomeAssembleia} ${doEstado(localizacao.uf)}`,
          conteudo: assembleia && (
            <CamaraSecao
              dados={assembleia}
              casa="assembleia"
              nome={`${nomeAssembleia} ${doEstado(localizacao.uf)}`}
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
            {temCidade
              ? "Quem decide sobre a sua vida mora em três andares: o país, o estado e a cidade. Toque num prédio para ver quem trabalha lá e o que faz."
              : "Quem decide sobre a sua vida mora em andares: o país e o estado. Toque num prédio para ver quem trabalha lá e o que faz."}
          </p>
        </div>

        <PrediosRepresentantes
          predios={predios}
          faixaEstado={faixaEstado(localizacao.uf, nomeEstado)}
          faixaCidade={temCidade && cidade ? cidade.toUpperCase() : null}
          voce={`Você, em ${temCidade && cidade ? cidade : nomeEstado}`}
        />
        {nEleitos2026 > 0 && eleitos2026 && (
          <a
            href="#ver-eleitos-2026"
            className="flex min-h-11 flex-col gap-1 rounded-[var(--radius)] border border-border bg-card p-3 hover:border-foreground/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze sm:p-4"
          >
            <span className="text-sm text-muted-foreground">
              Eleitos em {eleitos2026.ano_eleicao} · posse em {(eleitos2026.ano_eleicao ?? 0) + 1}
            </span>
            <span className="numero text-[1.375rem] leading-none">
              {nEleitos2026.toLocaleString("pt-BR")}{" "}
              <span className="text-base text-muted-foreground">{nEleitos2026 === 1 ? "eleito" : "eleitos"}</span>
            </span>
            <span className="text-sm text-bronze-texto">Ver a lista ›</span>
          </a>
        )}

        <CompartilharWhatsApp
          caminho={
            localizacao.codigo_ibge
              ? `/representantes?municipio=${localizacao.codigo_ibge}`
              : `/representantes?uf=${localizacao.uf}`
          }
          texto={`Veja quem representa ${lugar} no Congresso e para onde foi o dinheiro da cidade:`}
        />

        <AvisoSegundoTurno
          uf={localizacao.uf}
          href={
            localizacao.cep
              ? `/segundo-turno?cep=${localizacao.cep}`
              : localizacao.codigo_ibge
                ? `/segundo-turno?municipio=${localizacao.codigo_ibge}`
                : `/segundo-turno?uf=${localizacao.uf}`
          }
        />
      </div>

      {federal && !federal.sem_dados && federalUf && (
        <section aria-labelledby="federal-titulo" className="flex flex-col gap-2">
          <h2 id="federal-titulo" className="text-2xl">
            Quanto a União arrecadou e repassou em {nomeEstado}
          </h2>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-muted-foreground">Arrecadado em {federal.ano}</dt>
              <dd className="numero text-2xl">
                {federalUf.arrecadacao != null ? formatarReaisCompacto(federalUf.arrecadacao) : "sem dado"}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Repassado em {federal.ano}</dt>
              <dd className="numero text-2xl">
                {federalUf.repasse != null ? formatarReaisCompacto(federalUf.repasse) : "sem dado"}
              </dd>
            </div>
          </dl>
          <div className="flex flex-wrap gap-x-5">
            <Link
              href={`/impostos-e-repasses/${localizacao.uf}`}
              className="alvo-link text-sm font-medium text-primary underline underline-offset-4"
            >
              Ver {nomeEstado} no mapa
            </Link>
            {localizacao.codigo_ibge && cidade && (
              <Link
                href={`/impostos-e-repasses/${localizacao.uf}/${localizacao.codigo_ibge}`}
                className="alvo-link text-sm font-medium text-primary underline underline-offset-4"
              >
                Ver {cidade} no mapa
              </Link>
            )}
          </div>
          <FonteRodape
            fonte={federal.fontes[0]?.nome ?? "Tesouro Nacional e Receita Federal"}
            url={federal.fontes[0]?.url}
            atualizadoEm={federal.fontes.map((f) => f.atualizado_em).filter((d): d is string => Boolean(d)).sort()[0] ?? null}
          />
        </section>
      )}

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
      <div className="flex flex-col gap-1">
        <Link
          href={`/projetos?esfera=federal&votacao=com&uf=${localizacao.uf}`}
          className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
        >
          Veja como votaram em projetos do Congresso (com quem representa {nomeEstado})
        </Link>
        <Link
          href={`/projetos?uf=${localizacao.uf}`}
          className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
        >
          Projetos e votações da assembleia e das câmaras de {nomeEstado}
        </Link>
      </div>

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

/** Quantos rostos aparecem no painel de cada prédio; a lista inteira fica na gaveta. */
const ROSTOS = 6;

const AVISO_EXECUTIVO = "Mudanças depois da eleição (renúncia, cassação, posse do vice) ainda não aparecem aqui.";

function pessoaChapa(c: Chapa): PessoaPredio {
  const vice = c.vice ? `Vice: ${c.vice.nome_urna}${c.vice.partido ? ` (${c.vice.partido})` : ""}` : null;
  return {
    chave: `chapa-${c.titular.id}`,
    nome: c.titular.nome_urna,
    partido: c.titular.partido,
    detalhe: [`${c.cargo} · eleição de ${c.ano_eleicao}`, vice].filter(Boolean).join(" · "),
    foto: c.titular.foto ? urlFotoDe(c.titular) : null,
    href: `/eleito/${c.titular.id}`,
  };
}

function pessoasParlamentares(lista: ParlamentarResumo[]): PessoaPredio[] {
  return lista.slice(0, ROSTOS).map((p) => ({
    chave: `p-${p.id}`,
    nome: p.nome_parlamentar,
    partido: p.partido,
    detalhe: null,
    foto: p.foto_url,
    href: `/parlamentar/${p.id}`,
  }));
}

/** Câmara municipal ou assembleia, segundo a própria casa (SAPL). */
function pessoasDaCasa(dados: Camara, rota: "vereador" | "deputado-estadual"): PessoaPredio[] {
  return dados.itens.slice(0, ROSTOS).map((v) => ({
    chave: `v-${v.id}`,
    nome: v.nome,
    partido: v.partido,
    detalhe: v.titular ? null : "suplente",
    foto: v.foto_tse && v.candidatura_id ? urlFotoTse(v.candidatura_id) : v.foto_url,
    href: `/${rota}/${v.id}`,
  }));
}

/** Eleitos do TSE, quando a casa ainda não tem os dados dela carregados. */
function pessoasDoTse(dados: ListaEleitos): PessoaPredio[] {
  return dados.itens.slice(0, ROSTOS).map((e) => ({
    chave: `e-${e.id}`,
    nome: e.nome_urna,
    partido: e.partido,
    detalhe: null,
    foto: e.foto ? urlFotoDe(e) : null,
    href: `/eleito/${e.id}`,
  }));
}

function montarPredios({
  uf,
  nomeEstado,
  cidade,
  nomeAssembleia,
  executivo,
  senadores,
  deputados,
  atualizadoCongresso,
  assembleia,
  estaduais,
  camara,
  vereadores,
}: {
  uf: string;
  nomeEstado: string;
  /** Nulo na busca só por estado e no DF (que não tem prefeitura nem câmara municipal). */
  cidade: string | null;
  nomeAssembleia: string;
  executivo: Executivo | null;
  senadores: ParlamentarResumo[];
  deputados: ParlamentarResumo[];
  atualizadoCongresso: string | null;
  assembleia: Camara | null;
  estaduais: ListaEleitos | null;
  camara: Camara | null;
  vereadores: ListaEleitos | null;
}): PredioDados[] {
  const eDF = uf === "DF";
  const fonteExecutivo = executivo
    ? { nome: executivo.fonte_nome, url: executivo.fonte_url, atualizadoEm: executivo.atualizado_em }
    : null;
  const fonteCongresso = { nome: "Dados Abertos da Câmara e do Senado", atualizadoEm: atualizadoCongresso };
  const base = { aviso: null, extra: null };

  const exec = (
    id: PredioId,
    chapa: Chapa | null | undefined,
    p: Pick<PredioDados, "nivel" | "nome" | "oficial" | "faz" | "fazOficial" | "rotulo" | "sub" | "tituloPessoas">,
  ): PredioDados => ({
    ...base,
    ...p,
    id,
    total: chapa ? 1 : 0,
    pessoas: chapa ? [pessoaChapa(chapa)] : [],
    destino: "executivo",
    aviso: AVISO_EXECUTIVO,
    fonte: fonteExecutivo,
  });

  const lista: PredioDados[] = [
    exec("planalto", executivo?.presidente, {
      nivel: "País · Brasília",
      nome: "Palácio do Planalto",
      oficial: "Poder Executivo federal",
      faz: "O presidente comanda o governo do país: dirige os ministérios e cuida do dinheiro e dos serviços nacionais, como o INSS.",
      fazOficial: "Chefia do Poder Executivo da União",
      rotulo: "Palácio do Planalto",
      sub: "1 presidente",
      tituloPessoas: "Quem ocupa o cargo",
    }),
    {
      ...base,
      id: "senado",
      nivel: "País · Brasília",
      nome: "Senado Federal",
      oficial: "Casa legislativa da União",
      faz: "Os senadores votam as leis do país e analisam o que o governo faz. Cada estado tem 3.",
      fazOficial: "Senadores",
      rotulo: "Senado",
      sub: contagem(senadores.length, "senador", "senadores"),
      total: senadores.length,
      tituloPessoas: `Senadores de ${nomeEstado} (${senadores.length})`,
      pessoas: pessoasParlamentares(senadores),
      destino: "senado",
      fonte: fonteCongresso,
    },
    {
      ...base,
      id: "camara",
      nivel: "País · Brasília",
      nome: "Câmara dos Deputados",
      oficial: "Casa legislativa da União",
      faz: `Os deputados federais também votam as leis do país. ${nomeEstado} tem ${deputados.length} deles.`,
      fazOficial: "Deputados federais",
      rotulo: "Câmara",
      sub: contagem(deputados.length, "deputado", "deputados"),
      total: deputados.length,
      tituloPessoas: `Deputados federais de ${nomeEstado} (${deputados.length})`,
      pessoas: pessoasParlamentares(deputados),
      destino: "deputados",
      fonte: fonteCongresso,
    },
    exec("governo", executivo?.governador, {
      nivel: `Estado · ${nomeEstado}`,
      nome: `Governo ${doEstado(uf)}`,
      oficial: eDF ? "Poder Executivo do Distrito Federal" : "Poder Executivo estadual",
      faz: eDF
        ? "O governador comanda o Distrito Federal, que reúne tarefas de estado e de cidade: segurança, hospitais e escolas."
        : "O governador comanda o estado: dirige a segurança, os hospitais e as escolas estaduais.",
      fazOficial: eDF ? "Chefia do Poder Executivo distrital" : "Chefia do Poder Executivo estadual",
      rotulo: eDF ? "Governo do DF" : "Governo do estado",
      sub: "1 governador",
      tituloPessoas: "Quem ocupa o cargo",
    }),
  ];

  const nAssembleia = assembleia?.itens.length ?? estaduais?.itens.length ?? 0;
  lista.push({
    ...base,
    id: "assembleia",
    nivel: `Estado · ${nomeEstado}`,
    nome: eDF ? "Câmara Legislativa" : "Assembleia Legislativa",
    oficial: eDF ? "Câmara Legislativa do Distrito Federal" : `Assembleia Legislativa ${doEstado(uf)}`,
    faz: `Os deputados ${eDF ? "distritais" : "estaduais"} votam as leis ${eDF ? "do Distrito Federal" : "do estado"} e acompanham o que o governador faz.`,
    fazOficial: eDF ? "Deputados distritais" : "Deputados estaduais",
    rotulo: nomeAssembleia,
    sub: nAssembleia > 0 ? contagem(nAssembleia, "deputado", "deputados") : "sem dados ainda",
    total: nAssembleia,
    tituloPessoas: `${eDF ? "Deputados distritais" : "Deputados estaduais"} (${nAssembleia})`,
    pessoas: assembleia
      ? pessoasDaCasa(assembleia, "deputado-estadual")
      : estaduais
        ? pessoasDoTse(estaduais)
        : [],
    destino: nAssembleia > 0 ? (assembleia ? "assembleia" : "estaduais") : null,
    aviso:
      !assembleia && estaduais && nAssembleia > 0
        ? `Esta casa ainda não tem presença e projetos carregados. Aqui aparecem só os eleitos de ${estaduais.ano_eleicao}, pelo TSE.`
        : null,
    fonte: assembleia
      ? { nome: assembleia.fonte_nome, url: assembleia.fonte_url, atualizadoEm: assembleia.atualizado_em }
      : estaduais
        ? { nome: estaduais.fonte_nome, url: estaduais.fonte_url, atualizadoEm: estaduais.atualizado_em }
        : null,
  });

  if (cidade) {
    const nVereadores = camara?.itens.length ?? vereadores?.itens.length ?? 0;
    lista.push(
      exec("prefeitura", executivo?.prefeito, {
        nivel: `Cidade · ${cidade}`,
        nome: `Prefeitura de ${cidade}`,
        oficial: "Poder Executivo municipal",
        faz: "O prefeito cuida do dia a dia da cidade: ruas, postos de saúde, escolas municipais e coleta de lixo.",
        fazOficial: "Chefia do Poder Executivo municipal",
        rotulo: "Prefeitura",
        sub: "1 prefeito",
        tituloPessoas: "Quem ocupa o cargo",
      }),
      {
        ...base,
        id: "camaramun",
        nivel: `Cidade · ${cidade}`,
        nome: `Câmara de Vereadores de ${cidade}`,
        oficial: "Câmara Municipal",
        faz: "Os vereadores votam as leis da cidade e fiscalizam o prefeito.",
        fazOficial: "Vereadores",
        rotulo: "Câmara de Vereadores",
        sub: nVereadores > 0 ? contagem(nVereadores, "vereador", "vereadores") : "sem dados ainda",
        total: nVereadores,
        tituloPessoas: `Vereadores (${nVereadores})`,
        pessoas: camara ? pessoasDaCasa(camara, "vereador") : vereadores ? pessoasDoTse(vereadores) : [],
        destino: nVereadores > 0 ? (camara ? "camara" : "vereadores") : null,
        aviso:
          !camara && vereadores && nVereadores > 0
            ? `${cidade} ainda não tem os dados da câmara municipal (presença e votações) carregados. Aqui aparecem só os eleitos de ${vereadores.ano_eleicao}, pelo TSE.`
            : null,
        fonte: camara
          ? { nome: camara.fonte_nome, url: camara.fonte_url, atualizadoEm: camara.atualizado_em }
          : vereadores
            ? { nome: vereadores.fonte_nome, url: vereadores.fonte_url, atualizadoEm: vereadores.atualizado_em }
            : null,
      },
    );
  }
  return lista;
}
