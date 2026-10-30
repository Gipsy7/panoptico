// Service worker dos avisos do Panóptico. Arquivo à parte, sem bundler e sem imports.
// O texto vem do servidor: {"titulo", "corpo", "caminho"}. Nada é guardado em cache aqui.

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (evento) => evento.waitUntil(self.clients.claim()));

// Só caminho do próprio site; qualquer outra coisa vira a página de avisos.
function caminhoDoSite(caminho) {
  if (typeof caminho !== "string" || !caminho.startsWith("/") || caminho.startsWith("//") || caminho.includes("\\")) {
    return "/avisos";
  }
  return caminho;
}

self.addEventListener("push", (evento) => {
  let dados = {};
  try {
    dados = evento.data ? evento.data.json() : {};
  } catch {
    dados = {};
  }
  const titulo = typeof dados.titulo === "string" && dados.titulo ? dados.titulo : "Panóptico";
  const corpo = typeof dados.corpo === "string" ? dados.corpo : "";
  // Todo push precisa mostrar uma notificação (o iPhone cancela os avisos de quem não mostra).
  evento.waitUntil(
    self.registration.showNotification(titulo, {
      body: corpo,
      icon: "/icone-192.png",
      tag: "resumo-do-dia",
      data: { caminho: caminhoDoSite(dados.caminho) },
    }),
  );
});

self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  const alvo = new URL(caminhoDoSite(evento.notification.data && evento.notification.data.caminho), self.location.origin).href;
  evento.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((abas) => {
      const aba = abas.find((a) => a.url.startsWith(self.location.origin));
      if (aba) {
        return aba.focus().then(
          (focada) => (focada && "navigate" in focada ? focada.navigate(alvo) : undefined),
          () => undefined,
        );
      }
      return self.clients.openWindow(alvo);
    }),
  );
});
