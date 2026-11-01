#!/usr/bin/env bash
# Calcula COMET para varios modelos en una VM L4 de Colab y cierra la sesión.
#
# Sube los exámenes y resultados/profesores/NOMBRE/traducciones.json de cada
# modelo, corre colab/puntuar_comet.py y deja la nota de cada frase en
# resultados/profesores/NOMBRE/comet.json. Es el único cliente de su sesión.
#
# Uso: [EXAMEN=datos/examenes/externos.jsonl] colab/comet.sh NOMBRE [NOMBRE ...]
set -uo pipefail

[ $# -ge 1 ] || { echo "faltan los nombres"; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
name=comet
log="$root/resultados/profesores/comet-registro.txt"

trap 'colab stop -s "$name" >>"$log" 2>&1; echo "sesión parada" | tee -a "$log"' EXIT

remote() { echo "$1" | timeout 120 colab exec -s "$name" 2>&1; }
# Colab devuelve a veces 500 o 503 pasajeros al subir: se reintenta.
upload() {
  for try in 1 2 3 4; do
    colab upload -s "$name" "$1" "$2" >>"$log" 2>&1 && return 0
    sleep 20
  done
  return 1
}

colab new -s "$name" --gpu L4 >>"$log" 2>&1 || { echo "no se pudo crear la sesión" | tee -a "$log"; exit 1; }
upload "$root/${EXAMEN:-datos/examenes/entrada.jsonl}" /content/entrada.jsonl || { echo "no se pudo subir el examen" | tee -a "$log"; exit 1; }
upload "$root/colab/puntuar_comet.py" /content/puntuar_comet.py || { echo "no se pudo subir puntuar_comet.py" | tee -a "$log"; exit 1; }
for n in "$@"; do
  upload "$root/resultados/profesores/$n/traducciones.json" "/content/sistema-$n.json" || { echo "no se pudo subir $n" | tee -a "$log"; exit 1; }
done
# unbabel-comet va en un entorno aparte: instalado sobre el Python de Colab le baja
# de versión protobuf y numpy y rompe sus librerías. setuptools<81: torchmetrics aún usa pkg_resources.
setup='pip install -q uv && uv venv -q /content/cv && uv pip install -q --python /content/cv/bin/python unbabel-comet "setuptools<81"'
# La primera orden tras crear la VM a veces pierde la conexión y no lanza nada
# (2026-10-31): se reintenta hasta que exista el registro.
for try in 1 2 3; do
  remote "import subprocess; subprocess.Popen('($setup && /content/cv/bin/python -u /content/puntuar_comet.py) > /content/registro.txt 2>&1; echo FIN-PROCESO \$? >> /content/registro.txt', shell=True)" >>"$log"
  sleep 15
  timeout 120 colab ls -s "$name" /content 2>/dev/null | grep -qx registro.txt && break
done
timeout 120 colab ls -s "$name" /content 2>/dev/null | grep -qx registro.txt || { echo "COMET no arrancó" | tee -a "$log"; exit 1; }

start=$(date +%s)
while true; do
  sleep 60
  [ $(( $(date +%s) - start )) -ge 3600 ] && { echo "más de una hora: abandono" | tee -a "$log"; exit 1; }
  reg=$(remote "print('<<<INICIO>>>'); print(open('/content/registro.txt').read()[-2000:]); print('<<<FIN>>>')" | sed -n '/<<<INICIO>>>/,/<<<FIN>>>/p')
  [ -z "$reg" ] && continue
  echo "$reg" | tail -3 >>"$log"
  grep -q '^LISTO' <<<"$reg" && break
  # Cualquier error o el fin del proceso sin LISTO cuenta como fallo: la VM no debe quedar encendida.
  if grep -qE 'Traceback|^[A-Za-z.]*Error|^error:|Killed|FIN-PROCESO' <<<"$reg"; then
    remote "print(open('/content/registro.txt').read())" >>"$log"
    echo "COMET falló: ver $log" | tee -a "$log"
    exit 1
  fi
done
for n in "$@"; do
  colab download -s "$name" "/content/comet-$n.json" "$root/resultados/profesores/$n/comet.json" >>"$log" 2>&1 \
    || echo "no se pudo bajar $n" | tee -a "$log"
done
echo LISTO | tee -a "$log"
