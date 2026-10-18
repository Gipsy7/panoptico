import { AvisoErro } from "@/components/aviso-erro";

export default function NotFound() {
  return (
    <AvisoErro
      titulo="Página não encontrada"
      mensagem="O endereço pode estar errado ou o que você procura não está na nossa base. Tente buscar de novo pelo CEP."
    />
  );
}
