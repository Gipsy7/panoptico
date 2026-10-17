/**
 * Cabeçalho padrão das páginas internas: sobretítulo (bronze, versalete), título e subtítulo
 * em cinza. `children` entra depois do subtítulo (ex.: filtros de ano, selos).
 */
export function CabecalhoPagina({
  sobretitulo,
  titulo,
  subtitulo,
  children,
}: {
  sobretitulo: string;
  titulo: React.ReactNode;
  subtitulo?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex flex-col gap-[var(--esp-2)]">
      <p className="sobretitulo">{sobretitulo}</p>
      <h1 className="titulo-pagina">{titulo}</h1>
      {subtitulo && <p className="text-muted-foreground">{subtitulo}</p>}
      {children}
    </header>
  );
}
