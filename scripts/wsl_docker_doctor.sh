#!/usr/bin/env bash
set -euo pipefail

print_header() {
  echo "=== WSL Docker Doctor ==="
}

run_capture() {
  local output rc
  set +e
  output=$("$@" 2>&1)
  rc=$?
  set -e
  printf '%s\n' "$output"
  return "$rc"
}

print_header
notes=()

echo "uname -a: $(uname -a || echo 'unavailable')"
if command -v wslpath >/dev/null 2>&1; then
  echo "Windows path (pwd): $(wslpath -w . 2>/dev/null || echo 'n/a')"
else
  notes+=("wslpath not available; quoting paths is recommended.")
fi
if [[ -f /proc/version ]]; then
  echo "/proc/version: $(head -n1 /proc/version)"
fi

docker_info_ok=false
compose_ok=false
hello_world_ok=false
needs_group_fix=false
compose_v2=false
compose_legacy=false
socket_perm_ok=false
path_has_spaces=false
wsl_integration="likely_disabled"

# docker info
info_output=$(run_capture docker info)
if [[ $? -eq 0 ]]; then
  docker_info_ok=true
  echo "docker info: OK"
else
  notes+=("docker info failed: ${info_output%$'\n'}")
  echo "docker info: FAILED"
fi

# docker compose v2
compose_output=$(run_capture docker compose version || true)
if [[ $? -eq 0 ]]; then
  compose_v2=true
  compose_ok=true
  echo "docker compose v2: OK"
else
  notes+=("docker compose v2 unavailable: ${compose_output%$'\n'}")
  echo "docker compose v2: FAILED"
fi

# legacy docker-compose
legacy_output=$(run_capture docker-compose --version || true)
if [[ $? -eq 0 ]]; then
  compose_legacy=true
  compose_ok=true
  echo "docker-compose legacy: OK"
elif [[ -n "$legacy_output" ]]; then
  notes+=("docker-compose legacy unavailable: ${legacy_output%$'\n'}")
fi

# docker context
context_output=$(run_capture docker context ls || true)
echo "$context_output"

# socket snapshot
socket_json="{}"
if stat_output=$(stat -c '{"mode":"%a","user":"%U","group":"%G"}' /var/run/docker.sock 2>/dev/null); then
  socket_json="$stat_output"
  if [[ -r /var/run/docker.sock && -w /var/run/docker.sock ]]; then
    socket_perm_ok=true
  else
    notes+=("/var/run/docker.sock exists but current user lacks read/write access.")
  fi
else
  notes+=("/var/run/docker.sock missing or inaccessible.")
fi

# docker group membership
if id -nG 2>/dev/null | tr ' ' '\n' | grep -qx 'docker'; then
  echo "docker group membership: present"
else
  echo "docker group membership: MISSING"
  needs_group_fix=true
  notes+=("Add to docker group: sudo groupadd docker || true && sudo usermod -aG docker \"$USER\" && echo 'RESTART_SHELL_REQUIRED'")
fi

# hello world sanity
if $docker_info_ok; then
  hello_output=$(run_capture docker run --rm hello-world || true)
  if [[ $? -eq 0 ]]; then
    hello_world_ok=true
    echo "docker run hello-world: OK"
  else
    notes+=("docker run hello-world failed: ${hello_output%$'\n'}")
    echo "docker run hello-world: FAILED"
  fi
else
  notes+=("Skipping hello-world test because docker info failed.")
fi

# repo sanity
if [[ ! -f Makefile ]] || [[ ! -f README.md ]]; then
  notes+=("Run doctor from the repo root where Makefile and README.md are located.")
fi

if [[ $PWD == *" "* ]]; then
  path_has_spaces=true
  notes+=("Repository path contains spaces. Prefer cloning under ~/projects or quote docker volume mounts.")
fi

if grep -qi microsoft /proc/version 2>/dev/null; then
  if echo "$context_output" | grep -qi "desktop-linux"; then
    wsl_integration="likely_enabled"
  else
    wsl_integration="likely_disabled"
    notes+=("WSL integration not detected in docker context; enable your distro in Docker Desktop → Settings → Resources → WSL Integration.")
  fi
else
  wsl_integration="likely_enabled"
fi

status="ok"
if ! $docker_info_ok || ! $hello_world_ok || ! $socket_perm_ok; then
  status="error"
fi

notes_file=$(mktemp)
printf '%s\n' "${notes[@]-}" > "$notes_file"

export STATUS="$status"
export DOCKER_INFO_OK="$docker_info_ok"
export COMPOSE_OK="$compose_ok"
export HELLO_WORLD_OK="$hello_world_ok"
export NEEDS_GROUP_FIX="$needs_group_fix"
export COMPOSE_V2="$compose_v2"
export COMPOSE_LEGACY="$compose_legacy"
export SOCKET_JSON="$socket_json"
export PATH_HAS_SPACES="$path_has_spaces"
export WSL_INTEGRATION="$wsl_integration"
export SOCKET_PERM_OK="$socket_perm_ok"
export NOTES_FILE="$notes_file"

python3 - <<'PY'
import json
import os

def to_bool(name: str) -> bool:
    return os.environ.get(name, "false").lower() == "true"

notes_file = os.environ.get("NOTES_FILE")
notes: list[str] = []
if notes_file and os.path.exists(notes_file):
    with open(notes_file, encoding="utf-8") as handle:
        notes = [line.rstrip("\n") for line in handle if line.strip()]

socket_payload = {}
try:
    socket_payload = json.loads(os.environ.get("SOCKET_JSON", "{}"))
except json.JSONDecodeError:
    socket_payload = {}

payload = {
    "status": os.environ.get("STATUS", "error"),
    "docker_info_ok": to_bool("DOCKER_INFO_OK"),
    "compose_ok": to_bool("COMPOSE_OK"),
    "hello_world_ok": to_bool("HELLO_WORLD_OK"),
    "compose_v2": to_bool("COMPOSE_V2"),
    "compose_legacy": to_bool("COMPOSE_LEGACY"),
    "socket": socket_payload,
    "socket_perm_ok": to_bool("SOCKET_PERM_OK"),
    "needs_group_fix": to_bool("NEEDS_GROUP_FIX"),
    "wsl_integration": os.environ.get("WSL_INTEGRATION", "likely_disabled"),
    "path_has_spaces": to_bool("PATH_HAS_SPACES"),
    "notes": notes,
}

print(json.dumps(payload))
PY

rm -f "$notes_file"

if [[ "$status" == "ok" ]]; then
  exit 0
else
  exit 1
fi
