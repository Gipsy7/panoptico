export const UFS: { sigla: string; nome: string }[] = [
  { sigla: "AC", nome: "Acre" },
  { sigla: "AL", nome: "Alagoas" },
  { sigla: "AP", nome: "Amapá" },
  { sigla: "AM", nome: "Amazonas" },
  { sigla: "BA", nome: "Bahia" },
  { sigla: "CE", nome: "Ceará" },
  { sigla: "DF", nome: "Distrito Federal" },
  { sigla: "ES", nome: "Espírito Santo" },
  { sigla: "GO", nome: "Goiás" },
  { sigla: "MA", nome: "Maranhão" },
  { sigla: "MT", nome: "Mato Grosso" },
  { sigla: "MS", nome: "Mato Grosso do Sul" },
  { sigla: "MG", nome: "Minas Gerais" },
  { sigla: "PA", nome: "Pará" },
  { sigla: "PB", nome: "Paraíba" },
  { sigla: "PR", nome: "Paraná" },
  { sigla: "PE", nome: "Pernambuco" },
  { sigla: "PI", nome: "Piauí" },
  { sigla: "RJ", nome: "Rio de Janeiro" },
  { sigla: "RN", nome: "Rio Grande do Norte" },
  { sigla: "RS", nome: "Rio Grande do Sul" },
  { sigla: "RO", nome: "Rondônia" },
  { sigla: "RR", nome: "Roraima" },
  { sigla: "SC", nome: "Santa Catarina" },
  { sigla: "SP", nome: "São Paulo" },
  { sigla: "SE", nome: "Sergipe" },
  { sigla: "TO", nome: "Tocantins" },
];

// Estados que pedem "da"/"do" antes do nome; os demais levam "de" (de Pernambuco, de São Paulo).
const ARTIGO: Record<string, "da" | "do"> = {
  BA: "da",
  PB: "da",
  AC: "do",
  AP: "do",
  AM: "do",
  CE: "do",
  DF: "do",
  ES: "do",
  MA: "do",
  PA: "do",
  PR: "do",
  PI: "do",
  RJ: "do",
  RN: "do",
  RS: "do",
  TO: "do",
};

/** "da Paraíba", "do Acre", "de Pernambuco". */
export function doEstado(uf: string): string {
  const nome = UFS.find((u) => u.sigla === uf)?.nome ?? uf;
  return `${ARTIGO[uf] ?? "de"} ${nome}`;
}
