"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ARGOS_BOTAO, ArgosMensagem } from "@/components/argos/argos-mensagem";
import {
  getBusca,
  getGastos,
  getMunicipios,
  getParlamentar,
  getPresenca,
  getProjetos,
  getRepresentantes,
  postArgosAvaliacao,
  postArgosNaoEntendida,
} from "@/lib/api";
import { type ApiArgos, conversar } from "@/lib/argos/conversar";
import { limpar, prepararConversa, soMarca } from "@/lib/argos/limpar";
import { erroDeRede, saudacao } from "@/lib/argos/responder";
import type { Acao, Contexto, Mensagem } from "@/lib/argos/tipos";

// Lista de cidades por estado: guardada só na memória desta tela, para achar uma cidade sem estado.
const CIDADES = new Map<string, ReturnType<typeof getMunicipios>>();

const API: ApiArgos = {
  busca: (q) => getBusca(q),
  representantes: (consulta) => getRepresentantes(consulta),
  parlamentar: (id) => getParlamentar(id),
  gastos: (id, ano) => getGastos(id, ano),
  presenca: (id, ano) => getPresenca(id, ano),
  projetos: (id) => getProjetos(id),
  municipios: (uf) => {
    let lista = CIDADES.get(uf);
    if (!lista) {
      lista = getMunicipios(uf);
      CIDADES.set(uf, lista);
    }
    return lista;
  },
};

type Item = {
  id: number;
  autor: "voce" | "argos";
  texto?: string;
  mensagem?: Mensagem;
  /** Pergunta de consentimento para guardar a conversa (com os botões). */
  consentimento?: boolean;
};

/** Assuntos cuja resposta não conta para "isso ajudou?" (não trazem dado nem link de dado). */
const SEM_AVALIACAO = new Set(["saudacao", "nenhum", "opiniao"]);

type Avaliacao = "nao-perguntada" | "perguntando" | "consentimento" | "feita";

const textoDaMensagem = (m: Mensagem) => [m.texto, ...(m.detalhes ?? [])].join(" ");

/**
 * Chat do Argos: respostas prontas, sem IA. A conversa e a última pessoa citada ficam só na
 * memória desta tela. O que sai daqui (docs/DECISOES.md, 30/10/2026): a frase que o Argos não
 * entendeu (limpa de CEP, CPF, telefone, e-mail, URL e números longos), a avaliação "isso
 * ajudou?" e, só com "Pode guardar", a conversa limpa. Sem identificar quem escreveu.
 * `inicial` já abre respondendo a essa pergunta (usado por /pergunte?q=...).
 */
