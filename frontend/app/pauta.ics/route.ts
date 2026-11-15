import { getPauta } from "@/lib/api";
import { calendarioDaPauta } from "@/lib/calendario-pauta";
import { SITE_URL } from "@/lib/site";

// GET /pauta.ics: a pauta do Plenário (Câmara e Senado) dos próximos 30 dias, para assinar no
// calendário do celular. Sem cadastro: o aplicativo de calendário busca de novo sozinho.
const DIAS = 30;

export async function GET() {
  const r = await getPauta(DIAS);
  if (!r.ok) return new Response("A pauta não está disponível agora.", { status: 503 });
  return new Response(calendarioDaPauta(r.dados.itens, SITE_URL, new Date()), {
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": 'inline; filename="pauta-plenario.ics"',
      "Cache-Control": "public, max-age=1800, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
