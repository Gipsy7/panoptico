/** Âncora da casa na página de cobertura: "ALAC" -> "alac", "Governo de AC" -> "governo-de-ac". */
export function idDaCasa(casa: string): string {
  return casa
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
