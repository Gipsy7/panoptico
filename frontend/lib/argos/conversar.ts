/**
 * Uma volta da conversa: interpreta a frase, chama a API (injetada, para testar sem rede) e monta
 * as mensagens. Sem estado próprio: o contexto (a última pessoa) entra e sai pelos argumentos e
 * fica só na tela; nada é gravado.
 */
import type {
  Gastos,
  Municipio,
  ParlamentarDetalhe,
  Presenca,
  Projetos,
  Representantes,
  RespostaBusca,
  Resultado,
} from "@/lib/api";
import { UFS } from "@/lib/ufs";

import { PALAVRAS_DO_VOCABULARIO, interpretar } from "./interpretar";
import {
  type Lugar,
  compararNaoAchou,
  compararSemNomes,
  erroDaApi,
  escolherCandidatos,
  escolherCidade,
  idFederal,
  mensagemAssuntos,
  mensagemEscolha,
  mensagemSemNome,
  mensagemSoPerfil,
  naoEntendi,
  opiniao,
  pedirCep,
  pedirCidade,
  pedirNome,
  pessoaDe,
  respostaCidade,
  respostaComparar,
  respostaDinheiroFederal,
  respostaEleicao,
  respostaEmendas,
  respostaExecutivo,
  respostaGastos,
  respostaGovernoGasto,
  respostaLista,
  respostaPagina,
  respostaPartidos,
  respostaPresenca,
  respostaProjetos,
  respostaProjetosBusca,
  respostaRepresentantes,
  respostaSalario,
  respostaSecao,
  respostaSite,
  saudacao,
  semGenericos,
  semRanking,
} from "./responder";
import { normalizar, contem } from "./texto";
import type { Acao, AssuntoPessoa, Contexto, Interpretacao, Mensagem, PessoaLembrada } from "./tipos";

/** O que o Argos precisa da API; no site vem de `lib/api.ts`. */
export type ApiArgos = {
  busca: (q: string) => Promise<Resultado<RespostaBusca>>;
  representantes: (consulta: { cep?: string; uf?: string; municipio?: string }) => Promise<Resultado<Representantes>>;
  parlamentar: (id: string) => Promise<Resultado<ParlamentarDetalhe>>;
  gastos: (id: string, ano?: string) => Promise<Resultado<Gastos>>;
  presenca: (id: string, ano?: string) => Promise<Resultado<Presenca>>;
  projetos: (id: string) => Promise<Resultado<Projetos>>;
  municipios: (uf: string) => Promise<Resultado<Municipio[]>>;
};

export type Entrada = { frase: string; acao?: Acao };

export type Volta = { mensagens: Mensagem[]; contexto: Contexto };

type DadoDePessoa = "gastos" | "presenca" | "projetos";

async function dadosDaPessoa(pessoa: PessoaLembrada, acao: Acao, api: ApiArgos): Promise<Mensagem> {
  const id = idFederal(pessoa.caminho);
  if (!id) return mensagemSoPerfil(pessoa);
  const assunto = acao.assunto;
  if (assunto === "emendas") return respostaEmendas(pessoa);
  if (assunto === "secao") return respostaSecao(pessoa, acao.secao ?? "");
  const ano = acao.ano ? String(acao.ano) : undefined;

  if (assunto === "salario") {
    const p = await api.parlamentar(id);
    return p.ok ? respostaSalario(pessoa, p.dados) : erroDaApi(p.status, p.mensagem);
  }
  const quer = assunto as DadoDePessoa;
  const [parl, dado] = await Promise.all([
    api.parlamentar(id),
    quer === "gastos" ? api.gastos(id, ano) : quer === "presenca" ? api.presenca(id, ano) : api.projetos(id),
  ]);
  if (!dado.ok) return erroDaApi(dado.status, dado.mensagem);
  const casa = parl.ok ? parl.dados.casa : null;
  if (quer === "gastos") return respostaGastos(pessoa, casa, dado.dados as Gastos, acao.mes);
  if (quer === "presenca") return respostaPresenca(pessoa, casa, dado.dados as Presenca);
  return respostaProjetos(pessoa, casa, dado.dados as Projetos);
}

/** Responde sobre uma pessoa já escolhida. */
async function sobrePessoa(acao: Acao, api: ApiArgos): Promise<Volta> {
  const contexto: Contexto = { pessoa: acao.pessoa };
  if (!idFederal(acao.pessoa.caminho)) return { mensagens: [mensagemSoPerfil(acao.pessoa)], contexto };
  if (acao.assunto === "pessoa") return { mensagens: [mensagemAssuntos(acao.pessoa)], contexto };
  return { mensagens: [await dadosDaPessoa(acao.pessoa, acao, api)], contexto };
}

// ---------- Cidades ----------

type Cidades = { tipo: "nenhum" } | { tipo: "um"; m: Municipio } | { tipo: "varios"; itens: Municipio[] } | { tipo: "erro" };

