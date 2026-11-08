import { Chapa, cargoDoVice } from "@/components/chapa";
import { FotoOuIniciais } from "@/components/eleitos-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import type { Chapa as ChapaApi, Executivo } from "@/lib/api";

/** Presidente, governador e prefeito eleitos, cada um com o vice (TSE). */
export function ExecutivoSecao({ dados, estado, cidade }: { dados: Executivo; estado: string; cidade: string | null }) {
  const chapas: { rotulo: string; chapa: ChapaApi | null }[] = [
    { rotulo: "Presidente", chapa: dados.presidente },
    { rotulo: `Governador de ${estado}`, chapa: dados.governador },
    ...(cidade ? [{ rotulo: `Prefeito de ${cidade}`, chapa: dados.prefeito }] : []),
  ];
  if (chapas.every((c) => !c.chapa)) return null;

  return (
    <section aria-labelledby="executivo-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="executivo-titulo" className="text-2xl">
          Executivo
        </h2>
        <p className="text-sm text-muted-foreground">
          Quem foi eleito para governar o país, o estado e a cidade, segundo o TSE.
        </p>
      </div>
      <ul className="grid grid-cols-1 border-t border-border lg:grid-cols-3 lg:gap-x-8">
        {chapas.map(({ rotulo, chapa }) =>
          chapa ? (
            <li key={rotulo} className="flex flex-col gap-2 border-b border-border py-3">
              <span className="sobretitulo">{rotulo}</span>
              <Chapa
                titular={{
                  nome: chapa.titular.nome_urna,
                  partido: chapa.titular.partido,
                  cargo: chapa.cargo,
                  href: `/eleito/${chapa.titular.id}`,
                  retrato: <FotoOuIniciais eleito={chapa.titular} tamanho={40} decorativa />,
                }}
                vice={
                  chapa.vice && {
                    nome: chapa.vice.nome_urna,
                    partido: chapa.vice.partido,
                    cargo: cargoDoVice(chapa.cargo),
                    href: `/eleito/${chapa.vice.id}`,
                    retrato: <FotoOuIniciais eleito={chapa.vice} tamanho={40} decorativa />,
                  }
                }
                rodape={`Eleitos juntos, na mesma chapa, em ${chapa.ano_eleicao}.`}
              />
            </li>
          ) : null,
        )}
      </ul>
      <p className="text-sm text-muted-foreground">
        Mudanças depois da eleição (renúncia, cassação, posse do vice) ainda não aparecem aqui.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
