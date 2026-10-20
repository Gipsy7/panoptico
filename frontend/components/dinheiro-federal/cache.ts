import {
  type DinheiroFederalEstado,
  type DinheiroFederalMunicipio,
  type DinheiroFederalPainel,
  type Resultado,
  getDinheiroFederal,
  getDinheiroFederalMunicipio,
  getDinheiroFederalUf,
} from "@/lib/api";

// Cache em memória do navegador: navegar de volta ou trocar de ano repete respostas já vistas.
const cache = new Map<string, Promise<Resultado<unknown>>>();

function pegar<T>(chave: string, buscar: () => Promise<Resultado<T>>): Promise<Resultado<T>> {
  let p = cache.get(chave) as Promise<Resultado<T>> | undefined;
  if (!p) {
    p = buscar();
    p.then((r) => {
      if (!r.ok) cache.delete(chave); // tenta de novo na próxima vez
    });
    cache.set(chave, p);
  }
  return p;
}

export const painelDoAno = (ano: number) => pegar(`p:${ano}`, () => getDinheiroFederal(ano));
export const estadoDoAno = (uf: string, ano: number) => pegar(`e:${uf}:${ano}`, () => getDinheiroFederalUf(uf, ano));
export const municipioPorIbge = (ibge: string) => pegar(`m:${ibge}`, () => getDinheiroFederalMunicipio(ibge));

/** Guarda o que o servidor já entregou, para não pedir de novo. */
export function semear(
  painel: DinheiroFederalPainel,
  estado: DinheiroFederalEstado | null,
  municipio: DinheiroFederalMunicipio | null,
) {
  cache.set(`p:${painel.ano}`, Promise.resolve({ ok: true, dados: painel }));
  if (estado) cache.set(`e:${estado.uf}:${estado.ano}`, Promise.resolve({ ok: true, dados: estado }));
  if (municipio) cache.set(`m:${municipio.municipio.ibge}`, Promise.resolve({ ok: true, dados: municipio }));
}
