import { CalendarioAoVivo } from "@/components/calendario-ao-vivo";
import { getCalendarioVotacoes } from "@/lib/api";
import type { EstadoCalendario } from "@/lib/calendario-votacoes";

/** Busca o calendário no servidor (primeira visita e sem JavaScript); sem dado, não mostra nada. */
export async function SecaoCalendarioVotacoes({ estado }: { estado: EstadoCalendario }) {
  const [ano, mes] = estado.mes ? estado.mes.split("-") : [undefined, undefined];
  const r = await getCalendarioVotacoes({
    casa: estado.casa,
    ano,
    mes,
    dia: estado.dia,
    tipo: estado.tipo,
    pagina: estado.pagina,
  });
  if (!r.ok) return null;
  return <CalendarioAoVivo dadosIniciais={r.dados} estadoInicial={estado} />;
}
