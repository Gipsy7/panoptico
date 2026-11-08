import { FonteRodape } from "@/components/fonte-rodape";
import type { InternetMunicipio } from "@/lib/api";
import { MESES_NOME } from "@/lib/calendario-votacoes";

/**
 * Internet fixa em "Por dentro da cidade" (Anatel): acessos de banda larga fixa por 100 moradores
 * no mês mais recente, com o estado e o Brasil contados do mesmo jeito, e quanto é fibra e quanto
 * passa de 34 Mbps.
 */
const um = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function InternetResumo({ dados, cidade, uf }: { dados: InternetMunicipio; cidade: string; uf: string }) {
  if (dados.acessos == null || dados.ano == null || dados.mes == null) return null;
  const quando = `${MESES_NOME[dados.mes - 1]?.toLowerCase() ?? dados.mes} de ${dados.ano}`;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {dados.por_100_moradores != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">Internet fixa a cada 100 moradores, {quando}</dt>
            <dd className="numero text-2xl">{um(dados.por_100_moradores)}</dd>
            <dd className="text-sm text-muted-foreground">
              {[
                dados.uf_por_100_moradores != null && `${uf}: ${um(dados.uf_por_100_moradores)}`,
                dados.brasil_por_100_moradores != null && `Brasil: ${um(dados.brasil_por_100_moradores)}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </dd>
          </div>
        )}
        {dados.percentual_fibra != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">Por fibra óptica</dt>
            <dd className="numero text-2xl">{um(dados.percentual_fibra)}%</dd>
            <dd className="text-sm text-muted-foreground">dos acessos</dd>
          </div>
        )}
        {dados.percentual_rapida != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">Acima de 34 Mbps</dt>
            <dd className="numero text-2xl">{um(dados.percentual_rapida)}%</dd>
            <dd className="text-sm text-muted-foreground">dos acessos</dd>
          </div>
        )}
      </dl>
      <p className="text-sm text-muted-foreground">
        {dados.acessos.toLocaleString("pt-BR")} acessos de internet fixa em {cidade} (casas e empresas). Um acesso é uma
        conexão contratada; a conta é por 100 moradores, com a população do IBGE. Termo oficial: acessos em serviço de
        banda larga fixa (SCM).
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
