import type { Casa, Temas } from "@/lib/api";

const LIMITE = 10;

export function TemasSecao({ dados, casa }: { dados: Temas; casa: Casa }) {
  if (!dados.disponivel || dados.temas.length === 0) return null;
  const temas = dados.temas.slice(0, LIMITE);
  const maior = Math.max(...temas.map((t) => t.primeiro_autor), 1);

  return (
    <section aria-labelledby="temas-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="temas-titulo" className="text-xl font-semibold">
          Projetos por tema
        </h2>
        <p className="text-xs text-muted-foreground">
          Classificação oficial {casa === "camara" ? "da Câmara" : "do Senado"}. Um projeto pode ter mais de um tema.
        </p>
      </div>
      <ul className="flex flex-col gap-3">
        {temas.map((t) => (
          <li
            key={t.tema}
            className="group flex flex-col gap-1"
            title={`${t.tema}: ${t.primeiro_autor} como autor principal, ${t.coautor} como coautor`}
          >
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span>{t.tema}</span>
              <span className="shrink-0 tabular-nums">
                <span className="font-medium">{t.primeiro_autor}</span>
                {t.coautor > 0 && (
                  <span className="text-xs text-muted-foreground"> · coautor em {t.coautor}</span>
                )}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted" aria-hidden>
              <div
                className="h-2 rounded-full bg-chart-1 transition-opacity group-hover:opacity-80"
                style={{ width: `${(t.primeiro_autor / maior) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted-foreground">
        A barra mostra os projetos como autor principal.
        {dados.homenagens > 0 &&
          ` ${dados.homenagens} ${dados.homenagens === 1 ? "é homenagem ou data comemorativa" : "são homenagens ou datas comemorativas"}.`}
        {dados.temas.length > LIMITE && ` Mostrando os ${LIMITE} temas com mais projetos.`}
      </p>
    </section>
  );
}
