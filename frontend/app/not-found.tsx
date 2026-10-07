import { AvisoErro } from "@/components/aviso-erro";

export default function NotFound() {
  return (
    <AvisoErro
      titulo="Página não encontrada"
      mensagem="O endereço pode estar errado ou o parlamentar não está na nossa base."
    />
  );
}
