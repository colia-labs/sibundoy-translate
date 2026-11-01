#!/usr/bin/env bash
# Prueba un modelo como profesor en su propia VM de Colab y cierra la sesión.
#
# Sube los exámenes (datos/examenes/entrada.jsonl), el prompt de profesor y las
# opciones de petición, lanza colab/profesor.py en
# segundo plano, espera a que termine, baja las traducciones a
# resultados/profesores/<nombre>/ y para la sesión.
#
# Es el único cliente de su sesión: varias pruebas a la vez
# van en sesiones distintas. El avance queda en resultados/profesores/<nombre>/estado.txt.
#
# Uso: colab/probar_profesor.sh NOMBRE GPU MODELO PETICIÓN_JSON [argumentos extra de vllm serve]
# PETICIÓN_JSON: ver colab/profesor.py.
# Con EXAMEN=datos/examenes/externos.jsonl usa los exámenes públicos de dominio.
# Con SCRIPT=ruta sube ese script en lugar de colab/profesor.py.
# Con SUBIR_TOKEN_HF=1 sube el token de Hugging Face del portátil, para modelos
# con acceso restringido. Solo vive en la VM, que se borra al cerrarse.
set -uo pipefail

name=${1:?falta el nombre}
gpu=${2:?falta la GPU}
model=${3:?falta el modelo}
request=${4:?faltan las opciones de petición}
shift 4
root=$(cd "$(dirname "$0")/.." && pwd)
out="$root/resultados/profesores/$name"
mkdir -p "$out"
echo "$request" >"$out/peticion.json"
log="$out/registro-local.txt"
status="$out/estado.txt"
POLL=60
MAX_SILENCE=1800
MAX_TOTAL=7200

trap 'colab stop -s "$name" >>"$log" 2>&1; echo "sesión parada" | tee -a "$log"' EXIT

remote() { echo "$1" | timeout 120 colab exec -s "$name" 2>&1; }

read_remote_log() {
  remote "import os
t = open('/content/registro.txt').read()[-1500:]
v = open('/content/vllm.txt').read()[-1500:] if os.path.exists('/content/vllm.txt') else ''
print('<<<INICIO>>>'); print(t); print('--- vllm ---'); print(v); print('<<<FIN>>>')" | sed -n '/<<<INICIO>>>/,/<<<FIN>>>/p'
}

colab new -s "$name" --gpu "$gpu" >>"$log" 2>&1 || { echo "no se pudo crear la sesión" | tee -a "$log" "$status"; exit 1; }
remote "import subprocess; print(subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader'],capture_output=True,text=True).stdout)" | tee -a "$log"
for f in "${EXAMEN:-datos/examenes/entrada.jsonl}:examen.jsonl" "colab/profesor.md:profesor.md" "${SCRIPT:-colab/profesor.py}:profesor.py" "resultados/profesores/$name/peticion.json:peticion.json"; do
  colab upload -s "$name" "$root/${f%%:*}" "/content/${f##*:}" >>"$log" 2>&1 || { echo "no se pudo subir ${f%%:*}" | tee -a "$log" "$status"; exit 1; }
done
if [ "${SUBIR_TOKEN_HF:-0}" = 1 ]; then
  colab upload -s "$name" "$HOME/.cache/huggingface/token" /content/hf_token >>"$log" 2>&1 || { echo "no se pudo subir el token" | tee -a "$log" "$status"; exit 1; }
fi
# La primera orden tras crear la VM a veces pierde la conexión y no lanza nada
# (2026-10-31): se reintenta hasta que exista el registro.
for try in 1 2 3; do
  remote "import subprocess; subprocess.Popen('nohup python3 -u /content/profesor.py $model $* > /content/registro.txt 2>&1 &', shell=True)" >>"$log"
  sleep 15
  timeout 120 colab ls -s "$name" /content 2>/dev/null | grep -qx registro.txt && break
done
timeout 120 colab ls -s "$name" /content 2>/dev/null | grep -qx registro.txt || { echo "$(date +%H:%M) no arrancó" | tee -a "$log" "$status"; exit 1; }
echo "$(date +%H:%M) probando $model en $gpu" | tee -a "$log" >"$status"

start=$(date +%s)
last_ok=$start
while true; do
  sleep "$POLL"
  now=$(date +%s)
  if [ $((now - start)) -ge "$MAX_TOTAL" ]; then
    echo "$(date +%H:%M) más de $MAX_TOTAL s: abandono" | tee -a "$log" "$status"
    exit 1
  fi
  text=$(read_remote_log)
  if [ -z "$text" ]; then
    if [ $((now - last_ok)) -ge "$MAX_SILENCE" ]; then
      echo "Colab no responde: abandono" | tee -a "$log" "$status"
      exit 1
    fi
    continue
  fi
  last_ok=$now
  # El registro de vLLM trae avisos con trazas que no son fallos: solo cuenta el de profesor.py,
  # que termina con error si vLLM muere.
  reg=$(sed -n '/<<<INICIO>>>/,/--- vllm ---/p' <<<"$text" | grep -v '^<<<\|^--- vllm\|^$')
  echo "$(date +%H:%M) $(tail -1 <<<"$reg")" >"$status"
  tail -c 600 <<<"$text" >>"$log"
  if grep -q '^LISTO' <<<"$reg"; then
    break
  fi
  if grep -qE 'Traceback|vLLM terminó|vLLM no arrancó|Killed|out of memory|OutOfMemory|Error' <<<"$reg"; then
    remote "print(open('/content/registro.txt').read()); print(open('/content/vllm.txt').read()[-6000:])" >"$out/fallo.txt"
    echo "$(date +%H:%M) falló: ver $out/fallo.txt" | tee -a "$log" "$status"
    exit 1
  fi
done

for try in 1 2 3; do
  colab download -s "$name" /content/salida/traducciones.json "$out/traducciones.json" >>"$log" 2>&1 && [ -s "$out/traducciones.json" ] && break
  sleep 20
done
[ -s "$out/traducciones.json" ] || { trap - EXIT; echo "FALTA traducciones.json: la sesión $name sigue abierta" | tee -a "$log" "$status"; exit 1; }
echo "$(date +%H:%M) LISTO" | tee -a "$log" "$status"
