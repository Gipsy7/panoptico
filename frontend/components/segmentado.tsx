"use client";

/**
 * Régua de botões retos colados (no lugar de pílulas): escolhe uma opção entre poucas, como
 * "Hoje | Depois da posse" ou "Partido | Estado". O escolhido fica preenchido; `aria-pressed`
 * diz qual é. Quebra linha em tela estreita (reflow a 320 px).
 */
export function Segmentado<T extends string>({
  rotulo,
  opcoes,
  valor,
  aoMudar,
  esticar = false,
}: {
  rotulo: string;
  opcoes: readonly { valor: T; rotulo: string }[];
  valor: T;
  aoMudar: (v: T) => void;
  /** Ocupa a largura toda no celular, com as opções divididas por igual. */
  esticar?: boolean;
}) {
  return (
    <div
      role="group"
      aria-label={rotulo}
      className={`${esticar ? "flex w-full sm:inline-flex sm:w-auto" : "inline-flex"} max-w-full flex-wrap overflow-hidden rounded-[var(--raio)] border border-border text-sm`}
    >
      {opcoes.map((o) => (
        <button
          key={o.valor}
          type="button"
          aria-pressed={valor === o.valor}
          onClick={() => aoMudar(o.valor)}
          className={`min-h-11 border-l border-border px-3 first:border-l-0 hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-bronze aria-pressed:bg-foreground aria-pressed:font-semibold aria-pressed:text-background ${esticar ? "flex-1 sm:flex-none" : ""}`}
        >
          {o.rotulo}
        </button>
      ))}
    </div>
  );
}