/**
 * Procura, no texto, o nome de uma cidade (no estado dito, ou em todos). Só vale nome que tenha
 * pelo menos uma palavra fora do vocabulário ("Bom Jesus" vale; "Bom" sozinho, não).
 */
async function acharCidade(frase: string, uf: string | undefined, api: ApiArgos): Promise<Cidades> {
  const norm = normalizar(frase);
  const ufs = uf ? [uf] : UFS.map((u) => u.sigla);
  const listas = await Promise.all(ufs.map((u) => api.municipios(u)));
  if (listas.every((l) => !l.ok)) return { tipo: "erro" };
  const achados: Municipio[] = [];
  for (const l of listas) {
    if (!l.ok) continue;
    for (const m of l.dados) {
      const nome = normalizar(m.nome);
      if (!contem(norm, nome)) continue;
      if (nome.split(" ").every((p) => PALAVRAS_DO_VOCABULARIO.has(p))) continue;
      achados.push(m);
    }
  }
  if (achados.length === 0) return { tipo: "nenhum" };
  const maior = Math.max(...achados.map((m) => m.nome.length));
  const melhores = achados.filter((m) => m.nome.length === maior);
  return melhores.length === 1 ? { tipo: "um", m: melhores[0] } : { tipo: "varios", itens: melhores };
}

/** Lugar pedido na frase: o estado ou a cidade; devolve a mensagem de pergunta se precisar. */
async function acharLugar(
  frase: string,
  i: Interpretacao,
  api: ApiArgos,
): Promise<{ lugar: Lugar } | { mensagem: Mensagem } | { semLugar: true }> {
  if (i.nome || i.assunto === "cidade") {
    const c = await acharCidade(frase, i.uf, api);
    if (c.tipo === "erro") return { mensagem: erroDaApi(503, "") };
    if (c.tipo === "um") return { lugar: { uf: c.m.uf, municipio: c.m } };
    if (c.tipo === "varios") return { mensagem: escolherCidade(c.itens, frase) };
  }
  if (i.uf) return { lugar: { uf: i.uf } };
  return { semLugar: true };
}

// ---------- Conversa ----------

export async function conversar(entrada: Entrada, contexto: Contexto, api: ApiArgos, agora: Date = new Date()): Promise<Volta> {
  if (entrada.acao) return sobrePessoa(entrada.acao, api);

  const frase = entrada.frase;
  const i = interpretar(frase, agora);
  const so = (m: Mensagem): Volta => ({ mensagens: [m], contexto });

  switch (i.assunto) {
    case "opiniao":
      return so(opiniao());
    case "saudacao":
      return so(saudacao());
    case "site":
      return so(respostaSite(i.perguntaId));
    case "nenhum":
      return so(naoEntendi(i.sugestoes));
    case "ranking":
      return so(semRanking(i.ordem, { uf: i.uf, casa: i.casa }));
    case "pagina":
      return so(respostaPagina(i.secao ?? ""));
    case "partidos":
      return so(respostaPartidos(i.partido, i.ano));
    case "eleicao":
      return so(respostaEleicao(i.uf));
    case "projetos_busca":
      return so(respostaProjetosBusca(i.tema ?? "", i.uf, i.ano));
    case "representantes":
    case "lista":
      return representantes(i, frase, contexto, api);
    case "comparar":
      return comparar(i, contexto, api);
    case "executivo": {
      // "Prefeito de Gaspar" é lugar; "Lula presidente" é pessoa.
      if (i.nome) {
        const c = await acharCidade(frase, i.uf, api);
        if (c.tipo === "nenhum" || c.tipo === "erro") return pessoa({ ...i, assunto: "pessoa" }, frase, contexto, api);
      }
      return lugar(i, frase, contexto, api);
    }
    case "dinheiro_federal":
    case "governo_gasto":
    case "cidade":
      return lugar(i, frase, contexto, api);
    default:
      return pessoa(i, frase, contexto, api);
  }
}

async function representantes(i: Interpretacao, frase: string, contexto: Contexto, api: ApiArgos): Promise<Volta> {
  const so = (m: Mensagem): Volta => ({ mensagens: [m], contexto });
  const consultar = async (consulta: { cep?: string; uf?: string; municipio?: string }) => {
    const r = await api.representantes(consulta);
    return so(r.ok ? respostaRepresentantes(consulta.cep ?? null, r.dados, i.casa, consulta) : erroDaApi(r.status, r.mensagem));
  };
  if (i.cep) return consultar({ cep: i.cep });
  if (i.assunto === "lista" && !i.uf && !i.partido) return so(respostaLista({ casa: i.casa }));
  if (i.assunto === "lista" && i.partido && !i.uf) return so(respostaLista({ casa: i.casa, partido: i.partido }));
  if (i.nome || i.uf) {
    const l = await acharLugar(frase, i, api);
    if ("mensagem" in l) return so(l.mensagem);
    if ("lugar" in l) {
      if (l.lugar.municipio) return consultar({ municipio: l.lugar.municipio.ibge });
      if (l.lugar.uf) return consultar({ uf: l.lugar.uf });
    }
  }
  return i.assunto === "lista" ? so(respostaLista({ casa: i.casa })) : so(pedirCep());
}