export function ArgosChat({
  inicial,
  modo = "pagina",
  aoNavegar,
}: {
  inicial?: string;
  modo?: "pagina" | "painel";
  aoNavegar?: () => void;
}) {
  const idCampo = useId();
  const [itens, setItens] = useState<Item[]>(() =>
    inicial ? [{ id: 1, autor: "voce", texto: inicial }] : [{ id: 1, autor: "argos", mensagem: saudacao() }],
  );
  const [contexto, setContexto] = useState<Contexto>({});
  const [ocupado, setOcupado] = useState(Boolean(inicial));
  const [texto, setTexto] = useState("");
  const [avaliacao, setAvaliacao] = useState<Avaliacao>("nao-perguntada");
  const proximoId = useRef(2);
  const iniciou = useRef(false);
  const registro = useRef<HTMLDivElement>(null);
  const assuntoAvaliado = useRef("nenhum");

  /** Pede a resposta; a frase da pessoa já deve estar na lista e `ocupado` ligado. */
  async function responder(frase: string, acao: Acao | undefined, contextoAtual: Contexto) {
    let mensagens: Mensagem[];
    let novoContexto = contextoAtual;
    let assunto = "nenhum";
    try {
      const volta = await conversar({ frase, acao }, contextoAtual, API);
      mensagens = volta.mensagens;
      novoContexto = volta.contexto;
      assunto = volta.assunto;
      if (volta.naoEntendeu && !acao) {
        const limpa = limpar(frase);
        if (limpa && !soMarca(limpa)) void postArgosNaoEntendida(limpa);
      }
    } catch {
      mensagens = [erroDeRede()];
    }
    setContexto(novoContexto);
    setItens((atual) => [
      ...atual,
      ...mensagens.map((mensagem) => ({ id: proximoId.current++, autor: "argos" as const, mensagem })),
    ]);
    const temDado = mensagens.some((m) => !m.erro && (m.links.length > 0 || m.fonte));
    if (temDado && !SEM_AVALIACAO.has(assunto)) {
      if (avaliacao === "nao-perguntada") {
        assuntoAvaliado.current = assunto;
        setAvaliacao("perguntando");
      }
    }
    setOcupado(false);
  }

  function enviar(frase: string, acao?: Acao) {
    const limpa = frase.trim().slice(0, 200);
    if (!limpa || ocupado) return;
    setItens((atual) => [...atual, { id: proximoId.current++, autor: "voce", texto: limpa }]);
    setOcupado(true);
    setTexto("");
    void responder(limpa, acao, contexto);
  }

  function aoEnviar(e: FormEvent) {
    e.preventDefault();
    enviar(texto);
  }

  function acrescentar(mensagem: Mensagem, consentimento = false) {
    setItens((atual) => [...atual, { id: proximoId.current++, autor: "argos", mensagem, consentimento }]);
  }

  function avaliar(util: boolean) {
    if (util) {
      void postArgosAvaliacao(true, assuntoAvaliado.current);
      setAvaliacao("feita");
      acrescentar({ texto: "Obrigado pela resposta.", links: [], botoes: [] });
      return;
    }
    setAvaliacao("consentimento");
    acrescentar(
      {
        texto: "Posso guardar esta conversa, sem identificar você, para a equipe melhorar o assistente?",
        links: [],
        botoes: [],
      },
      true,
    );
  }

  function consentir(guardar: boolean) {
    let conversa;
    if (guardar) {
      conversa = prepararConversa(
        itens
          .filter((i) => !i.consentimento)
          .map((i) =>
            i.autor === "voce"
              ? { autor: "cidadao" as const, texto: i.texto ?? "" }
              : { autor: "argos" as const, texto: i.mensagem ? textoDaMensagem(i.mensagem) : "" },
          ),
      );
    }
    void postArgosAvaliacao(false, assuntoAvaliado.current, conversa);
    setAvaliacao("feita");
    // A pergunta deixa de ter botões; o agradecimento oferece caminhos.
    setItens((atual) => atual.map((i) => (i.consentimento ? { ...i, consentimento: false } : i)));
    acrescentar({
      texto: guardar
        ? "Obrigado, a conversa foi guardada sem identificar você."
        : "Tudo bem, nada foi guardado além da sua avaliação. Obrigado.",
      links: [
        { rotulo: "Busca de parlamentares por nome", href: "/parlamentares" },
        { rotulo: "Perguntas frequentes", href: "/perguntas" },
      ],
      botoes: [],
    });
  }

  useEffect(() => {
    if (!inicial || iniciou.current) return;
    iniciou.current = true;
    void responder(inicial, undefined, {});
    // Só na primeira exibição.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Mostra o começo da última mensagem (uma resposta longa não "foge" para o fim).
  useEffect(() => {
    const log = registro.current;
    const ultima = log?.lastElementChild as HTMLElement | null | undefined;
    if (log && ultima) log.scrollTop = Math.max(0, ultima.offsetTop - 8);
  }, [itens, ocupado]);

  const altura = modo === "painel" ? "min-h-0 flex-1" : "min-h-64 max-h-[60dvh]";

  return (
    <div className={`flex flex-col gap-3 ${modo === "painel" ? "min-h-0 flex-1" : ""}`}>
      <div
        ref={registro}
        role="log"
        aria-label="Conversa com o Argos"
        aria-live="polite"
        aria-relevant="additions"
        className={`relative flex flex-col gap-4 overflow-y-auto overscroll-contain pr-1 ${altura}`}
      >
        {itens.map((item) =>
          item.autor === "voce" ? (
            <div key={item.id} className="troca-suave ml-auto flex max-w-[90%] flex-col gap-1 rounded-[2px] bg-secondary px-3 py-2">
              <p className="text-sm text-muted-foreground">Você</p>
              <p className="text-base break-words">{item.texto}</p>
            </div>
          ) : (
            <div key={item.id} className="troca-suave flex max-w-full flex-col gap-1 rounded-[2px] bg-card p-3 ring-1 ring-foreground/10">
              <p className="text-sm text-muted-foreground">Argos</p>
              {item.mensagem && (
                <ArgosMensagem mensagem={item.mensagem} aoEscolher={enviar} aoNavegar={aoNavegar} ocupado={ocupado} />
              )}
              {item.consentimento && (
                <ul className="flex flex-wrap gap-2">
                  <li>
                    <button type="button" onClick={() => consentir(true)} className={ARGOS_BOTAO}>
                      Pode guardar
                    </button>
                  </li>
                  <li>
                    <button type="button" onClick={() => consentir(false)} className={ARGOS_BOTAO}>
                      Não
                    </button>
                  </li>
                </ul>
              )}
            </div>
          ),
        )}
        {ocupado && (
          <div aria-hidden className="troca-suave flex flex-col gap-1 rounded-[2px] bg-card p-3 ring-1 ring-foreground/10">
            <p className="text-sm text-muted-foreground">Argos</p>
            <p className="text-base text-muted-foreground">Buscando nos dados oficiais…</p>
          </div>
        )}
      </div>

      <p role="status" className="sr-only">
        {ocupado ? "O Argos está buscando a resposta." : ""}
      </p>

      {avaliacao === "perguntando" && (
        <div role="group" aria-label="Avaliação da resposta" className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>Isso ajudou?</span>
          <button type="button" onClick={() => avaliar(true)} className={ARGOS_BOTAO}>
            Sim
          </button>
          <button type="button" onClick={() => avaliar(false)} className={ARGOS_BOTAO}>
            Não
          </button>
        </div>
      )}

      <form onSubmit={aoEnviar} className="flex flex-col gap-1 border-t border-border pt-3">
        <label htmlFor={idCampo} className="text-sm font-medium">
          Escreva sua pergunta
        </label>
        <div className="flex items-end gap-2">
          <input
            id={idCampo}
            type="text"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            maxLength={200}
            enterKeyHint="send"
            autoComplete="off"
            placeholder="Ex.: quanto Fulano gastou"
            className="campo min-w-0 flex-1 text-base"
          />
          <button type="submit" aria-disabled={ocupado} className="botao shrink-0 px-4">
            Enviar
          </button>
        </div>
        <p className="text-sm text-muted-foreground">
          Frases que eu não entendo ficam guardadas, sem identificar você, para eu aprender.{" "}
          <Link href="/privacidade#argos" onClick={aoNavegar} className="underline underline-offset-2">
            Saiba mais
          </Link>
        </p>
      </form>
    </div>
  );
}
