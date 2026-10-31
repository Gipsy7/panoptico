#!/usr/bin/env bash
# Liga os avisos por Web Push no release: gera um par VAPID só do release e grava no .env sem
# exibir a chave privada, recria os serviços do release e semeia o detector, que não envia nada
# na primeira vez. Pode rodar de novo: reaproveita as chaves. Uso (na VPS, como root):
#   bash /opt/panoptico/deploy/vps/ligar-avisos-release.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
dc=(docker compose --profile release)

if ! grep -q '^VAPID_PRIVADA_RELEASE=.' .env; then
  chaves=$("${dc[@]}" exec -T api-release python - <<'PY'
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64(dados):
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


chave = ec.generate_private_key(ec.SECP256R1())
privada = chave.private_numbers().private_value.to_bytes(32, "big")
publica = chave.public_key().public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
)
print(b64(privada), b64(publica))
PY
  )
  read -r privada publica <<<"$chaves"
  sed -i '/^VAPID_PRIVADA_RELEASE=/d;/^VAPID_PUBLICA_RELEASE=/d;/^AVISOS_ATIVOS_RELEASE=/d' .env
  [ -z "$(tail -c1 .env)" ] || echo >>.env
  printf 'VAPID_PRIVADA_RELEASE=%s\nVAPID_PUBLICA_RELEASE=%s\n' "$privada" "$publica" >>.env
  unset chaves privada publica
fi
grep -q '^AVISOS_ATIVOS_RELEASE=true' .env || {
  sed -i '/^AVISOS_ATIVOS_RELEASE=/d' .env
  echo 'AVISOS_ATIVOS_RELEASE=true' >>.env
}

# A chave pública entra no site na hora do build.
nice -n 19 "${dc[@]}" build --no-cache web-release
"${dc[@]}" up -d --no-deps --no-build api-release web-release
for _ in $(seq 1 30); do
  "${dc[@]}" exec -T api-release python -c \
    "import urllib.request as u; u.urlopen('http://localhost:8000/saude', timeout=4)" >/dev/null 2>&1 && break
  sleep 2
done
"${dc[@]}" exec -T api-release python -m app.avisos_diario --semear
"${dc[@]}" exec -T api-release python -m app.avisos_diario --simular
echo "avisos ligados no release"
