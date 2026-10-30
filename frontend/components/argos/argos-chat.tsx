"use client";

import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ArgosMensagem } from "@/components/argos/argos-mensagem";
import {
  getBusca,
  getGastos,
  getParlamentar,
  getPresenca,
  getProjetos,
  getRepresentantes,
} from "@/lib/api";
import { type ApiArgos, conversar } from "@/lib/argos/conversar";
import { erroDeRede, saudacao } from "@/lib/argos/responder";
import type { Acao, Contexto, Mensagem } from "@/lib/argos/tipos";

const API: ApiArgos = {
  busca: (q) => getBusca(q),
  representantes: (cep) => getRepresentantes({ cep }),
  parlamentar: (id) => getParlamentar(id),
  gastos: (id) => getGastos(id),
  presenca: (id) => getPresenca(id),
  projetos: (id) => getProjetos(id),
};

type Item = { id: number; autor: "voce" | "argos"; texto?: string; mensagem?: Mensagem };

/**
 * Chat do Argos: respostas prontas, sem IA. A conversa e a última pessoa citada ficam só na
 * memória desta tela (nada vai para o servidor, o localStorage ou análise de uso).
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
  const proximoId = useRef(2);
  const iniciou = useRef(false);
  const registro = useRef<HTMLDivElement>(null);

  /** Pede a resposta; a frase da pessoa já deve estar na lista e `ocupado` ligado. */
  async function responder(frase: string, acao: Acao | undefined, contextoAtual: Contexto) {
    let mensagens: Mensagem[];
    let novoContexto = contextoAtual;
    try {
      const volta = await conversar({ frase, acao }, contextoAtual, API);
      mensagens = volta.mensagens;
      novoContexto = volta.contexto;
    } catch {
      mensagens = [erroDeRede()];
    }
    setContexto(novoContexto);
    setItens((atual) => [
      ...atual,
      ...mensagens.map((mensagem) => ({ id: proximoId.current++, autor: "argos" as const, mensagem })),
    ]);
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
        <p className="text-sm text-muted-foreground">O site não grava o que você escreve.</p>
      </form>
    </div>
  );
}
