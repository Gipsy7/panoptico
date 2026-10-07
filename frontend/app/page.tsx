import { BuscaParlamentar } from "@/components/busca-parlamentar";
import { CepForm } from "@/components/cep-form";
import { Marca } from "@/components/logo";

export default function Home() {
  return (
    <div className="flex flex-col items-center gap-10 pt-6 sm:pt-14">
      <div className="flex max-w-2xl flex-col items-center gap-5 text-center">
        {/* A marca como selo: se desenha uma vez ao carregar e não disputa com o texto. */}
        <Marca tamanho={56} animada traco={2.2} className="text-bronze" />
        <p className="sobretitulo">O panóptico, invertido</p>
        <h1 className="text-5xl leading-[1.04] text-balance sm:text-6xl">
          Quem te representa, às claras
        </h1>
        <p className="max-w-md text-lg leading-relaxed text-pretty text-muted-foreground">
          O panóptico era uma prisão em que um vigia via todos. Aqui é o contrário: todos podem
          ver quem os representa no Congresso, com dados oficiais.
        </p>
      </div>

      <div className="w-full max-w-md border-t border-foreground pt-6">
        <CepForm />
      </div>

      <div className="flex w-full max-w-md flex-col gap-2">
        <BuscaParlamentar rotulo="Ou procure um parlamentar pelo nome" />
      </div>
    </div>
  );
}
