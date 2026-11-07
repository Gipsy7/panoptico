import { AvisarErroProvider } from "@/components/avisar-erro/contexto";
import { FonteRodape } from "@/components/fonte-rodape";
import { type PerfilTipo, ANCORA_RESPOSTAS } from "@/lib/avisar-erro";
import { getRespostas } from "@/lib/api";
import { formatarData } from "@/lib/formato";

/**
 * Embrulha o perfil com a gaveta de aviso (Frente 7). Busca as respostas publicadas para o
 * link discreto de cada seção; se a rota não responde, o perfil segue sem elas.
 */
export async function AvisosDoPerfil({
  tipo,
  id,
  nome,
  children,
}: {
  tipo: PerfilTipo;
  id: string;
  nome: string;
  children: React.ReactNode;
}) {
  const r = await getRespostas(tipo, id);
  const secoes = r.ok ? r.dados.flatMap((x) => (x.secao ? [x.secao] : [])) : [];
  return (
    <AvisarErroProvider perfil={{ tipo, id, nome }} secoesComResposta={secoes}>
      {children}
    </AvisarErroProvider>
  );
}

/**
 * "Respostas de quem é citado", no fim do perfil. Só aparece se houver resposta publicada.
 * O texto sai como chegou; o site não concorda nem discorda dele.
 */
export async function RespostasCitado({ tipo, id, nome }: { tipo: PerfilTipo; id: string; nome: string }) {
  const r = await getRespostas(tipo, id);
  if (!r.ok || r.dados.length === 0) return null;
  const ultima = r.dados.map((x) => x.publicada_em).filter((d): d is string => !!d).sort().at(-1);
  return (
    <section aria-labelledby={ANCORA_RESPOSTAS} data-sem-aviso className="flex flex-col gap-3">
      <div>
        <h2 id={ANCORA_RESPOSTAS} className="text-2xl">
          Respostas de quem é citado
        </h2>
        <p className="text-sm text-muted-foreground">
          O texto abaixo foi enviado pela própria pessoa ou pela assessoria e publicado como chegou. O Panóptico não
          concorda nem discorda dele; os números do perfil continuam os da fonte oficial.
        </p>
      </div>
      <ul className="flex flex-col gap-3">
        {r.dados.map((x) => (
          <li key={x.id} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
            <p className="text-sm text-muted-foreground">
              Resposta de {nome}, recebida em {formatarData(x.recebida_em)}
              {x.secao ? <> · sobre “{x.secao}”</> : <> · sobre o perfil inteiro</>}
            </p>
            <blockquote className="mt-2 border-l-[3px] border-[var(--bronze)] pl-3 text-base leading-relaxed whitespace-pre-line">
              {x.texto}
            </blockquote>
          </li>
        ))}
      </ul>
      <FonteRodape
        fonte="texto enviado por quem é citado, com a identidade confirmada pelo canal oficial"
        atualizadoEm={ultima}
        semAviso
      />
    </section>
  );
}
