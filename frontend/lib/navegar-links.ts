import type { KeyboardEvent } from "react";

// Setas numa lista de links logo abaixo de um campo de busca: ↓ do campo vai ao primeiro link,
// ↑/↓ andam entre eles (↑ do primeiro volta ao campo), Home/End vão às pontas, Esc volta ao campo.
// Tab continua andando pelos links normalmente.
export function teclarNaBusca(
  e: KeyboardEvent<HTMLElement>,
  container: HTMLElement | null,
  campo: HTMLInputElement | null,
) {
  if (!container || !campo) return;
  const links = Array.from(container.querySelectorAll<HTMLAnchorElement>("a[href]"));
  const noCampo = e.target === campo;
  const i = links.indexOf(e.target as HTMLAnchorElement);
  if (!noCampo && i < 0) return;
  let destino: HTMLElement | undefined;
  if (e.key === "ArrowDown") destino = noCampo ? links[0] : links[Math.min(i + 1, links.length - 1)];
  else if (e.key === "ArrowUp") destino = noCampo ? undefined : i === 0 ? campo : links[i - 1];
  else if (e.key === "Home" && !noCampo) destino = links[0];
  else if (e.key === "End" && !noCampo) destino = links[links.length - 1];
  else if (e.key === "Escape" && !noCampo) destino = campo;
  if (!destino) return;
  e.preventDefault();
  destino.focus();
}

export const CONTORNO_FOCO =
  "focus-visible:bg-accent focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-bronze-texto";
