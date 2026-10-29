import { FonteRodape } from "@/components/fonte-rodape";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import type { RepassesEstaduais, TipoRepasseEstadual } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

function porcento(valor: number) {
  return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function TiposLista({ tipos, maior }: { tipos: TipoRepasseEstadual[]; maior: number }) {
  return (
    <ul className="flex flex-col gap-4">
      {tipos.map((t) => (
        <li key={t.chave} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-3">
            <span className="min-w-0 font-medium">{t.rotulo}</span>
            <span className="shrink-0 tabular-nums">
              {formatarReais(t.valor, true)}
              <span className="ml-1 text-sm text-muted-foreground">{porcento(t.percentual)}</span>
            </span>
          </div>
          <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
            <div
              className="h-1.5 rounded-full bg-chart-1"
              style={{ width: `${maior ? Math.max(1, (Math.max(t.valor, 0) / maior) * 100) : 0}%` }}
            />
          </div>
          <p className="text-sm text-muted-foreground">{t.termo_oficial}</p>
          <p className="text-sm">{t.explicacao}</p>
          {t.por_habitante != null && (
            <p className="text-sm text-muted-foreground">
              <span className="tabular-nums">{formatarReais(t.por_habitante, true)}</span> por morador
              {t.media_uf_por_habitante != null && (
                <>
                  {" "}
                  · média do estado{" "}
                  <span className="tabular-nums">{formatarReais(t.media_uf_por_habitante, true)}</span>
                </>
              )}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

/** Quanto o governo do estado repassou à prefeitura, por tipo (SICONFI, DCA). */
export function RepassesEstaduaisSecao({
  dados,
  cidade,
  estado,
}: {
  dados: RepassesEstaduais;
  cidade: string;
  estado: string;
}) {
  if (!dados.disponivel || dados.total == null || dados.ano == null) {
    return (
      <section aria-labelledby="repasses-estado-titulo" className="flex flex-col gap-2">
        <h2 id="repasses-estado-titulo" className="text-2xl">
          Dinheiro do governo do estado
        </h2>
        {dados.motivo && <p className="text-sm text-muted-foreground">{dados.motivo}</p>}
        <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
      </section>
    );
  }
  const maior = Math.max(0, ...dados.tipos.map((t) => t.valor));
  const fora = Math.max(0, dados.municipios_uf - dados.municipios_na_media);
  return (
    <section aria-labelledby="repasses-estado-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="repasses-estado-titulo" className="text-2xl">
          Dinheiro do governo do estado em {dados.ano}
        </h2>
        <p className="text-sm text-muted-foreground">
          O que a prefeitura de {cidade} declarou ao Tesouro Nacional ter recebido do governo de {estado}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        <div className="figura min-w-0">
          <dt className="text-sm text-muted-foreground">Recebeu do estado</dt>
          <dd className="numero text-xl break-words sm:text-3xl">{formatarReais(dados.total, true)}</dd>
          {dados.anterior && (
            <dd className="text-sm text-muted-foreground">
              Em {dados.anterior.ano}: <span className="tabular-nums">{formatarReais(dados.anterior.total, true)}</span>
            </dd>
          )}
        </div>
        {dados.por_habitante != null && (
          <div className="figura min-w-0">
            <dt className="text-sm text-muted-foreground">Por morador</dt>
            <dd className="numero text-xl break-words sm:text-3xl">{formatarReais(dados.por_habitante, true)}</dd>
            {dados.media_uf_por_habitante != null && (
              <dd className="text-sm text-muted-foreground">
                Média dos {dados.municipios_na_media.toLocaleString("pt-BR")} municípios do estado:{" "}
                <span className="tabular-nums">{formatarReais(dados.media_uf_por_habitante, true)}</span>
              </dd>
            )}
          </div>
        )}
      </dl>
      {dados.por_habitante != null && dados.media_uf_por_habitante != null && (
        <BarraComparacao
          pessoa={{ rotulo: cidade, valor: dados.por_habitante }}
          media={{ rotulo: "Média dos municípios do estado", valor: dados.media_uf_por_habitante }}
          formato="reais"
        />
      )}
      {dados.parte_por_lei != null && dados.percentual_por_lei != null && (
        <p className="text-sm">
          <span className="tabular-nums">{porcento(dados.percentual_por_lei)}</span> desse dinheiro (
          <span className="tabular-nums">{formatarReais(dados.parte_por_lei, true)}</span>) são partes de impostos e
          royalties que a Constituição e as leis mandam o estado dividir com as cidades: é repasse obrigatório, e a
          conta de quanto cabe a cada cidade segue regras fixas. O restante (saúde, convênios e outros) segue
          programas e acordos entre o estado e a prefeitura.
        </p>
      )}
      {dados.tipos.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">O que o estado repassou, por tipo</h3>
          <TiposLista tipos={dados.tipos} maior={maior} />
        </div>
      )}
      {dados.fundeb != null && dados.fundeb > 0 && (
        <p className="text-sm text-muted-foreground">
          Do total, <span className="tabular-nums">{formatarReais(dados.fundeb, true)}</span> (20% das partes de
          impostos) foram separados para o Fundeb, o fundo da educação básica, que redistribui o dinheiro entre as
          redes de ensino do estado pelo número de alunos.
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        {dados.anos_sem_contas.length > 0 && (
          <>
            A prefeitura não enviou ao Tesouro as contas de {dados.anos_sem_contas.join(" e ")}
            {dados.anos_sem_contas.some((a) => a > dados.ano!) ? `; por isso o ano mostrado é ${dados.ano}` : ""}.{" "}
          </>
        )}
        {fora > 0 && (
          <>
            Na média ficam de fora {fora.toLocaleString("pt-BR")}{" "}
            {fora === 1 ? "município" : "municípios"} de {estado} cuja prefeitura não enviou as contas de {dados.ano} ao
            Tesouro (ou não informou a população).{" "}
          </>
        )}
        {dados.media_uf_descricao} Os valores são brutos, como a prefeitura declarou no ano (receitas de
        transferências dos estados, correntes e de capital).
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
