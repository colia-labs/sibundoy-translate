#!/usr/bin/env bash
# Traduce una parte de la cola masiva con el profesor en su propia VM de Colab.
#
# Sube la entrada, el prompt y las opciones de petición, lanza
# colab/traducir_masivo.py en segundo plano y, mientras trabaja, baja cada
# COPY s lo traducido a datos/masivo/salida-<nombre>.jsonl: si Colab corta,
# no se pierde más que ese rato, y al relanzar con la misma salida la VM
# nueva sigue donde quedó. Al terminar, o ante cualquier fallo, para la sesión.
#
# Es el único cliente de su sesión. El avance queda en datos/masivo/estado-<nombre>.txt.
#
# Uso: colab/lanzar_masivo.sh NOMBRE ENTRADA MODELO PETICIÓN_JSON [argumentos extra de vllm serve]
set -uo pipefail

name=${1:?falta el nombre}
input=${2:?falta la entrada}
model=${3:?falta el modelo}
request=${4:?faltan las opciones de petición}
shift 4
root=$(cd "$(dirname "$0")/.." && pwd)
dir="$root/datos/masivo"
out="$dir/salida-$name.jsonl"
log="$dir/registro-$name.txt"
status="$dir/estado-$name.txt"
printf '%s\n' "$request" >"$dir/peticion-$name.json"
POLL=60
COPY=900
MAX_SILENCE=1800
MAX_TOTAL=$((8 * 3600))

trap 'colab stop -s "$name" >>"$log" 2>&1; echo "$(date +%H:%M) sesión parada" | tee -a "$log" >>"$status"' EXIT

remote() { echo "$1" | timeout 120 colab exec -s "$name" 2>&1; }
upload() {
  for try in 1 2 3 4; do
    colab upload -s "$name" "$1" "$2" >>"$log" 2>&1 && return 0
    sleep 20
  done
  return 1
}
# Baja lo traducido a un fichero aparte y solo reemplaza la copia local si trae más líneas.
fetch() {
  colab download -s "$name" /content/salida/resultado.jsonl "$out.nuevo" >>"$log" 2>&1 || return 1
  local new old
  new=$(wc -l <"$out.nuevo" 2>/dev/null || echo 0)
  old=$(wc -l <"$out" 2>/dev/null || echo 0)
  if [ "$new" -ge "$old" ]; then mv "$out.nuevo" "$out"; else rm -f "$out.nuevo"; fi
}

colab new -s "$name" --gpu G4 >>"$log" 2>&1 || { echo "$(date +%H:%M) no se pudo crear la sesión" | tee -a "$log" >"$status"; exit 1; }
remote "import os; os.makedirs('/content/salida', exist_ok=True)" >>"$log"
upload "$input" /content/entrada.jsonl || { echo "no se pudo subir la entrada" | tee -a "$log" >"$status"; exit 1; }
upload "$root/colab/profesor.md" /content/profesor.md || exit 1
upload "$root/colab/traducir_masivo.py" /content/traducir_masivo.py || exit 1
upload "$dir/peticion-$name.json" /content/peticion.json || exit 1
# Si ya hay algo traducido de una VM anterior, la nueva sigue desde ahí.
if [ -s "$out" ]; then
  upload "$out" /content/salida/resultado.jsonl || { echo "no se pudo subir lo ya traducido" | tee -a "$log" >"$status"; exit 1; }
fi
remote "import subprocess; subprocess.Popen('nohup python3 -u /content/traducir_masivo.py $model $* > /content/registro.txt 2>&1; echo FIN-PROCESO \$? >> /content/registro.txt', shell=True)" >>"$log"
echo "$(date +%H:%M) traduciendo $(basename "$input") con $model" | tee -a "$log" >"$status"

start=$(date +%s)
last_ok=$start
last_copy=$start
while true; do
  sleep "$POLL"
  now=$(date +%s)
  if [ $((now - start)) -ge "$MAX_TOTAL" ]; then
    fetch
    echo "$(date +%H:%M) más de $MAX_TOTAL s: paro (lo traducido está en $out)" | tee -a "$log" >"$status"
    exit 1
  fi
  raw=$(remote "import os; print('<<<INICIO>>>'); print(open('/content/registro.txt').read()[-1500:] if os.path.exists('/content/registro.txt') else 'aún sin registro'); print('<<<FIN>>>')")
  reg=$(sed -n '/<<<INICIO>>>/,/<<<FIN>>>/p' <<<"$raw" | grep -v '^<<<\|^$')
  if [ -z "$reg" ]; then
    echo "$(date +%H:%M) respuesta sin registro: $(tail -c 300 <<<"$raw" | tr '\n' ' ')" >>"$log"
    if [ $((now - last_ok)) -ge "$MAX_SILENCE" ]; then
      echo "$(date +%H:%M) Colab no responde: abandono" | tee -a "$log" >"$status"
      exit 1
    fi
    continue
  fi
  last_ok=$now
  echo "$(date +%H:%M) $(tail -1 <<<"$reg") | copia local: $(wc -l <"$out" 2>/dev/null || echo 0) unidades" >"$status"
  if grep -q '^LISTO' <<<"$reg"; then
    break
  fi
  # Cualquier error o el fin del proceso sin LISTO es un fallo: la VM no debe quedar encendida.
  if grep -qE 'Traceback|^[A-Za-z.]*Error|vLLM terminó|vLLM no arrancó|Killed|FIN-PROCESO' <<<"$reg"; then
    fetch
    remote "print(open('/content/registro.txt').read()); print(open('/content/vllm.txt').read()[-6000:])" >"$dir/fallo-$name.txt"
    echo "$(date +%H:%M) falló: ver $dir/fallo-$name.txt (lo traducido está en $out)" | tee -a "$log" >"$status"
    exit 1
  fi
  if [ $((now - last_copy)) -ge "$COPY" ]; then
    fetch && last_copy=$now
  fi
done

for try in 1 2 3; do
  fetch && break
  sleep 20
done
echo "$(date +%H:%M) LISTO: $(wc -l <"$out") unidades en $out" | tee -a "$log" >"$status"
