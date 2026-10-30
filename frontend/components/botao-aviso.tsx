"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  type AlvoTipo,
  type EstadoAviso,
  type Suporte,
  TEXTO_O_QUE_AVISA,
  TEXTO_O_QUE_GUARDA,
  acompanhaAlvo,
  estadoInicial,
  instrucaoSemSuporte,
} from "@/lib/avisos";
import { AVISOS_LIGADOS } from "@/lib/avisos-config";
import { ativar, consultarMinhas, inscricaoAtual, lerPermissao, lerSuporte, mudarAlvo } from "@/lib/avisos-navegador";

/**
 * "Avisar sobre novidades de ...": liga os avisos no celular para um parlamentar ou projeto federal.
 * Não renderiza nada no servidor nem sem a chave pública do build (NEXT_PUBLIC_VAPID_PUBLICA): lê as
 * APIs do navegador só depois da hidratação. A permissão só é pedida no clique. Só consulta o servidor
 * se o aparelho já tiver inscrição, para saber se este alvo está ativo.
 */
export function BotaoAviso({ alvoTipo, alvoChave, destino }: { alvoTipo: AlvoTipo; alvoChave: string | null; destino: string }) {
  const [pronto, setPronto] = useState(false);
  const [suporte, setSuporte] = useState<Suporte>("suportado");
  const [estado, setEstado] = useState<EstadoAviso>("pronto");
  const [mensagem, setMensagem] = useState("");
  const [indisponivel, setIndisponivel] = useState(false);

  useEffect(() => {
    if (!AVISOS_LIGADOS || !alvoChave) return;
    let ativo = true;
    (async () => {
      const s = lerSuporte();
      const permissao = lerPermissao();
      let acompanha = false;
      if (s === "suportado" && permissao === "granted") {
        const sub = await inscricaoAtual();
        if (sub) {
          const minhas = await consultarMinhas(sub);
          if (minhas.ok) acompanha = acompanhaAlvo(minhas.dados, alvoTipo, alvoChave);
          else if (minhas.status === 503) {
            if (ativo) setIndisponivel(true);
          }
        }
      }
      if (!ativo) return;
      setSuporte(s);
      setEstado(estadoInicial(s, permissao, acompanha));
      setPronto(true);
    })();
    return () => {
      ativo = false;
    };
  }, [alvoTipo, alvoChave]);

  if (!AVISOS_LIGADOS || !alvoChave || !pronto || indisponivel) return null;

  async function alternar() {
    if (!alvoChave) return;
    setMensagem("");
    if (estado === "ativo") {
      setEstado("pedindo");
      const sub = await inscricaoAtual();
      const r = sub ? await mudarAlvo(sub, alvoTipo, alvoChave, "remover") : null;
      if (r?.ok) {
        setEstado("pronto");
        setMensagem(`Avisos desligados para ${destino}.`);
      } else {
        setEstado("ativo");
        setMensagem(r ? r.mensagem : "Não foi possível desligar agora. Tente de novo.");
      }
      return;
    }
    setEstado("pedindo");
    const r = await ativar(alvoTipo, alvoChave);
    if (r.ok) {
      setEstado("ativo");
      setMensagem(`Avisos ativados para ${destino}.`);
    } else if (r.motivo === "negado") {
      setEstado("negado");
    } else {
      setEstado("erro");
      setMensagem(r.mensagem);
    }
  }

  if (estado === "sem-suporte" && suporte !== "suportado") {
    return (
      <div className="flex flex-col gap-1 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">Avisos no celular</p>
        <p>{instrucaoSemSuporte(suporte)}</p>
      </div>
    );
  }
  if (estado === "sem-suporte") return null;

  const ocupado = estado === "pedindo";
  const ativoAgora = estado === "ativo";
  const nome = ativoAgora ? `Parar de avisar sobre ${destino}` : `Avisar sobre novidades de ${destino}`;

  return (
    <div className="flex flex-col gap-2">
      {estado !== "negado" && (
        <button
          type="button"
          onClick={alternar}
          disabled={ocupado}
          aria-busy={ocupado}
          className="botao-linha !h-auto min-h-11 self-start py-2 text-center disabled:opacity-60"
        >
          {ocupado ? "Aguarde…" : nome}
        </button>
      )}
      <p role="status" className="text-sm font-medium">
        {mensagem}
      </p>
      {estado === "negado" && (
        <p className="max-w-prose text-sm text-muted-foreground">
          O navegador está bloqueando os avisos deste site. Para ativar, libere as notificações do Panóptico nas configurações do
          navegador e volte a esta página.
        </p>
      )}
      {ativoAgora ? (
        <p className="max-w-prose text-sm text-muted-foreground">
          Você recebe no máximo 1 aviso por dia.{" "}
          <Link href="/avisos" className="underline underline-offset-4">
            Ver o que este aparelho acompanha
          </Link>
          .
        </p>
      ) : (
        estado !== "negado" && (
          <p className="max-w-prose text-sm text-muted-foreground">
            {TEXTO_O_QUE_AVISA} {TEXTO_O_QUE_GUARDA}{" "}
            <Link href="/privacidade#avisos" className="underline underline-offset-4">
              Ler a página de privacidade
            </Link>
            .
          </p>
        )
      )}
    </div>
  );
}
