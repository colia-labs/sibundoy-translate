#!/usr/bin/env bash
# Entrena en Colab con el entrenamiento en un proceso aparte y la VM viva a base
# de `colab exec` periódicos (los hace colab/vigilar_entrenamiento.sh).
#
# Por qué (2026-10-30): Colab apaga la VM a los ~20 min si ningún cliente le
# manda órdenes, aunque el núcleo esté ocupado. Una celda larga sin órdenes desde
# fuera cayó así; lo que mantiene viva la VM son los exec periódicos, aunque
# algunos se cuelguen.
#   1. prepara la VM: sube datos y, si hay, la última copia (en trozos de 50 MB);
#   2. lanza entrenar.py con Popen y comprueba que arrancó (/content/celda-iniciada);
#   3. el proceso añade FIN-PROCESO al registro al terminar;
#   4. el seguimiento lo hace colab/vigilar_entrenamiento.sh.
#
# Lánzalo con setsid nohup para que no dependa de la sesión que lo arranca.
# Uso: colab/lanzar_entrenamiento.sh NOMBRE GPU DATOS [argumentos de entrenar.py]
set -uo pipefail

name=${1:?falta el nombre}
gpu=${2:?falta la GPU}
data=${3:?faltan los datos}
shift 3
root=$(cd "$(dirname "$0")/.." && pwd)
out="$root/modelos/$name"
mkdir -p "$out/copias"
rm -f "$out"/perdida.json "$out"/modelo-*.gguf "$out"/muestras.json
log="$out/registro-local.txt"
status="$out/estado.txt"

say() { echo "$(date +%H:%M) $*" | tee -a "$log" >>"$status"; }
fail() { say "$*"; colab stop -s "$name" >>"$log" 2>&1; say "sesión parada"; exit 1; }
remote() { echo "$1" | timeout 300 colab exec -s "$name" 2>&1; }
ask() { remote "print('<<<INICIO>>>')
$1
print('<<<FIN>>>')" | sed -n '/<<<INICIO>>>/,/<<<FIN>>>/p' | grep -v '^<<<'; }
ask_retry() {
  local r
  for try in 1 2 3 4; do
    r=$(ask "$1")
    [ -n "$r" ] && { echo "$r"; return 0; }
    sleep 15
  done
  return 1
}
upload() {
  for try in 1 2 3 4; do
    colab upload -s "$name" "$1" "$2" >>"$log" 2>&1 && return 0
    sleep 20
  done
  return 1
}
upload_big() {
  local parts="$out/trozos-subida" size
  rm -rf "$parts"; mkdir -p "$parts"
  split -b 50M -d -a 3 "$1" "$parts/trozo-"
  ask_retry "import os, shutil; shutil.rmtree('/content/trozos', ignore_errors=True); os.makedirs('/content/trozos'); print('ok')" >/dev/null
  for p in "$parts"/trozo-*; do
    upload "$p" "/content/trozos/$(basename "$p")" || { rm -rf "$parts"; return 1; }
  done
  rm -rf "$parts"
  size=$(ask_retry "import glob, os
with open('$2', 'wb') as out:
    for p in sorted(glob.glob('/content/trozos/trozo-*')):
        out.write(open(p, 'rb').read())
print(os.path.getsize('$2'))")
  echo "unida $2: $size de $(stat -c %s "$1") bytes" >>"$log"
  [ "$size" = "$(stat -c %s "$1")" ]
}
exists() { timeout 120 colab ls -s "$name" /content 2>/dev/null | grep -qx "$1"; }

colab new -s "$name" --gpu "$gpu" >>"$log" 2>&1 || { say "no se pudo crear la sesión"; exit 1; }
upload_big "$root/$data" /content/entrenamiento.jsonl || fail "no se pudo subir los datos"
upload "$root/scripts/prompt.py" /content/prompt.py || fail "no se pudo subir prompt.py"
upload "$root/colab/entrenar.py" /content/entrenar.py || fail "no se pudo subir entrenar.py"

# Última copia completa (la marca .completa la pone el vigilante). Se ordena por nombre.
last=$(ls "$out/copias" 2>/dev/null | grep '^checkpoint-[0-9]*$' | while read -r d; do [ -f "$out/copias/$d/.completa" ] && echo "$d"; done | sort -V | tail -1)
if [ -n "$last" ]; then
  (cd "$out/copias" && rm -f "$last.zip" && zip -q -r -0 "$last.zip" "$last" -x "$last/.completa")
  upload_big "$out/copias/$last.zip" /content/copia.zip || fail "no se pudo subir la copia $last"
  rm -f "$out/copias/$last.zip"
  found=$(ask_retry "import os, zipfile; os.makedirs('/content/checkpoints', exist_ok=True); zipfile.ZipFile('/content/copia.zip').extractall('/content/checkpoints'); print(' '.join(os.listdir('/content/checkpoints')))")
  [[ " $found " == *" $last "* ]] || fail "no se pudo descomprimir la copia $last (hay: $found)"
  say "sigo desde $last"
fi

# entrenar.py en su propio grupo de procesos: el núcleo queda libre para los exec.
start="import os, subprocess, time
if not os.path.exists('/content/celda-iniciada'):
    open('/content/celda-iniciada', 'w').write(time.strftime('%H:%M:%S'))
    subprocess.Popen(['bash', '-c', 'python3 -u /content/entrenar.py $* > /content/registro.txt 2>&1; rc=\$?; printf \"\\\\nFIN-PROCESO %d\\\\n\" \$rc >> /content/registro.txt'], start_new_session=True)
print('lanzado')"
for try in 1 2 3; do
  echo "$start" | timeout 120 colab exec -s "$name" >>"$log" 2>&1
  sleep 10
  exists celda-iniciada && break
done
exists celda-iniciada || fail "el entrenamiento no arrancó"
sleep 30
exists registro.txt || fail "el entrenamiento no escribe registro"
say "entrenando en $gpu (proceso aparte, exec cada 2 min): $*"

gguf=""
[[ " $* " == *" --sin-gguf "* ]] && gguf="--sin-gguf"
exec "$root/colab/vigilar_entrenamiento.sh" "$name" $gguf
