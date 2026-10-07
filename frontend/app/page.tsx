import { BuscaParlamentar } from "@/components/busca-parlamentar";
import { CepForm } from "@/components/cep-form";
import { Marca } from "@/components/logo";

export default function Home() {
  return (
    <div className="relative mx-auto flex max-w-md flex-col gap-8 pt-2 sm:pt-10">
      {/* A marca grande, ao fundo: os traços apontam para o centro da página, onde fica
          a busca. É decorativa (o significado está no texto). */}
      <div
        aria-hidden
        className="pointer-events-none absolute top-[-1rem] left-1/2 -z-10 -translate-x-1/2 text-primary/25"
      >
        <Marca tamanho={440} animada traco={0.45} />
      </div>

      <div className="flex flex-col gap-4 pt-16 text-center sm:pt-20">
        <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
          O panóptico, invertido
        </p>
        <h1 className="text-4xl leading-[1.05] font-semibold sm:text-5xl">
          Quem te representa, às claras
        </h1>
        <p className="text-lg leading-relaxed text-muted-foreground">
          O panóptico era uma prisão em que um vigia via todos. Aqui é o contrário: todos podem
          ver quem os representa no Congresso, com dados oficiais.
        </p>
      </div>

      <div className="rounded-2xl border border-border/80 bg-card/90 p-5 shadow-[0_1px_0_0_var(--border),0_12px_40px_-24px_oklch(0.36_0.1_330/0.35)] backdrop-blur-sm sm:p-6">
        <CepForm />
      </div>

      <div className="flex flex-col gap-2">
        <BuscaParlamentar rotulo="Ou procure um parlamentar pelo nome" />
      </div>
    </div>
  );
}
