/**
 * Ícones de assunto (traço, 24×24, cor do texto): os mesmos no Mapa, nas fichas e nos atalhos.
 * Desenho simples e reto, no espírito da identidade; nenhum ícone diz "bom" ou "ruim".
 */
export type Assunto =
  | "dinheiro"
  | "seguranca"
  | "saude"
  | "saneamento"
  | "escolas"
  | "economia"
  | "politica"
  | "pessoa"
  | "partido"
  | "projeto"
  | "lugar"
  | "mao";

const TRACOS: Record<Assunto, React.ReactNode> = {
  dinheiro: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.4 0-2.5.8-2.5 2s1.1 1.7 2.5 2 2.5.8 2.5 2-1.1 2-2.5 2c-1 0-2-.5-2.5-1.5M12 6.5v11" />
    </>
  ),
  seguranca: <path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6z" />,
  saude: <path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z" />,
  saneamento: <path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z" />,
  escolas: (
    <>
      <path d="M3 8l9-4 9 4-9 4z" />
      <path d="M7 10v5c0 1.5 2.5 3 5 3s5-1.5 5-3v-5" />
    </>
  ),
  economia: <path d="M4 20h16M6 16v-4M10 16V8M14 16v-6M18 16V5" />,
  politica: <path d="M4 20h16M5 10h14M12 4l8 4H4zM7 10v8M12 10v8M17 10v8" />,
  pessoa: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
    </>
  ),
  partido: <path d="M5 21V4M5 4h11l-2 4 2 4H5" />,
  projeto: (
    <>
      <path d="M7 3h7l4 4v14H7z" />
      <path d="M14 3v4h4M10 12h5M10 16h5" />
    </>
  ),
  lugar: (
    <>
      <path d="M12 21s-6-6-6-11a6 6 0 0 1 12 0c0 5-6 11-6 11z" />
      <circle cx="12" cy="10" r="2" />
    </>
  ),
  mao: (
    <path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V10m0-1.5a1.5 1.5 0 0 1 3 0V11m0-1a1.5 1.5 0 0 1 3 0v4c0 4-2.5 7-6 7h-1c-2 0-3.5-1-4.5-2.5L4.8 14a1.5 1.5 0 0 1 2.4-1.8L9 14" />
  ),
};

export function IconeAssunto({ assunto, className = "size-5" }: { assunto: Assunto; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={`shrink-0 ${className}`}
    >
      {TRACOS[assunto]}
    </svg>
  );
}
