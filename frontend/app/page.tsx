import { BuscaParlamentar } from "@/components/busca-parlamentar";
import { CepForm } from "@/components/cep-form";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-md flex-col gap-8 pt-6 sm:pt-16">
      <div className="flex flex-col gap-3 text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Quem te representa, às claras
        </h1>
        <p className="text-lg text-muted-foreground">
          Veja seus deputados federais e senadores, com dados oficiais.
        </p>
      </div>
      <CepForm />
      <div className="flex flex-col gap-2 border-t pt-6">
        <BuscaParlamentar rotulo="Ou procure um parlamentar pelo nome" />
      </div>
    </div>
  );
}
