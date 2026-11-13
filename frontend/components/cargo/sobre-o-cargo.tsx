import { FonteRodape } from "@/components/fonte-rodape";
import {
  CARGOS,
  CF_CONFERIDA_EM,
  CF_NOME,
  CF_URL,
  FAIXAS_VEREADOR,
  type CargoId,
  type ItemComArtigo,
  textoDoCargo,
} from "@/lib/cargos";

function Lista({ titulo, itens }: { titulo: string; itens: ItemComArtigo[] }) {
  return (
    <div className="flex flex-col gap-1">
      <h2 className="font-sans text-base font-semibold tracking-normal">{titulo}</h2>
      <ul className="flex list-disc flex-col gap-1 pl-5">
        {itens.map((i) => (
          <li key={i.texto}>
            {i.texto} <span className="text-xs text-muted-foreground">({i.artigo})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * "Sobre o cargo", recolhido, logo abaixo da linha do cargo no cabeçalho do perfil: o que o
 * cargo faz, o que pode, o que não pode e quanto ganha, com o artigo da Constituição em cada
 * frase. Descreve a regra do cargo, não a pessoa. `df` usa os textos do Distrito Federal.
 */
export function SobreOCargo({ cargo, df = false }: { cargo: CargoId; df?: boolean }) {
  const c = CARGOS[cargo];
  const t = textoDoCargo(c, df);
  const nome = t.nome.toLowerCase();
  const fontesDiferentes = c.ganha.fonte.url !== CF_URL;
  return (
    <details className="max-w-prose text-sm">
      <summary className="alvo-44 inline-flex cursor-pointer items-center font-medium underline underline-offset-4">
        Sobre o cargo de {nome}
      </summary>
      <div className="flex flex-col gap-3 pb-2 pt-1">
        <p className="text-muted-foreground">
          O que a Constituição diz que o cargo pode, não pode e paga. Vale para o cargo, não avalia a pessoa.
        </p>
        <div className="flex flex-col gap-1">
          <h2 className="font-sans text-base font-semibold tracking-normal">O que faz</h2>
          <p>{t.faz}</p>
          <p className="text-xs text-muted-foreground">Termo oficial: {t.fazOficial}</p>
        </div>
        <Lista titulo="O que pode" itens={c.pode} />
        <Lista titulo="O que não pode" itens={c.naoPode} />
        <div className="flex flex-col gap-1">
          <h2 className="font-sans text-base font-semibold tracking-normal">Quanto ganha</h2>
          <p>
            {c.ganha.texto} <span className="text-xs text-muted-foreground">({c.ganha.artigo})</span>
          </p>
          {cargo === "vereador" && (
            <ul className="flex list-disc flex-col gap-0.5 pl-5">
              {FAIXAS_VEREADOR.map((f) => (
                <li key={f.rotulo}>
                  Cidade {f.rotulo}: até {f.percentual}% do deputado estadual
                </li>
              ))}
            </ul>
          )}
          {fontesDiferentes && <FonteRodape fonte={c.ganha.fonte.nome} url={c.ganha.fonte.url} />}
        </div>
        <FonteRodape fonte={CF_NOME} url={CF_URL} atualizadoEm={CF_CONFERIDA_EM} />
      </div>
    </details>
  );
}
