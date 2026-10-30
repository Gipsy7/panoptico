/**
 * Uma volta da conversa: interpreta a frase, chama a API (injetada, para testar sem rede) e monta
 * as mensagens. Sem estado próprio: o contexto (a última pessoa) entra e sai pelos argumentos e
 * fica só na tela; nada é gravado.
 */
import type {
  Gastos,
  ParlamentarDetalhe,
  Presenca,
  Projetos,
  Representantes,
  RespostaBusca,
  Resultado,
} from "@/lib/api";

import { interpretar } from "./interpretar";
import {
  erroDaApi,
  escolherCandidatos,
  idFederal,
  mensagemAssuntos,
  mensagemEscolha,
  mensagemSemNome,
  mensagemSoPerfil,
  naoEntendi,
  opiniao,
  pedirCep,
  pedirNome,
  semRanking,
  pessoaDe,
  respostaEmendas,
  respostaGastos,
  respostaPresenca,
  respostaProjetos,
  respostaRepresentantes,
  respostaSite,
  saudacao,
} from "./responder";
import type { Acao, AssuntoPessoa, Contexto, Mensagem, PessoaLembrada } from "./tipos";

/** O que o Argos precisa da API; no site vem de `lib/api.ts`. */
export type ApiArgos = {
  busca: (q: string) => Promise<Resultado<RespostaBusca>>;
  representantes: (cep: string) => Promise<Resultado<Representantes>>;
  parlamentar: (id: string) => Promise<Resultado<ParlamentarDetalhe>>;
  gastos: (id: string) => Promise<Resultado<Gastos>>;
  presenca: (id: string) => Promise<Resultado<Presenca>>;
  projetos: (id: string) => Promise<Resultado<Projetos>>;
};

export type Entrada = { frase: string; acao?: Acao };

export type Volta = { mensagens: Mensagem[]; contexto: Contexto };

async function dadosDaPessoa(
  pessoa: PessoaLembrada,
  assunto: Exclude<AssuntoPessoa, "pessoa">,
  api: ApiArgos,
): Promise<Mensagem> {
  const id = idFederal(pessoa.caminho);
  if (!id) return mensagemSoPerfil(pessoa);
  if (assunto === "emendas") return respostaEmendas(pessoa);

  const [parl, dado] = await Promise.all([
    api.parlamentar(id),
    assunto === "gastos" ? api.gastos(id) : assunto === "presenca" ? api.presenca(id) : api.projetos(id),
  ]);
  if (!dado.ok) return erroDaApi(dado.status, dado.mensagem);
  const casa = parl.ok ? parl.dados.casa : null;
  if (assunto === "gastos") return respostaGastos(pessoa, casa, dado.dados as Gastos);
  if (assunto === "presenca") return respostaPresenca(pessoa, casa, dado.dados as Presenca);
  return respostaProjetos(pessoa, casa, dado.dados as Projetos);
}

/** Responde sobre uma pessoa já escolhida. */
async function sobrePessoa(pessoa: PessoaLembrada, assunto: AssuntoPessoa, api: ApiArgos): Promise<Volta> {
  const contexto: Contexto = { pessoa };
  if (!idFederal(pessoa.caminho)) return { mensagens: [mensagemSoPerfil(pessoa)], contexto };
  if (assunto === "pessoa") return { mensagens: [mensagemAssuntos(pessoa)], contexto };
  return { mensagens: [await dadosDaPessoa(pessoa, assunto, api)], contexto };
}

export async function conversar(entrada: Entrada, contexto: Contexto, api: ApiArgos): Promise<Volta> {
  if (entrada.acao) return sobrePessoa(entrada.acao.pessoa, entrada.acao.assunto, api);

  const i = interpretar(entrada.frase);
  const mantido: Volta["contexto"] = contexto;
  const so = (m: Mensagem): Volta => ({ mensagens: [m], contexto: mantido });

  switch (i.assunto) {
    case "opiniao":
      return so(opiniao());
    case "saudacao":
      return so(saudacao());
    case "ranking":
      return so(semRanking());
    case "site":
      return so(respostaSite(i.perguntaId));
    case "nenhum":
      return so(naoEntendi());
    case "representantes": {
      if (!i.cep) return so(pedirCep());
      const r = await api.representantes(i.cep);
      return so(r.ok ? respostaRepresentantes(i.cep, r.dados) : erroDaApi(r.status, r.mensagem));
    }
    default: {
      // gastos, presença, projetos, emendas ou só um nome.
      const assunto: AssuntoPessoa = i.assunto;
      if (!i.nome) {
        if (contexto.pessoa) return sobrePessoa(contexto.pessoa, assunto, api);
        return so(pedirNome());
      }
      const b = await api.busca(i.nome);
      if (!b.ok) return so(erroDaApi(b.status, b.mensagem));
      const c = escolherCandidatos(b.dados, i.nome);
      if (c.tipo === "nenhum") return so(mensagemSemNome(b.dados.partidos));
      if (c.tipo === "varios") return so(mensagemEscolha(c.itens, c.total, assunto));
      const volta = await sobrePessoa(pessoaDe(c.item), assunto, api);
      if (!idFederal(c.item.caminho)) {
        // Cargo sem resumo numérico: o link do perfil, com o cargo dito.
        return { mensagens: [mensagemSoPerfil(pessoaDe(c.item), c.item.cargo)], contexto: volta.contexto };
      }
      return volta;
    }
  }
}
