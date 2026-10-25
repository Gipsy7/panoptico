import Link from "next/link";
import { TextoLongo } from "@/components/ui/texto-longo";
import { notFound } from "next/navigation";

import { GastosLocaisSecao, PresencaLocalSecao, VotacoesLocaisSecao, casaNaMatriz } from "@/components/atividade-local";
import { AvisoErro } from "@/components/aviso-erro";
import { FotoVereador } from "@/components/camara-secao";
import { CarreiraSecao } from "@/components/carreira-secao";
import { EmendasDoDeputadoEstadual } from "@/components/emendas-estaduais";
import { SancoesSecao, TEXTO_REGISTRO } from "@/components/sancoes-secao";
import { ServicoFederalSecao } from "@/components/servico-federal-secao";
import { CandidaturaSecao } from "@/components/candidatura-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { QuemESecao } from "@/components/dados-pessoais";
import { SeloEleitoFuturo } from "@/components/eleito-futuro";
import { FonteRodape } from "@/components/fonte-rodape";
import { PorQueFalta } from "@/components/por-que-falta";
import { ContratosSocioSecao } from "@/components/contratos-socio-secao";
import { LinhaDoTempoSecao } from "@/components/linha-do-tempo-secao";
import { AbasDetalhe, type AbaDetalhe } from "@/components/painel/abas-detalhe";
import { formatarNumero } from "@/components/painel/barra-comparacao";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { getEleito, getEmendasDeputadoEstadual, getLinhaDoTempo, getSancoes, getVereador, getVotacoesLocais, type VereadorDetalhe } from "@/lib/api";
import { formatarData, formatarGastos, formatarReais, formatarReaisCompacto } from "@/lib/formato";

