import type { Metadata } from "next";
import Link from "next/link";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { Revelacao } from "@/components/revelacao";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { Migalhas } from "@/components/ui/migalhas";
import { AcompanharPorFeed, CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { SeloEleitoFuturo } from "@/components/eleito-futuro";
import { CarreiraSecao } from "@/components/carreira-secao";
import { SancoesSecao, TEXTO_REGISTRO } from "@/components/sancoes-secao";
import { ServicoFederalSecao } from "@/components/servico-federal-secao";
import { CandidaturaSecao } from "@/components/candidatura-secao";
import { QuemESecao } from "@/components/dados-pessoais";
import { ComissoesSecao } from "@/components/comissoes-secao";
import { DestinoEmendasSecao } from "@/components/destino-emendas-secao";
import { EmendasRelatorSecao } from "@/components/emendas-relator-secao";
import { GastosSecao } from "@/components/gastos-secao";
import { ContratosSocioSecao } from "@/components/contratos-socio-secao";
import { LinhaDoTempoSecao } from "@/components/linha-do-tempo-secao";
import { Foto } from "@/components/parlamentar-card";
import { PresencaSecao } from "@/components/presenca-secao";
import { ProjetosSecao } from "@/components/projetos-secao";
import { RemuneracaoSecao } from "@/components/remuneracao-secao";
import { ResumoPerfil } from "@/components/resumo-perfil";
import { TemasSecao } from "@/components/temas-secao";
import { VotosSecao } from "@/components/votos-secao";
import { VotosTemaSecao } from "@/components/votos-tema-secao";
import {
  getDestinoEmendas,
  getEmendasRelator,
  getGastos,
  getParlamentar,
  getPresenca,
  getCandidatura,
  getLinhaDoTempo,
  getProjetos,
  getTemas,
  getVotos,
  getVotosPorTema,
  getSancoes,
  getVotosComissoes,
  type Casa,
  type ParlamentarDetalhe,
  type Presenca,
  type Votos,
} from "@/lib/api";
import { CASA_CURTA, FONTE_CASA, NOME_CASA } from "@/lib/formato";

export async function generateMetadata({
  params,
}: PageProps<"/parlamentar/[id]">): Promise<Metadata> {
  const { id } = await params;
  const resultado = await getParlamentar(id);
  if (!resultado.ok) return { title: "Parlamentar" };
  const p = resultado.dados;
  const descricao = `Gastos do gabinete, presença em votações e projetos de lei de ${p.nome_parlamentar} (${[p.partido, p.uf].filter(Boolean).join("-")}), com dados oficiais e link para a fonte.`;
  return {
    title: p.nome_parlamentar,
    description: descricao,
    openGraph: { title: `${p.nome_parlamentar} · ${NOME_CASA[p.casa]}`, description: descricao },
  };
}

export default function ParlamentarPage({
  params,
  searchParams,
}: PageProps<"/parlamentar/[id]">) {
  return (
    <Revelacao fallback={<Carregando />}>
      {Promise.all([params, searchParams]).then(([{ id }, sp]) => {
        const texto = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);
        return (
          <Perfil
            id={id}
            ano={texto(sp.ano)}
            tema={texto(sp.tema)}
            paginaVotos={texto(sp.pagina_votos)}
            paginaComissoes={texto(sp.pagina_comissoes)}
          />
        );
      })}
    </Revelacao>
  );
}

