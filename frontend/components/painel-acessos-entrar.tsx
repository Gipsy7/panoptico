"use client";

import { useId, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function Entrar({ aoEntrar }: { aoEntrar: (token: string) => void }) {
  const id = useId();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const r = await fetch(`${API}/painel/entrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario, senha }),
      });
      if (r.ok) {
        aoEntrar((await r.json()).token);
        return;
      }
      setSenha("");
      setErro(
        r.status === 429
          ? "Muitas tentativas. Tente de novo em alguns minutos."
          : r.status === 503
            ? "O painel não está configurado neste ambiente."
            : "Usuário ou senha incorretos.",
      );
    } catch {
      setErro("Não deu para falar com o servidor. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  const campo = "w-full rounded-lg border border-border bg-card px-3 py-2 text-base";
  return (
    <form onSubmit={enviar} className="flex max-w-sm flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1">
        <label htmlFor={`${id}-u`} className="text-sm font-medium">
          Usuário
        </label>
        <input
          id={`${id}-u`}
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `${id}-e` : undefined}
          className={campo}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor={`${id}-s`} className="text-sm font-medium">
          Senha
        </label>
        <input
          id={`${id}-s`}
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          autoComplete="current-password"
          required
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `${id}-e` : undefined}
          className={campo}
        />
      </div>
      {erro && (
        <p id={`${id}-e`} role="alert" className="text-sm font-medium text-foreground">
          {erro}
        </p>
      )}
      <button type="submit" className="botao" disabled={enviando}>
        {enviando ? "Entrando..." : "Entrar"}
      </button>
    </form>
  );
}
