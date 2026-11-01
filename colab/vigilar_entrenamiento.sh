#!/usr/bin/env bash
# Vigila un entrenamiento de colab/lanzar_entrenamiento.sh.
#
# Cada POLL s manda un `colab exec` mínimo: es lo que impide que Colab apague la
# VM (sin exec la apaga a los ~20 min, 2026-10-30). Si se cuelga da igual, se
# corta con timeout; nunca van dos a la vez. Todo lo demás usa `colab ls` y
# `colab download`, que siguen funcionando cuando los exec se cuelgan:
# - cada POLL s baja progreso.json (para estado.txt);
# - baja cada copia nueva (checkpoint-N con rng_state.pth, lo último que escribe
#   el Trainer) fichero a fichero a modelos/<nombre>/copias/checkpoint-N/, y
#   guarda solo las 2 últimas;
# - cuando aparecen los resultados finales en /content/salida, los baja y para la
#   sesión;
# - si en CHECK_FAIL s el progreso no avanza, baja el registro y, si el proceso
#   terminó con error (FIN-PROCESO distinto de 0), lo dice y para la sesión.
# Nunca para la sesión por falta de respuesta: solo al terminar o ante un fallo real.
# Si Colab dice 3 veces seguidas que la sesión no existe, avisa y termina.
#
# Uso: setsid nohup colab/vigilar_entrenamiento.sh NOMBRE [--sin-gguf]
# (colab/lanzar_entrenamiento.sh lo arranca solo tras lanzar la celda de entrenamiento)
set -uo pipefail

name=${1:?falta el nombre}
gguf=1
[ "${2:-}" = "--sin-gguf" ] && gguf=0
root=$(cd "$(dirname "$0")/.." && pwd)
out="$root/modelos/$name"
log="$out/registro-local.txt"
status="$out/estado.txt"
POLL=120
CHECK_FAIL=1200

say() { echo "$(date +%H:%M) $*" | tee -a "$log" >>"$status"; }
listing() { timeout 120 colab ls -s "$name" "$1" 2>/dev/null; }
get() {
  for try in 1 2 3; do
    timeout 900 colab download -s "$name" "$1" "$2" >>"$log" 2>&1 && [ -s "$2" ] && return 0
    sleep 20
  done
  return 1
}

say "vigilante sin núcleo en marcha"
last_step=-1
last_move=$(date +%s)
gone=0
while true; do
  sleep "$POLL"
  echo "print(1)" | timeout 90 colab exec -s "$name" >/dev/null 2>&1
  if timeout 120 colab sessions 2>/dev/null | grep -q "^\[$name\]"; then
    gone=0
  else
    gone=$((gone + 1))
    if [ "$gone" -ge 3 ]; then
      say "la VM de $name se apagó (Colab ya no la tiene): copias en $out/copias"
      exit 1
    fi
  fi
  if get /content/progreso.json "$out/progreso.json.nuevo"; then
    mv "$out/progreso.json.nuevo" "$out/progreso.json"
    line=$(python3 - "$out/progreso.json" <<'EOF'
import json, sys, time
p = json.load(open(sys.argv[1]))
h = p['historial']
loss = [e['loss'] for e in h if 'loss' in e][-2:]
ev = [round(e['eval_loss'], 4) for e in h if 'eval_loss' in e][-3:]
rate = p['segundos'] / max(1, p['paso'] - p.get('paso_inicio', 0))
left = rate * (p['pasos'] - p['paso'])
print('%d %s paso %d/%d falta %dh%02dm | loss %s | eval %s' % (p['paso'], time.strftime('%H:%M'), p['paso'], p['pasos'],
      left // 3600, left % 3600 // 60, loss, ev))
EOF
)
    step=${line%% *}
    echo "${line#* }" >"$status"
    if [ "$step" != "$last_step" ]; then last_step=$step; last_move=$(date +%s); fi
  fi

  # Copias nuevas, completas (con rng_state.pth), fichero a fichero.
  for ck in $(listing /content/checkpoints | grep -o 'checkpoint-[0-9]*' | sort -V); do
    [ -f "$out/copias/$ck/.completa" ] && continue
    files=$(listing "/content/checkpoints/$ck" | grep -v '/$')
    grep -q '^rng_state.pth$' <<<"$files" || continue
    mkdir -p "$out/copias/$ck"
    ok=1
    for f in $files; do
      get "/content/checkpoints/$ck/$f" "$out/copias/$ck/$f" || { ok=0; break; }
    done
    if [ "$ok" = 1 ]; then
      touch "$out/copias/$ck/.completa"
      echo "$(date +%H:%M) copia $ck bajada" >>"$log"
      # Solo las 2 últimas copias completas.
      ls "$out/copias" | grep '^checkpoint-' | sort -V | head -n -2 | sed "s|^|$out/copias/|" | xargs -r rm -rf
    fi
  done

  # ¿Terminó? Los resultados aparecen en /content/salida; muestras.json va antes que el GGUF.
  done_files=$(listing /content/salida)
  want="perdida.json"
  [ "$gguf" = 1 ] && want="modelo-Q4_K_M.gguf modelo-Q8_0.gguf $want"
  finished=1
  for f in $want; do grep -qx "$f" <<<"$done_files" || finished=0; done
  # Un GGUF existe mientras se escribe: solo cuenta como terminado si el registro dice LISTO.
  if [ "$finished" = 1 ] && get /content/registro.txt "$out/registro.txt" && tr '\r' '\n' <"$out/registro.txt" | grep -q '^LISTO'; then
    for f in $want muestras.json; do get "/content/salida/$f" "$out/$f" || say "no se pudo bajar $f"; done
    mkdir -p "$out/lora"
    for f in $(listing /content/salida/lora | grep -v '/$'); do get "/content/salida/lora/$f" "$out/lora/$f"; done
    missing=$(for f in $want; do [ -s "$out/$f" ] || echo "$f"; done)
    if [ -n "$missing" ]; then
      say "FALTAN ($missing): no paro la sesión $name para poder bajarlos a mano"
      exit 1
    fi
    for try in 1 2 3; do
      timeout 120 colab stop -s "$name" >>"$log" 2>&1
      timeout 120 colab sessions 2>/dev/null | grep -q "^\[$name\]" || break
      sleep 30
    done
    say "LISTO: resultados en $out; sesión parada"
    exit 0
  fi

  # ¿Falló? Si el progreso no avanza en un rato, se mira el final del registro.
  if [ $(( $(date +%s) - last_move )) -ge "$CHECK_FAIL" ]; then
    if get /content/registro.txt "$out/registro.txt"; then
      end=$(tr '\r' '\n' <"$out/registro.txt" | grep -o 'FIN-PROCESO [0-9]*' | tail -1)
      if [ -n "$end" ] && [ "$end" != "FIN-PROCESO 0" ]; then
        timeout 120 colab stop -s "$name" >>"$log" 2>&1
        say "el entrenamiento falló ($end): ver $out/registro.txt; sesión parada"
        exit 1
      fi
    fi
    last_move=$(date +%s)
  fi
done