async function lugar(i: Interpretacao, frase: string, contexto: Contexto, api: ApiArgos): Promise<Volta> {
  const so = (m: Mensagem): Volta => ({ mensagens: [m], contexto });
  const l = await acharLugar(frase, i, api);
  if ("mensagem" in l) return so(l.mensagem);
  const onde: Lugar = "lugar" in l ? l.lugar : {};
  const temLugar = "lugar" in l;
  switch (i.assunto) {
    case "dinheiro_federal":
      return so(respostaDinheiroFederal(onde, i.relativo ? undefined : i.ano));
    case "governo_gasto":
      return so(respostaGovernoGasto(i, onde));
    case "executivo":
      return so(respostaExecutivo(i.cargo, onde));
    default:
      return so(onde.municipio ? respostaCidade(onde.municipio) : temLugar ? respostaLista({ uf: onde.uf }) : pedirCidade());
  }
}

async function comparar(i: Interpretacao, contexto: Contexto, api: ApiArgos): Promise<Volta> {
  const so = (m: Mensagem): Volta => ({ mensagens: [m], contexto });
  const nomes = (i.nomes ?? []).slice(0, 4);
  if (nomes.length === 0) return so(compararSemNomes(contexto.pessoa));
  const achados: PessoaLembrada[] = [];
  const faltou: string[] = [];
  const respostas = await Promise.all(nomes.map((n) => api.busca(n)));
  respostas.forEach((r, k) => {
    if (!r.ok) return;
    const c = escolherCandidatos(semGenericos(r.dados, nomes[k]), nomes[k]);
    const federal = c.tipo === "um" && idFederal(c.item.caminho) ? c.item : null;
    if (federal) achados.push(pessoaDe(federal));
    else faltou.push(nomes[k]);
  });
  if (respostas.every((r) => !r.ok)) return so(erroDaApi(503, ""));
  if (achados.length >= 2 && faltou.length === 0) return { mensagens: [respostaComparar(achados, i.ano)], contexto };
  if (achados.length >= 2) return { mensagens: [respostaComparar(achados, i.ano)], contexto };
  if (achados.length === 1 && faltou.length === 0) return so(compararSemNomes(achados[0]));
  return so(compararNaoAchou(faltou, achados));
}

async function pessoa(i: Interpretacao, frase: string, contexto: Contexto, api: ApiArgos): Promise<Volta> {
  const so = (m: Mensagem): Volta => ({ mensagens: [m], contexto });
  const assunto = i.assunto as AssuntoPessoa;
  const acaoCom = (p: PessoaLembrada): Acao => ({ assunto, pessoa: p, secao: i.secao, ano: i.ano, mes: i.mes });

  if (!i.nome) {
    if (contexto.pessoa) return sobrePessoa(acaoCom(contexto.pessoa), api);
    return so(pedirNome());
  }
  const b = await api.busca(i.nome);
  if (!b.ok) return so(erroDaApi(b.status, b.mensagem));
  const c = escolherCandidatos(semGenericos(b.dados, i.nome), i.nome);
  if (c.tipo === "nenhum") {
    // Não é pessoa: talvez seja uma cidade ("dinheiro que Gaspar recebeu").
    const cidade = await acharCidade(frase, i.uf, api);
    if (cidade.tipo === "um") return so(respostaCidade(cidade.m));
    if (cidade.tipo === "varios") return so(escolherCidade(cidade.itens, frase));
    return so(mensagemSemNome(b.dados.partidos));
  }
  if (c.tipo === "varios") {
    const escolha = mensagemEscolha(c.itens, c.total, assunto);
    // O nome também pode ser de uma cidade ("dinheiro que Gaspar recebeu"): oferece os links dela.
    const cidade = await acharCidade(frase, i.uf, api);
    if (cidade.tipo === "um") {
      const m = cidade.m;
      escolha.detalhes = [`Se você quis dizer a cidade ${m.nome}-${m.uf}, veja os links abaixo.`];
      escolha.links = [
        { rotulo: `Página de ${m.nome}-${m.uf}`, href: `/cidade/${m.ibge}` },
        { rotulo: `Impostos e repasses de ${m.nome}`, href: `/impostos-e-repasses/${m.uf}/${m.ibge}` },
      ];
    }
    return so(escolha);
  }
  const p = pessoaDe(c.item);
  if (!idFederal(c.item.caminho)) return { mensagens: [mensagemSoPerfil(p, c.item.cargo)], contexto: { pessoa: p } };
  return sobrePessoa(acaoCom(p), api);
}