async function Perfil({
  id,
  ano,
  tema,
  paginaVotos,
  paginaComissoes,
}: {
  id: string;
  ano?: string;
  tema?: string;
  paginaVotos?: string;
  paginaComissoes?: string;
}) {
  const [resultado, gastos, projetos, presenca, temas, votos, votosTema, candidatura, comissoes, [linha, sancoes], destino, relator] =
    await Promise.all([
      getParlamentar(id),
      getGastos(id, ano),
      getProjetos(id),
      getPresenca(id, ano),
      getTemas(id),
      getVotos(id, { ano, tema, pagina: paginaVotos }),
      getVotosPorTema(id, ano),
      getCandidatura(id),
      getVotosComissoes(id, paginaComissoes),
      // As sanções dependem da pessoa; a SancoesSecao repete a chamada e o fetch é memoizado.
      getLinhaDoTempo("parlamentar", id).then(
        async (l) => [l, l.ok ? await getSancoes(l.dados.pessoa_id) : null] as const,
      ),
      getDestinoEmendas(id),
      getEmendasRelator(id),
    ]);
  if (!resultado.ok) {
    if (resultado.status === 404 || resultado.status === 422) notFound();
    return <AvisoErro titulo="Não deu para carregar agora" mensagem={resultado.mensagem} />;
  }
  const p = resultado.dados;
  const pessoaId = linha.ok ? linha.dados.pessoa_id : null;

  // Cada seção aparece UMA vez, dentro de uma aba; o cartão do topo abre a mesma seção em gaveta.
  const abas: AbaDetalhe[] = [
    {
      id: "dinheiro",
      rotulo: "Dinheiro",
      secoes: [
        {
          id: "gastos",
          titulo: "Gastos do gabinete",
          conteudo: gastos.ok ? (
            <GastosSecao gastos={gastos.dados} casa={p.casa} parlamentarId={p.id} />
          ) : (
            <p className="text-sm text-muted-foreground">Gastos do gabinete: {gastos.mensagem}</p>
          ),
        },
        { id: "remuneracao", titulo: "Salário", conteudo: <RemuneracaoSecao remuneracao={p.remuneracao} /> },
        {
          id: "destino-emendas",
          titulo: "Emendas",
          conteudo: destino.ok && <DestinoEmendasSecao dados={destino.dados} />,
        },
        {
          id: "emendas-relator",
          titulo: "Emendas de relator",
          conteudo: relator.ok && <EmendasRelatorSecao dados={relator.dados} />,
        },
        {
          id: "contratos-socio",
          titulo: "Contratos de empresas de que é sócio",
          conteudo: pessoaId !== null && <ContratosSocioSecao pessoaId={pessoaId} />,
        },
      ],
    },
    {
      id: "votacoes",
      rotulo: "Votações",
      secoes: [
        {
          id: "presenca",
          titulo: "Presença em votações",
          conteudo: presenca.ok && <PresencaSecao presenca={presenca.dados} casa={p.casa} />,
        },
        {
          id: "votos",
          titulo: "Como votou",
          conteudo: votos.ok && <VotosSecao dados={votos.dados} casa={p.casa} parlamentarId={p.id} />,
        },
        {
          id: "votos-tema",
          titulo: "Votações por tema",
          conteudo: votosTema.ok && votosTema.dados.temas.length > 0 && (
            <VotosTemaSecao dados={votosTema.dados} casa={p.casa} parlamentarId={p.id} />
          ),
        },
        {
          id: "comissoes",
          titulo: "Votações em comissões",
          conteudo: comissoes.ok && <ComissoesSecao dados={comissoes.dados} parlamentarId={p.id} />,
        },
      ],
    },
    {
      id: "projetos",
      rotulo: "Projetos",
      secoes: [
        {
          id: "projetos",
          titulo: "Projetos de lei",
          conteudo: projetos.ok && <ProjetosSecao projetos={projetos.dados} casa={p.casa} />,
        },
        { id: "temas", titulo: "Temas", conteudo: temas.ok && <TemasSecao dados={temas.dados} casa={p.casa} /> },
      ],
    },
    {
      id: "ficha",
      rotulo: "Ficha",
      secoes: [
        {
          id: "quem-e",
          titulo: "Quem é",
          conteudo: candidatura.ok && (
            <QuemESecao pessoais={candidatura.dados.pessoais} votos={candidatura.dados.votos} />
          ),
        },
        {
          id: "carreira",
          titulo: "Eleições disputadas",
          conteudo: pessoaId !== null && <CarreiraSecao pessoaId={pessoaId} />,
        },
        {
          id: "candidatura",
          titulo: "Candidatura e bens",
          conteudo: candidatura.ok && <CandidaturaSecao dados={candidatura.dados} />,
        },
        {
          id: "linha-do-tempo",
          titulo: "Linha do tempo",
          conteudo: linha.ok && <LinhaDoTempoSecao dados={linha.dados} />,
        },
        {
          id: "servico-federal",
          titulo: "Trabalho no governo federal",
          conteudo: pessoaId !== null && <ServicoFederalSecao pessoaId={pessoaId} />,
        },
        { id: "contato", titulo: "Contato do gabinete", conteudo: <Contato p={p} /> },
      ],
    },
    {
      id: "justica",
      rotulo: "Justiça",
      secoes: [
        {
          id: "sancoes",
          titulo: "Punições e contas reprovadas",
          conteudo: pessoaId !== null && <SancoesSecao pessoaId={pessoaId} explicacao="#entender-registro" />,
        },
      ],
    },
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <Migalhas
          itens={[
            { rotulo: "Início", href: "/" },
            { rotulo: "Parlamentares", href: "/parlamentares" },
            { rotulo: p.nome_parlamentar },
          ]}
        />
        <header className="flex items-start gap-4">
          <Foto parlamentar={p} largura={96} prioridade />
          <div className="flex min-w-0 flex-col gap-1">
            <p className="sobretitulo">{p.casa === "senado" ? "Senador" : "Deputado federal"}</p>
            <h1 className="titulo-pagina">{p.nome_parlamentar}</h1>
            {p.nome_civil && p.nome_civil !== p.nome_parlamentar && (
              <p className="text-sm text-muted-foreground">{p.nome_civil}</p>
            )}
            <p className="text-muted-foreground">
              {NOME_CASA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
            </p>
            {!p.em_exercicio && <p className="text-sm font-medium">Fora de exercício no momento.</p>}
          </div>
        </header>

        {candidatura.ok && candidatura.dados.eleito_2026 && (
          <SeloEleitoFuturo eleito={candidatura.dados.eleito_2026} atualizadoEm={candidatura.dados.atualizado_em} />
        )}

        <ResumoPerfil
          nome={p.nome_parlamentar}
          casa={p.casa}
          gastos={gastos.ok ? gastos.dados : undefined}
          presenca={presenca.ok ? presenca.dados : undefined}
          projetos={projetos.ok ? projetos.dados : undefined}
          votos={votos.ok ? votos.dados : undefined}
          bens={candidatura.ok ? candidatura.dados.bens : undefined}
          sancoes={sancoes?.ok ? sancoes.dados : undefined}
          subsidio={p.remuneracao.subsidio_mensal}
        />
        <p className="text-sm text-muted-foreground">Toque num número para ver o detalhe, com a fonte e a data.</p>

        <div className="flex flex-wrap gap-2">
          <Link href={`/comparar?a=${p.id}`} className="botao-linha">
            Comparar com outro parlamentar
          </Link>
        </div>
        {p.uf && (
          <Link
            href={`/dinheiro-federal/${p.uf}`}
            className="alvo-link self-start text-sm text-muted-foreground underline underline-offset-4"
          >
            {p.uf} no mapa do dinheiro federal
          </Link>
        )}
        <CompartilharWhatsApp
          caminho={`/parlamentar/${p.id}`}
          texto={`Veja os gastos, a presença e os projetos de ${p.nome_parlamentar} (${NOME_CASA[p.casa]}), com dados oficiais:`}
        />
        {linha.ok && <AcompanharPorFeed pessoaId={linha.dados.pessoa_id} />}
      </div>

      <PerguntasPerfil
        casa={p.casa}
        nome={p.nome_parlamentar}
        presenca={presenca.ok ? presenca.dados : undefined}
        votos={votos.ok ? votos.dados : undefined}
        temSancoes={pessoaId !== null}
      />

      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />

      <FonteRodape fonte={FONTE_CASA[p.casa]} url={p.fonte_url} atualizadoEm={p.atualizado_em} />
    </article>
  );
}

function Contato({ p }: { p: ParlamentarDetalhe }) {
  if (!p.email && !p.telefone && !p.pagina_url) return null;
  return (
    <section aria-labelledby="contato-titulo" className="flex flex-col gap-2">
      <h2 id="contato-titulo" className="text-2xl">
        Contato do gabinete
      </h2>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {p.email && (
          <>
            <dt className="text-muted-foreground">E-mail</dt>
            <dd className="break-all">
              <a href={`mailto:${p.email}`} className="underline underline-offset-2">
                {p.email}
              </a>
            </dd>
          </>
        )}
        {p.telefone && (
          <>
            <dt className="text-muted-foreground">Telefone</dt>
            <dd>
              <a href={`tel:${p.telefone.replace(/\D/g, "")}`} className="underline underline-offset-2">
                {p.telefone}
              </a>
            </dd>
          </>
        )}
        {p.pagina_url && (
          <>
            <dt className="text-muted-foreground">Página oficial</dt>
            <dd>
              <a href={p.pagina_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                {NOME_CASA[p.casa]}
              </a>
            </dd>
          </>
        )}
      </dl>
      <FonteRodape fonte={FONTE_CASA[p.casa]} url={p.fonte_url} atualizadoEm={p.atualizado_em} />
    </section>
  );
}

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

/** "Para entender os números": só o que tem nuance. Os textos de método que ficavam espalhados
 * pelas seções moram aqui; as seções trazem um link para a pergunta. */
function PerguntasPerfil({
  casa,
  nome,
  presenca,
  votos,
  temSancoes,
}: {
  casa: Casa;
  nome: string;
  presenca?: Presenca;
  votos?: Votos;
  temSancoes: boolean;
}) {
  const colegas = casa === "camara" ? "deputados" : "senadores";
  const umColega = casa === "camara" ? "deputado" : "senador";
  const mediaDa = `Média ${casa === "camara" ? "da" : "do"} ${CASA_CURTA[casa]}`;
  const governo = votos?.governo && votos.governo.total > 0 ? votos.governo : null;
  return (
    <ListaPerguntas titulo="Para entender os números">
      {presenca && presenca.total_votacoes > 0 && (
        <Pergunta
          id="entender-presenca"
          pergunta="O que entra na conta da presença?"
          resposta={
            presenca.ausencia_detalhada
              ? "Votos, faltas e ausências justificadas, como o Senado registra"
              : "Todas as votações do ano; só o voto registrado conta como presença"
          }
        >
          <p>
            Em {presenca.ano}, foram {presenca.total_votacoes} votações nominais no Plenário. {nome} registrou voto
            em {presenca.votou}.
          </p>
          <ComposicaoPresenca presenca={presenca} />
          <p className="text-muted-foreground">
            {presenca.ausencia_detalhada
              ? "Ausência justificada inclui missão oficial, licença e atividade parlamentar fora do Plenário, conforme o registro do Senado."
              : "A Câmara publica apenas quem registrou voto. Em votação secreta, quem aparece na lista conta como quem votou, mesmo sem o voto público. Ausências por licença ou missão oficial não aparecem separadas nestes dados; por isso o número mostra só o que a Câmara registrou."}
          </p>
          <FonteRodape fonte={presenca.fonte_nome} url={presenca.fonte_url} atualizadoEm={presenca.atualizado_em} />
        </Pergunta>
      )}
      {votos && (
        <Pergunta
          id="entender-governo"
          pergunta="O que quer dizer “votou como o Governo orientou”?"
          resposta="Antes de cada votação, o líder do Governo diz como a base deve votar"
        >
          <p>
            Contamos quantas vezes o voto foi igual a essa orientação. Contam só as votações em que deu voto (Sim,
            Não, Abstenção ou Obstrução), e só quando a liderança do Governo orientou Sim, Não ou Obstrução;
            votações liberadas ficam de fora.
          </p>
          {governo && governo.percentual !== null && votos.media_governo !== null && (
            <BarraComparacao
              pessoa={{ rotulo: nome, valor: governo.percentual }}
              media={{ rotulo: mediaDa, valor: votos.media_governo }}
              formato="percentual"
              escala={100}
            />
          )}
          {governo && governo.total < 20 && (
            <p>
              Em {votos.ano}, {governo.total === 1 ? "foi 1 voto contado" : `foram ${governo.total} votos contados`}.
              Com poucos votos, cada um muda muito a porcentagem.
            </p>
          )}
          {casa === "senado" && (
            <p>
              No Senado, a maioria das votações é secreta ou não tem orientação registrada, por isso os totais são
              pequenos.
            </p>
          )}
          <p className="text-muted-foreground">
            A maioria do partido, que aparece em cada votação, é como votaram os outros {colegas} do mesmo partido
            naquele dia.{" "}
            <Link href="/sobre-as-fontes" className="underline underline-offset-2">
              Como calculamos
            </Link>
          </p>
          <FonteRodape fonte={votos.fonte_nome} url={votos.fonte_url} atualizadoEm={votos.atualizado_em} />
        </Pergunta>
      )}
      {temSancoes && (
        <Pergunta
          id="entender-registro"
          pergunta="O que é um registro na CGU e no TCU?"
          resposta="Uma punição ou decisão que um órgão público registrou"
        >
          <p>
            A Controladoria-Geral da União (CGU) mantém os cadastros de quem foi punido por órgãos públicos{" "}
            <span className="text-muted-foreground">(CEIS, CNEP e CEAF)</span>. O Tribunal de Contas da União (TCU)
            publica quem teve as contas julgadas irregulares ou foi proibido de exercer cargo público.
          </p>
          <p>{TEXTO_REGISTRO}</p>
          <p>
            <a href="#ver-sancoes" className="alvo-link underline underline-offset-2">
              Ver os registros desta pessoa
            </a>
          </p>
        </Pergunta>
      )}
      <Pergunta
        id="entender-media"
        pergunta="Como é calculada a média?"
        resposta={`É a média entre os ${colegas} em exercício`}
      >
        <p>
          Cada número vem ao lado da média {casa === "camara" ? "da Câmara" : "do Senado"}: somamos o valor de cada{" "}
          {umColega} em exercício e dividimos pelo número deles. Quem não tem registro no período entra com zero. Nos
          gráficos, bronze é sempre esta pessoa e cinza é sempre a média.
        </p>
        <p className="text-muted-foreground">
          A média dá o contexto; não é meta nem nota. Parte do trabalho de um parlamentar acontece fora do que estes
          dados registram.
        </p>
      </Pergunta>
    </ListaPerguntas>
  );
}

/** Uma barra só, dividida pelo que aconteceu nas votações; os números ficam na legenda. */
function ComposicaoPresenca({ presenca: p }: { presenca: Presenca }) {
  const partes = [
    { rotulo: "Votou", valor: p.votou, cor: "bg-bronze" },
    { rotulo: "Presente, sem registrar voto", valor: p.presente_sem_voto, cor: "bg-chart-2" },
    { rotulo: "Ausência justificada", valor: p.ausencia_detalhada ? p.justificada : 0, cor: "bg-chart-3" },
    {
      rotulo: p.ausencia_detalhada ? "Não compareceu" : "Sem registro de voto",
      valor: p.nao_compareceu,
      cor: "bg-muted",
    },
  ].filter((x) => x.valor > 0);
  return (
    <div className="flex flex-col gap-2">
      <div aria-hidden className="flex h-3 w-full gap-px overflow-hidden rounded-[2px] ring-1 ring-border">
        {partes.map((x) => (
          <span key={x.rotulo} className={`${x.cor} h-full`} style={{ flexGrow: x.valor }} />
        ))}
      </div>
      <ul className="flex flex-col gap-1">
        {partes.map((x) => (
          <li key={x.rotulo} className="flex items-center gap-2">
            <span aria-hidden className={`${x.cor} size-3 shrink-0 rounded-[2px] ring-1 ring-border`} />
            <span className="min-w-0 flex-1">{x.rotulo}</span>
            <span className="tabular-nums">
              {x.valor} ({PCT.format((x.valor / p.total_votacoes) * 100)}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Carregando() {
  return (
    <div className="flex flex-col gap-[var(--esp-10)]" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando perfil…</span>
      <div aria-hidden className="flex gap-4">
        <div className="h-32 w-24 animate-pulse rounded-[2px] bg-muted motion-reduce:animate-none" />
        <div className="flex flex-1 flex-col gap-2">
          <div className="h-7 w-2/3 animate-pulse rounded-[2px] bg-muted motion-reduce:animate-none" />
          <div className="h-5 w-1/2 animate-pulse rounded-[2px] bg-muted motion-reduce:animate-none" />
        </div>
      </div>
      <EsqueletoSecao rotulo="Carregando seções do perfil…" secoes={2} />
    </div>
  );
}