/** Perfil de quem está no cargo numa câmara ou assembleia, com os dados da própria casa. */
export async function PerfilMandatoLocal({ id, paginaVotos }: { id: string; paginaVotos?: string }) {
  const resultado = await getVereador(id);
  if (!resultado.ok) {
    if (resultado.status === 404) notFound();
    return <AvisoErro titulo="Não deu para carregar" mensagem={resultado.mensagem} />;
  }
  const v = resultado.dados;
  const camara = v.casa === "camara";
  const cargo = camara ? "Vereador" : v.uf === "DF" ? "Deputado distrital" : "Deputado estadual";
  const nomeCasa = camara ? "câmara" : "assembleia";
  const rota = `/${camara ? "vereador" : "deputado-estadual"}/${v.id}`;
  const [eleicao, votacoes, linha, emendasEstaduaisR] = await Promise.all([
    v.candidatura_id ? getEleito(String(v.candidatura_id)) : null,
    getVotacoesLocais(String(v.id), paginaVotos),
    getLinhaDoTempo(camara ? "vereador" : "deputado_estadual", String(v.id)),
    // Só onde a API tem a fonte (hoje SC); nas outras UFs devolve 404 e nada novo aparece.
    camara ? null : getEmendasDeputadoEstadual(v.id),
  ]);
  const emendasEstaduais = emendasEstaduaisR?.ok ? emendasEstaduaisR.dados : null;
  const pessoaId = linha.ok ? linha.dados.pessoa_id : null;
  const sancoes = pessoaId !== null ? await getSancoes(pessoaId) : null;
  const dEleicao = eleicao?.ok ? eleicao.dados : null;
  const mediaCasa = `Média da ${nomeCasa}`;
  const comRegistroDeVoto = votacoes.ok && votacoes.dados.casa_registra;
  const faltam = [
    !v.gastos && "gastos do gabinete",
    !v.presenca && "presença nas sessões",
    votacoes.ok && !votacoes.dados.casa_registra && "o voto de cada parlamentar",
  ].filter(Boolean) as string[];

  const abas: AbaDetalhe[] = [
    {
      id: "dinheiro",
      rotulo: "Dinheiro",
      secoes: [
        { id: "gastos", titulo: "Gastos do gabinete", conteudo: <GastosLocaisSecao v={v} nomeCasa={nomeCasa} /> },
        {
          id: "emendas-estaduais",
          titulo: "Emendas ao orçamento do Estado",
          conteudo: emendasEstaduais && <EmendasDoDeputadoEstadual dados={emendasEstaduais} />,
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
        { id: "presenca", titulo: "Presença nas sessões", conteudo: <PresencaLocalSecao v={v} nomeCasa={nomeCasa} /> },
        {
          id: "votos",
          titulo: "Como votou",
          conteudo: votacoes.ok && <VotacoesLocaisSecao dados={votacoes.dados} nomeCasa={nomeCasa} caminho={rota} v={v} />,
        },
      ],
    },
    {
      id: "projetos",
      rotulo: "Projetos",
      secoes: [{ id: "proposicoes", titulo: "Projetos e proposições", conteudo: <ProjetosLocaisSecao v={v} nomeCasa={nomeCasa} /> }],
    },
    {
      id: "ficha",
      rotulo: "Ficha",
      secoes: [
        {
          id: "quem-e",
          titulo: "Quem é",
          conteudo: dEleicao && (
            <QuemESecao
              pessoais={dEleicao.pessoais}
              votos={dEleicao.votos != null ? { ano: dEleicao.ano_eleicao, total: dEleicao.votos } : null}
            />
          ),
        },
        {
          id: "carreira",
          titulo: "Eleições disputadas",
          conteudo: pessoaId !== null && <CarreiraSecao pessoaId={pessoaId} />,
        },
        { id: "candidatura", titulo: "Candidatura e bens", conteudo: dEleicao && <CandidaturaSecao dados={dEleicao} /> },
        {
          id: "candidatura-recente",
          titulo: v.eleicao_recente ? `Candidatura e bens de ${v.eleicao_recente.ano_eleicao}` : "Candidatura e bens",
          conteudo: v.eleicao_recente && (
            <CandidaturaSecao
              dados={v.eleicao_recente}
              idTitulo="tse-recente-titulo"
              titulo={`Eleição de ${v.eleicao_recente.ano_eleicao}`}
              posse={`a da eleição para o mandato que começa em ${v.eleicao_recente.ano_eleicao + 1}`}
            />
          ),
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
        { id: "contato", titulo: "Contato", conteudo: <ContatoLocal v={v} /> },
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
      <header className="flex items-start gap-4">
        <FotoVereador vereador={v} tamanho={72} />
        <div className="flex min-w-0 flex-col gap-1">
          <p className="sobretitulo">{cargo}</p>
          <h1 className="titulo-pagina">{v.nome}</h1>
          {v.nome_completo && v.nome_completo !== v.nome && (
            <p className="text-sm text-muted-foreground">{v.nome_completo}</p>
          )}
          <p className="flex flex-wrap gap-1">
            <span className="pilula">{cargo}</span>
            {v.partido && <span className="pilula">{v.partido}</span>}
            <span className="pilula">{v.titular ? "Titular" : "Suplente"}</span>
          </p>
          {(v.inicio || v.fim) && (
            <p className="text-sm text-muted-foreground">
              Mandato {v.inicio ? `de ${formatarData(v.inicio)}` : ""} {v.fim ? `até ${formatarData(v.fim)}` : ""}
            </p>
          )}
        </div>
      </header>

      {v.eleito_2026 && <SeloEleitoFuturo eleito={v.eleito_2026} atualizadoEm={v.atualizado_em} />}

      <GradeCartoes rotulo="Números principais">
        {v.presenca && v.presenca.sessoes > 0 && (
          <CartaoNumero
            destino="presenca"
            rotulo="Presença nas sessões, ano atual e anterior"
            valor={String(v.presenca.presencas)}
            complemento={`de ${v.presenca.sessoes}`}
            largo
            comparacao={
              v.presenca.media_casa !== null
                ? {
                    pessoa: { rotulo: v.nome, valor: (100 * v.presenca.presencas) / v.presenca.sessoes },
                    media: { rotulo: mediaCasa, valor: v.presenca.media_casa },
                    formato: "percentual",
                    escala: 100,
                  }
                : undefined
            }
          />
        )}
        {v.gastos && (
          <CartaoNumero
            destino="gastos"
            rotulo={`Verba do gabinete em ${v.gastos.ano}`}
            valor={v.gastos.total === 0 ? formatarGastos(0) : formatarReaisCompacto(v.gastos.total)}
            apoio={v.gastos.media_casa !== null ? `Média ${formatarReaisCompacto(v.gastos.media_casa)}` : undefined}
          />
        )}
        {emendasEstaduais && (
          <CartaoNumero
            destino="emendas-estaduais"
            rotulo="Emendas ao orçamento do Estado, pagas"
            valor={formatarReaisCompacto(emendasEstaduais.total_pago)}
            comparacao={
              emendasEstaduais.media_casa_pago !== null
                ? {
                    pessoa: { rotulo: v.nome, valor: emendasEstaduais.total_pago },
                    media: { rotulo: mediaCasa, valor: emendasEstaduais.media_casa_pago },
                    formato: "reais-compacto",
                  }
                : undefined
            }
          />
        )}
        {comRegistroDeVoto && votacoes.ok && (
          <CartaoNumero
            destino="votos"
            rotulo="Votações nominais, ano atual e anterior"
            valor={String(votacoes.dados.votou)}
            complemento={`de ${votacoes.dados.total}`}
            apoio="Em que registrou voto"
          />
        )}
        <CartaoNumero
          destino="proposicoes"
          rotulo="Projetos como autor ou coautor"
          valor={formatarNumero(v.projetos, "inteiro")}
          apoio={`${formatarNumero(v.proposicoes, "inteiro")} proposições no total`}
        />
        {v.eleicao_recente?.bens && (
          <CartaoNumero
            destino="candidatura-recente"
            rotulo={`Bens declarados em ${v.eleicao_recente.bens.candidatura.ano}`}
            valor={formatarReaisCompacto(v.eleicao_recente.bens.total)}
            apoio={
              v.eleicao_recente.bens.anterior
                ? `Em ${v.eleicao_recente.bens.anterior.candidatura.ano}: ${formatarReaisCompacto(v.eleicao_recente.bens.anterior.total)}`
                : "Valor informado ao TSE"
            }
          />
        )}
        {dEleicao?.bens && (
          <CartaoNumero
            destino="candidatura"
            rotulo={`Bens declarados em ${dEleicao.bens.candidatura.ano}`}
            valor={formatarReaisCompacto(dEleicao.bens.total)}
            apoio={
              dEleicao.bens.anterior
                ? `Em ${dEleicao.bens.anterior.candidatura.ano}: ${formatarReaisCompacto(dEleicao.bens.anterior.total)}`
                : "Valor informado ao TSE"
            }
          />
        )}
        {dEleicao?.votos != null && (
          <CartaoNumero
            destino="quem-e"
            rotulo={`Votos recebidos em ${dEleicao.ano_eleicao}`}
            valor={formatarNumero(dEleicao.votos, "inteiro")}
            apoio="Número informado pelo TSE"
          />
        )}
        {sancoes?.ok && (
          <CartaoNumero
            destino="sancoes"
            rotulo="Registros na CGU e no TCU"
            valor={sancoes.dados.itens.length === 0 ? "Nenhum" : String(sancoes.dados.itens.length)}
            apoio={sancoes.dados.atualizado_em ? `Consulta de ${formatarData(sancoes.dados.atualizado_em)}` : undefined}
          />
        )}
      </GradeCartoes>
      <p className="text-sm text-muted-foreground">Toque num número para ver o detalhe, com a fonte e a data.</p>

      <Link href={`/comparar/local?a=${v.id}`} className="botao-linha self-start">
        Comparar com outro {camara ? "vereador desta câmara" : "deputado desta assembleia"}
      </Link>

      <CompartilharWhatsApp
        caminho={rota}
        texto={
          v.gastos
            ? `${v.nome} (${cargo.toLowerCase()}) gastou ${formatarReais(v.gastos.total, true)} do gabinete em ${v.gastos.ano}, segundo a ${nomeCasa}. Veja o perfil com dados oficiais:`
            : `${v.nome} (${cargo.toLowerCase()}) tem ${v.projetos} projetos no ano atual e no anterior, segundo a ${nomeCasa}. Veja o perfil com dados oficiais:`
        }
      />

      <ListaPerguntas titulo="Para entender os números">
        <Pergunta
          id="entender-dados"
          pergunta={`De onde vêm os dados desta ${nomeCasa}?`}
          resposta={`Do que a própria ${nomeCasa} publica, do ano atual e do anterior`}
        >
          <p>
            Os números de gastos, presença, votos e projetos são os que a {nomeCasa} divulga em dados abertos, sobre o
            ano atual e o anterior. O Panóptico não corrige nem completa esses registros.
          </p>
          {faltam.length > 0 && (
            <p>
              Para esta {nomeCasa}, não há dados abertos de: {faltam.join(", ")}. Por isso esses números não aparecem,
              e isso não diz nada sobre a pessoa.{" "}
              {casaNaMatriz(v) && <PorQueFalta uf={v.uf} casa={casaNaMatriz(v)} />}
            </p>
          )}
          <FonteRodape fonte={v.fonte_nome} url={v.fonte_url} atualizadoEm={v.atualizado_em} />
        </Pergunta>
        {v.presenca && (
          <Pergunta
            id="entender-presenca"
            pergunta="O que entra na conta da presença?"
            resposta="As sessões plenárias com lista de presença lançada"
          >
            <p>
              Em {v.presenca.sessoes} sessões, {v.nome} aparece na lista de presença de {v.presenca.presencas}.
              Ausências justificadas (licença, missão oficial) não aparecem separadas nos dados da {nomeCasa}.
            </p>
            <p className="text-muted-foreground">
              Parte do trabalho de quem está no cargo acontece fora das sessões e não entra neste número.
            </p>
          </Pergunta>
        )}
        {(v.gastos?.media_casa != null || v.presenca?.media_casa != null) && (
          <Pergunta
            id="entender-media"
            pergunta="Como é calculada a média?"
            resposta={`É a média entre quem está no cargo na ${nomeCasa}`}
          >
            <p>
              Somamos o valor de cada parlamentar em exercício e dividimos pelo número deles. Quem não tem registro no
              período entra com zero. Nas barras, bronze é sempre esta pessoa e cinza é sempre a média.
            </p>
            <p className="text-muted-foreground">A média dá o contexto; não é meta nem nota.</p>
          </Pergunta>
        )}
        {pessoaId !== null && (
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
      </ListaPerguntas>

      <AbasDetalhe titulo="Tudo em detalhe" abas={abas} />

      <Link
        href={v.municipio_ibge ? `/representantes?municipio=${v.municipio_ibge}` : `/representantes?uf=${v.uf}`}
        className="self-start text-sm underline underline-offset-4"
      >
        {camara ? "Ver a câmara e os outros representantes da cidade" : "Ver a assembleia e os outros representantes do estado"}
      </Link>
    </article>
  );
}

/** Projetos e proposições como a casa publica; o contato fica na ficha. */
function ProjetosLocaisSecao({ v, nomeCasa }: { v: VereadorDetalhe; nomeCasa: string }) {
  return (
    <section aria-labelledby="atuacao-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="atuacao-titulo" className="text-2xl">
          Projetos e proposições
        </h2>
        <p className="text-xs text-muted-foreground">Ano atual e anterior, como a {nomeCasa} publica</p>
      </div>
      {v.proposicoes_por_tipo.length === 0 ? (
        <p className="text-muted-foreground">Nenhuma proposição como autor neste período.</p>
      ) : (
        <dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
          {v.proposicoes_por_tipo.map((p) => (
            <div key={p.tipo} className="flex items-baseline justify-between gap-4 border-b border-border py-2 text-sm">
              <dt className="text-muted-foreground">{p.tipo}</dt>
              <dd className="tabular-nums">{p.total}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-xs text-muted-foreground">
        Requerimentos e indicações são pedidos (de informação, de obra, de serviço); projetos podem virar lei. Conta
        como autor ou coautor.
      </p>
      {v.lista_projetos.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Projetos</h3>
          <ul className="lista-fios flex flex-col">
            {v.lista_projetos.map((p, i) => (
              <li key={i} className="flex flex-col gap-1 py-3">
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                  {p.tipo} {p.numero ? `nº ${p.numero}` : ""}/{p.ano}
                </a>
                <TextoLongo linhas={3}>{p.ementa}</TextoLongo>
                <p className="text-xs text-muted-foreground">
                  {p.data_apresentacao ? formatarData(p.data_apresentacao) : ""}
                  {p.em_tramitacao === true ? " · em tramitação" : p.em_tramitacao === false ? " · tramitação encerrada" : ""}
                  {p.primeiro_autor ? "" : " · coautor"}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
      <FonteRodape fonte={v.fonte_nome} url={v.fonte_url} atualizadoEm={v.atualizado_em} />
    </section>
  );
}

function ContatoLocal({ v }: { v: VereadorDetalhe }) {
  if (!v.email && !v.telefone) return null;
  return (
    <section aria-labelledby="contato-titulo" className="flex flex-col gap-2">
      <h2 id="contato-titulo" className="text-2xl">
        Contato
      </h2>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {v.email && (
          <>
            <dt className="text-muted-foreground">E-mail</dt>
            <dd className="break-all">
              <a href={`mailto:${v.email}`} className="underline underline-offset-2">
                {v.email}
              </a>
            </dd>
          </>
        )}
        {v.telefone && (
          <>
            <dt className="text-muted-foreground">Telefone</dt>
            <dd>{v.telefone}</dd>
          </>
        )}
      </dl>
      <FonteRodape fonte={v.fonte_nome} url={v.fonte_url} atualizadoEm={v.atualizado_em} />
    </section>
  );
}
