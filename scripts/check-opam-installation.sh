#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VERSIONS_FILE="${REPO_ROOT}/opam/versions.env"

if [[ ! -f "${VERSIONS_FILE}" ]]; then
  printf 'ERROR: version file is missing: %s\n' "${VERSIONS_FILE}" >&2
  exit 1
fi

# shellcheck source=opam/versions.env
source "${VERSIONS_FILE}"

switch_name=autodeduct-31
prefix="${HOME}/.local/share/autodeduct"
run_quick=false
run_full=false
run_cleanup_self_test_mode=false
run_parser_self_test_mode=false
run_wp_result_self_test_mode=false
run_backend_error_self_test_mode=false
run_phase_status_self_test_mode=false

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_version_metadata() {
  : "${OPAM_ARCHIVE_MIRROR:?OPAM_ARCHIVE_MIRROR is missing from ${VERSIONS_FILE}}"
  : "${OCAML_VERSION:?OCAML_VERSION is missing from ${VERSIONS_FILE}}"
  : "${FRAMA_C_VERSION:?FRAMA_C_VERSION is missing from ${VERSIONS_FILE}}"
  : "${SAIDA_REF:?SAIDA_REF is missing from ${VERSIONS_FILE}}"
  : "${SAIDA_COMMIT:?SAIDA_COMMIT is missing from ${VERSIONS_FILE}}"
  : "${ISP_REF:?ISP_REF is missing from ${VERSIONS_FILE}}"
  : "${ISP_COMMIT:?ISP_COMMIT is missing from ${VERSIONS_FILE}}"
  : "${TRICERA_REF:?TRICERA_REF is missing from ${VERSIONS_FILE}}"
  : "${EXAMPLES_REF:?EXAMPLES_REF is missing from ${VERSIONS_FILE}}"
  : "${EXAMPLES_COMMIT:?EXAMPLES_COMMIT is missing from ${VERSIONS_FILE}}"
}

require_version_metadata

info() {
  printf 'INFO: %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: scripts/check-opam-installation.sh [OPTIONS]

Options:
  --switch NAME       OPAM switch name (default: autodeduct-31)
  --prefix DIRECTORY  Managed prefix (default: $HOME/.local/share/autodeduct)
  --quick             Run the quick environment check
  --full              Run the full paper-model smoke test
  --self-test-cleanup Run the temporary-directory cleanup self-test
  --self-test-parser  Run the Frama-C parser-command self-test
  --self-test-wp-result Run the WP-result parser self-test
  --self-test-backend-errors Run the retained TriCera error self-test
  --self-test-phase-status Run the phase exit-status self-test
  -h, --help          Show this help

If no mode is selected, --quick is used.
The full test uses the paper profile by default. Set
AUTODEDUCT_SMOKE_PROFILE=library-entry to use the separate strict profile.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --switch)
      [[ $# -ge 2 ]] || die "--switch needs a value"
      switch_name=$2
      shift 2
      ;;
    --prefix)
      [[ $# -ge 2 ]] || die "--prefix needs a value"
      prefix=$2
      shift 2
      ;;
    --quick)
      run_quick=true
      shift
      ;;
    --full)
      run_full=true
      shift
      ;;
    --self-test-cleanup)
      run_cleanup_self_test_mode=true
      shift
      ;;
    --self-test-parser)
      run_parser_self_test_mode=true
      shift
      ;;
    --self-test-wp-result)
      run_wp_result_self_test_mode=true
      shift
      ;;
    --self-test-backend-errors)
      run_backend_error_self_test_mode=true
      shift
      ;;
    --self-test-phase-status)
      run_phase_status_self_test_mode=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

if [[ "${run_quick}" == false && "${run_full}" == false && "${run_cleanup_self_test_mode}" == false && "${run_parser_self_test_mode}" == false && "${run_wp_result_self_test_mode}" == false && "${run_backend_error_self_test_mode}" == false && "${run_phase_status_self_test_mode}" == false ]]; then
  run_quick=true
fi

if [[ "${prefix}" != /* ]]; then
  prefix="$(pwd -P)/${prefix}"
fi
if [[ "${run_cleanup_self_test_mode}" == true || "${run_parser_self_test_mode}" == true || "${run_wp_result_self_test_mode}" == true || "${run_backend_error_self_test_mode}" == true || "${run_phase_status_self_test_mode}" == true ]]; then
  prefix="$(pwd -P)"
else
  prefix="$(cd -- "${prefix}" 2>/dev/null && pwd -P)" || die "prefix does not exist: ${prefix}"
fi

OPAM_ROOT="${prefix}/opam-root"
OPAM_INIT_CONFIG="${prefix}/opamrc"
BIN_ROOT="${prefix}/bin"
MANIFEST_FILE="${prefix}/installation-manifest.txt"
WHY3_CONFIG="${prefix}/why3.conf"

require_command() {
  local command_name=$1
  command -v "${command_name}" >/dev/null 2>&1 || die "missing command '${command_name}'"
}

opam_wrapper() {
  opam --cli=2.1 "$@"
}

opam_root_cmd() {
  OPAMROOT="${OPAM_ROOT}" opam_wrapper "$@"
}

opam_switch_cmd() {
  OPAMROOT="${OPAM_ROOT}" OPAMSWITCH="${switch_name}" opam_wrapper "$@"
}

opam_exec() {
  OPAMROOT="${OPAM_ROOT}" OPAMSWITCH="${switch_name}" opam_wrapper exec -- "$@"
}

switch_exists() {
  opam_root_cmd switch --short list | awk -v name="${switch_name}" '$1 == name { found=1 } END { exit found ? 0 : 1 }'
}

manifest_value() {
  local key=$1
  awk -F= -v key="${key}" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "${MANIFEST_FILE}"
}

check_manifest_value() {
  local key=$1
  local expected=$2
  local actual
  actual="$(manifest_value "${key}")"
  [[ "${actual}" == "${expected}" ]] || die "manifest ${key} is '${actual}', expected '${expected}'"
}

check_exact_source_commit() {
  local directory=$1
  local expected=$2
  [[ -d "${directory}/.git" ]] || die "Git checkout is missing: ${directory}"
  local actual
  actual="$(git -C "${directory}" rev-parse HEAD)"
  [[ "${actual}" == "${expected}" ]] || die "${directory} is at ${actual}, expected ${expected}"
}

check_managed_opamrc() {
  [[ -f "${OPAM_INIT_CONFIG}" ]] || die "managed OPAM init config is missing: ${OPAM_INIT_CONFIG}"
  cmp -s <(printf 'opam-version: "2.0"\narchive-mirrors: [\n  "%s"\n]\n' "${OPAM_ARCHIVE_MIRROR}") "${OPAM_INIT_CONFIG}" || die "managed OPAM init config does not match ${OPAM_ARCHIVE_MIRROR}: ${OPAM_INIT_CONFIG}"
}

check_archive_mirror() {
  local mirrors
  if ! mirrors="$(opam_root_cmd option --global archive-mirrors 2>&1)"; then
    printf 'OPAM archive-mirrors output:\n%s\n' "${mirrors}" >&2
    die "could not read OPAM archive-mirrors for root ${OPAM_ROOT}"
  fi
  grep -Fqx "\"${OPAM_ARCHIVE_MIRROR}\"" <<<"${mirrors}" || die "OPAM archive-mirrors does not contain ${OPAM_ARCHIVE_MIRROR}"
}

check_pin_target() {
  local package=$1
  local expected_commit=$2
  local label=$3
  local pin_output=$4
  local pin_line
  local pin_target

  pin_line="$(awk -v package="${package}" 'index($1, package ".") == 1 { print; exit }' <<<"${pin_output}")"
  [[ -n "${pin_line}" ]] || die "OPAM ${label} pin is missing for switch ${switch_name}"

  pin_target="$(sed -nE 's/.*git\+[^[:space:]]+#([^[:space:]]+).*/\1/p' <<<"${pin_line}")"
  [[ -n "${pin_target}" ]] || die "OPAM ${label} pin has no Git target: ${pin_line}"
  case "${pin_target}" in
    main|master|HEAD|head|latest|*/main|*/master|*/HEAD|*/head|*/latest)
      die "OPAM ${label} pin uses a moving target: ${pin_target}"
      ;;
  esac
  [[ "${pin_target}" =~ ^[0-9a-f]{40}$ ]] || die "OPAM ${label} pin target is not an immutable commit: ${pin_target}"
  [[ "${pin_target}" == "${expected_commit}" ]] || die "OPAM ${label} pin is ${pin_target}, expected ${expected_commit}"
}

check_platform() {
  require_command uname
  [[ "$(uname -s)" == "Linux" ]] || die "version 1 supports Linux Ubuntu only"
  [[ -f /etc/os-release ]] || die "cannot identify the operating system"
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 ]] || die "version 1 supports Ubuntu 24.04 only"
}

check_plugins() {
  local output
  output="$(opam_exec frama-c -plugins 2>&1)" || die "Frama-C plugin listing failed"
  grep -Eiq '(^|[^[:alnum:]])saida([^[:alnum:]]|$)' <<<"${output}" || die "Saida plugin is not visible to Frama-C"
  grep -Eiq '(^|[^[:alnum:]])isp([^[:alnum:]]|$)' <<<"${output}" || die "ISP plugin is not visible to Frama-C"
}

check_why3_provers() {
  local output
  output="$(WHY3CONFIG="${WHY3_CONFIG}" opam_exec why3 config list-provers 2>&1)" || die "Why3 could not list its configured provers"
  grep -Eiq 'alt-ergo' <<<"${output}" || die "Why3 does not know Alt-Ergo"
  grep -Eiq 'z3' <<<"${output}" || die "Why3 does not know Z3"
  grep -Eiq 'cvc4' <<<"${output}" || die "Why3 does not know CVC4"
}

check_metadata() {
  check_manifest_value OPAM_ARCHIVE_MIRROR "${OPAM_ARCHIVE_MIRROR}"
  check_manifest_value OPAM_INIT_CONFIG "${OPAM_INIT_CONFIG}"
  check_managed_opamrc
  check_archive_mirror
  check_manifest_value SAIDA_REF "${SAIDA_REF}"
  check_manifest_value SAIDA_COMMIT "${SAIDA_COMMIT}"
  check_manifest_value ISP_REF "${ISP_REF}"
  check_manifest_value ISP_COMMIT "${ISP_COMMIT}"
  check_manifest_value TRICERA_REF "${TRICERA_REF}"
  check_manifest_value EXAMPLES_REF "${EXAMPLES_REF}"
  check_manifest_value EXAMPLES_COMMIT "${EXAMPLES_COMMIT}"
  check_exact_source_commit "${prefix}/src/tricera" "${TRICERA_REF}"
  check_exact_source_commit "${prefix}/src/auto-deduct-examples" "${EXAMPLES_COMMIT}"

  local pins
  if ! pins="$(opam_switch_cmd pin list 2>&1)"; then
    printf 'OPAM pin-list output for switch %s:\n%s\n' "${switch_name}" "${pins}" >&2
    die "could not list OPAM pins for switch ${switch_name}"
  fi
  check_pin_target frama-c-saida "${SAIDA_COMMIT}" Saida "${pins}"
  check_pin_target frama-c-isp "${ISP_COMMIT}" ISP "${pins}"
}

run_quick_check() {
  check_platform
  require_command opam
  require_command git
  require_command java
  require_command python3
  require_command z3
  require_command cvc4
  [[ -f "${MANIFEST_FILE}" ]] || die "installation manifest is missing: ${MANIFEST_FILE}"
  [[ -f "${prefix}/opam-package-list.txt" ]] || die "OPAM package list is missing"
  [[ -f "${prefix}/env.sh" ]] || die "activation file is missing"
  [[ -f "${WHY3_CONFIG}" ]] || die "Why3 configuration is missing: ${WHY3_CONFIG}"
  [[ -x "${BIN_ROOT}/tri" ]] || die "tri is not executable"
  [[ -x "${BIN_ROOT}/tri-pp" ]] || die "tri-pp is not executable"
  [[ -x "${BIN_ROOT}/tri-client" ]] || die "tri-client is not executable"

  switch_exists || die "OPAM switch does not exist: ${switch_name}"
  local ocaml_version
  ocaml_version="$(opam_exec ocamlc -version)"
  [[ "${ocaml_version}" == "${OCAML_VERSION}" ]] || die "OCaml is ${ocaml_version}, expected ${OCAML_VERSION}"

  local frama_version
  frama_version="$(opam_exec frama-c -version | head -n1)"
  grep -Eq '(^|[^0-9])31\.0([^0-9]|$)' <<<"${frama_version}" || die "Frama-C is not exactly 31.0: ${frama_version}"
  check_plugins

  local z3_output cvc4_output
  z3_output="$(z3 -version 2>&1)" || die "Z3 could not be executed"
  grep -q 'Z3 version' <<<"${z3_output}" || die "Z3 output was not recognized"
  cvc4_output="$(cvc4 --version 2>&1)" || die "CVC4 could not be executed"
  grep -qi 'cvc4' <<<"${cvc4_output}" || die "CVC4 output was not recognized"
  check_why3_provers
  check_metadata

  local helper
  for helper in \
    autodeduct-contract-assistant \
    autodeduct-contract-assistant-gui; do
    [[ -x "${BIN_ROOT}/${helper}" ]] || die "helper command is not executable: ${BIN_ROOT}/${helper}"
  done
  for helper in \
    autodeduct_contract_assistant_draft.py \
    autodeduct_contract_assistant_framac.py \
    autodeduct_contract_assistant_openai.py \
    autodeduct_contract_assistant_project.py; do
    [[ -f "${BIN_ROOT}/${helper}" ]] || die "helper module is missing: ${BIN_ROOT}/${helper}"
  done
  info "quick check passed for ${prefix}"
}

assert_original_profile() {
  local input_file=$1
  python3 - "${input_file}" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

def has_contract(name):
    pattern = r"/\*@.*?\*/\s*[^;{}]*\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{"
    return re.search(pattern, text, re.S) is not None

if not has_contract("main"):
    raise SystemExit("paper input has no ACSL contract on main")

helpers = ["read", "write", "get_system_state", "eval_prim_sensor_state", "secondary_steering"]
missing = [name for name in helpers if has_contract(name)]
if missing:
    raise SystemExit("paper input already has helper contracts: " + ", ".join(missing))
PY
}

assert_inferred_helpers() {
  local output_file=$1
  python3 - "${output_file}" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
helpers = ["read", "write", "get_system_state", "eval_prim_sensor_state", "secondary_steering"]

def has_contract(name):
    pattern = r"/\*@.*?\*/\s*[^;{}]*\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{"
    return re.search(pattern, text, re.S) is not None

missing = [name for name in helpers if not has_contract(name)]
if missing:
    raise SystemExit("Saida did not infer helper contracts: " + ", ".join(missing))
PY
  if grep -Eiq 'No inferred contract found for (read|write|get_system_state|eval_prim_sensor_state|secondary_steering)' "${output_file}"; then
    die "Saida reported an expected helper contract as missing"
  fi
}

check_wp_result() {
  local wp_log=$1
  local profile=${2:-paper}
  local summary
  summary="$(grep -E '\[wp\].*Proved goals:[[:space:]]*[0-9]+[[:space:]]*/[[:space:]]*[0-9]+' "${wp_log}" | tail -n1 || true)"
  [[ -n "${summary}" ]] || die "WP did not report a proved-goals summary; see ${wp_log}"
  local proved total
  proved="$(sed -E 's/.*Proved goals:[[:space:]]*([0-9]+)[[:space:]]*\/[[:space:]]*([0-9]+).*/\1/' <<<"${summary}")"
  total="$(sed -E 's/.*Proved goals:[[:space:]]*([0-9]+)[[:space:]]*\/[[:space:]]*([0-9]+).*/\2/' <<<"${summary}")"
  (( total > 0 )) || die "WP scheduled zero goals"
  (( proved == total )) || die "WP proved ${proved} of ${total} goals"
  if grep -Eiq '\[wp\].*(failed|unknown|timeout)' "${wp_log}"; then
    die "WP reported a failed, unknown, or timed out goal"
  fi
  if [[ "${profile}" == paper ]]; then
    (( proved == 236 && total == 236 )) || die "paper profile requires WP proved 236/236 goals, got ${proved}/${total}"
  fi
  info "WP proved ${proved}/${total} goals"
}

check_tricera_result() {
  local result_file=$1
  local error_class=""

  if grep -Eiq 'parser error' "${result_file}"; then
    error_class='parser error'
  elif grep -Eiq 'parse error' "${result_file}"; then
    error_class='parse error'
  elif grep -Eiq 'translation error' "${result_file}"; then
    error_class='translation error'
  elif grep -Eiq 'fatal error' "${result_file}"; then
    error_class='fatal error'
  elif grep -Eiq 'exception' "${result_file}"; then
    error_class='exception'
  elif grep -Eiq 'horn[[:space:]]+relation.*(arity|argument[[:space:]-]+count)' "${result_file}"; then
    error_class='Horn relation arity or argument-count mismatch'
  elif grep -Eiq 'solver[[:space:]]+error' "${result_file}"; then
    error_class='solver error'
  fi

  if [[ -n "${error_class}" ]]; then
    printf 'Retained TriCera result:\n' >&2
    cat -- "${result_file}" >&2 || true
    printf 'ERROR: retained TriCera output contains %s\n' "${error_class}" >&2
    return 1
  fi
}

parse_source() {
  local phase=$1
  local source_file=$2
  local log_file=$3
  local tmp_dir=$4
  local status

  if TMPDIR="${tmp_dir}" opam_exec frama-c -quiet "${source_file}" >"${log_file}" 2>&1; then
    info "${phase} parse passed"
    return 0
  else
    status=$?
    printf '%s parse output:\n' "${phase}" >&2
    cat -- "${log_file}" >&2
    printf 'ERROR: %s parse failed; see %s\n' "${phase}" "${log_file}" >&2
    return "${status}"
  fi
}

run_logged_command() {
  local phase=$1
  local log_file=$2
  shift 2

  if "$@" >"${log_file}" 2>&1; then
    return 0
  else
    local status=$?
    printf '%s output:\n' "${phase}" >&2
    cat -- "${log_file}" >&2 || true
    printf 'ERROR: %s failed with status %s; see %s\n' "${phase}" "${status}" "${log_file}" >&2
    return "${status}"
  fi
}

cleanup_expected_work_directory() {
  local work=${1:-}
  local work_parent=${2:-}
  local relative

  if [[ -z "${work}" || -z "${work_parent}" || ! -d "${work}" ]]; then
    return 0
  fi
  if [[ "${work_parent}" != /* || "${work}" != "${work_parent}"/* ]]; then
    printf 'WARNING: refusing to remove unexpected work directory: %s\n' "${work}" >&2
    return 0
  fi

  relative=${work#"${work_parent}"/}
  if [[ "${relative}" == .paper-smoke.* && "${relative}" != */* ]]; then
    if ! rm -rf -- "${work}"; then
      printf 'WARNING: could not remove work directory: %s\n' "${work}" >&2
    fi
  else
    printf 'WARNING: refusing to remove unexpected work directory: %s\n' "${work}" >&2
  fi
}

run_cleanup_self_test_case() (
  set -Eeuo pipefail

  local work=""
  local work_parent=$1
  local mode=$2
  local expected_status=$3

  # shellcheck disable=SC2317,SC2329
  cleanup_self_test_case() {
    local status=$?
    trap - EXIT
    cleanup_expected_work_directory "${work:-}" "${work_parent:-}"
    exit "${status}"
  }
  trap cleanup_self_test_case EXIT

  case "${mode}" in
    success|failure)
      work="$(mktemp -d "${work_parent}/.paper-smoke.XXXXXX")"
      ;;
    empty)
      ;;
    unexpected)
      work="${work_parent}/unexpected"
      ;;
    *)
      printf 'ERROR: unknown cleanup self-test case: %s\n' "${mode}" >&2
      exit 2
      ;;
  esac

  exit "${expected_status}"
)

run_cleanup_self_test() (
  set -Eeuo pipefail

  local test_parent=""
  local failure_status
  local empty_output

  # shellcheck disable=SC2317,SC2329
  cleanup_self_test_parent() {
    local status=$?
    trap - EXIT
    if [[ -n "${test_parent:-}" && -d "${test_parent}" ]]; then
      case "${test_parent}" in
        "${TMPDIR:-/tmp}"/autodeduct-cleanup-self-test.*)
          rm -rf -- "${test_parent}"
          ;;
        *)
          printf 'WARNING: refusing to remove self-test directory: %s\n' "${test_parent}" >&2
          ;;
      esac
    fi
    exit "${status}"
  }
  trap cleanup_self_test_parent EXIT

  test_parent="$(mktemp -d "${TMPDIR:-/tmp}/autodeduct-cleanup-self-test.XXXXXX")"

  run_cleanup_self_test_case "${test_parent}" success 0
  [[ -z "$(find "${test_parent}" -mindepth 1 -maxdepth 1 -type d -name '.paper-smoke.*' -print -quit)" ]] || die "cleanup self-test did not remove a successful work directory"

  failure_status=0
  run_cleanup_self_test_case "${test_parent}" failure 23 2>"${test_parent}/failure.log" || failure_status=$?
  [[ "${failure_status}" -eq 23 ]] || die "cleanup self-test changed failure status to ${failure_status}"
  [[ -z "$(find "${test_parent}" -mindepth 1 -maxdepth 1 -type d -name '.paper-smoke.*' -print -quit)" ]] || die "cleanup self-test did not remove a failed work directory"

  empty_output="$(run_cleanup_self_test_case "${test_parent}" empty 0 2>&1)"
  [[ "${empty_output}" != *'unbound variable'* ]] || die "cleanup self-test reported an unbound variable for empty work"

  mkdir -- "${test_parent}/unexpected"
  run_cleanup_self_test_case "${test_parent}" unexpected 0 >/dev/null 2>"${test_parent}/unexpected.log"
  [[ -d "${test_parent}/unexpected" ]] || die "cleanup self-test removed an unexpected directory"

  info "cleanup self-test passed"
)

run_parser_self_test() (
  set -Eeuo pipefail

  local test_dir=""
  local test_parent="${TMPDIR:-/tmp}"
  local error_kind
  local minimal_status
  local invalid_status
  local expected_invalid_status
  parser_test_exec() {
    if [[ -d "${OPAM_ROOT}" ]]; then
      opam_exec "$@"
    else
      opam_wrapper exec -- "$@"
    fi
  }

  if [[ "${test_parent}" != /* ]]; then
    die "TMPDIR must be absolute for the parser self-test"
  fi

  # shellcheck disable=SC2317,SC2329
  cleanup_parser_self_test() {
    local status=$?
    trap - EXIT
    if [[ -n "${test_dir:-}" && -d "${test_dir}" ]]; then
      case "${test_dir}" in
        "${test_parent}"/autodeduct-parser-self-test.*)
          if ! rm -rf -- "${test_dir}"; then
            printf 'WARNING: could not remove parser self-test directory: %s\n' "${test_dir}" >&2
          fi
          ;;
        *)
          printf 'WARNING: refusing to remove parser self-test directory: %s\n' "${test_dir}" >&2
          ;;
      esac
    fi
    exit "${status}"
  }
  trap cleanup_parser_self_test EXIT

  test_dir="$(mktemp -d "${test_parent}/autodeduct-parser-self-test.XXXXXX")"
  printf 'int main(void) { return 0; }\n' >"${test_dir}/minimal.c"
  printf 'int main(void) { return ;\n' >"${test_dir}/invalid.c"

  if parser_test_exec frama-c -quiet "${test_dir}/minimal.c" >"${test_dir}/minimal.log" 2>&1; then
    minimal_status=0
  else
    minimal_status=$?
  fi
  [[ "${minimal_status}" -eq 0 ]] || die "Frama-C parser self-test rejected minimal C"

  if parser_test_exec frama-c -quiet "${test_dir}/invalid.c" >"${test_dir}/invalid.log" 2>&1; then
    invalid_status=0
  else
    invalid_status=$?
  fi
  [[ "${invalid_status}" -ne 0 ]] || die "Frama-C parser self-test accepted invalid C"

  if parser_test_exec frama-c -quiet "${test_dir}/invalid.c" >/dev/null 2>&1; then
    expected_invalid_status=0
  else
    expected_invalid_status=$?
  fi
  [[ "${invalid_status}" -eq "${expected_invalid_status}" ]] || die "parser self-test changed the Frama-C exit status"
  info "parser-command self-test passed"
)

run_wp_result_self_test() (
  set -Eeuo pipefail

  local test_dir=""
  local test_parent="${TMPDIR:-/tmp}"

  if [[ "${test_parent}" != /* ]]; then
    die "TMPDIR must be absolute for the WP-result self-test"
  fi

  # shellcheck disable=SC2317,SC2329
  cleanup_wp_result_self_test() {
    local status=$?
    trap - EXIT
    if [[ -n "${test_dir:-}" && -d "${test_dir}" ]]; then
      case "${test_dir}" in
        "${test_parent}"/autodeduct-wp-result-self-test.*)
          if ! rm -rf -- "${test_dir}"; then
            printf 'WARNING: could not remove WP-result self-test directory: %s\n' "${test_dir}" >&2
          fi
          ;;
        *)
          printf 'WARNING: refusing to remove WP-result self-test directory: %s\n' "${test_dir}" >&2
          ;;
      esac
    fi
    exit "${status}"
  }
  trap cleanup_wp_result_self_test EXIT

  test_dir="$(mktemp -d "${test_parent}/autodeduct-wp-result-self-test.XXXXXX")"

  printf '[wp] Proved goals: 236 / 236\n' >"${test_dir}/good.log"
  check_wp_result "${test_dir}/good.log" paper

  printf '[wp] Proved goals: 235 / 235\n' >"${test_dir}/wrong-equal.log"
  if (check_wp_result "${test_dir}/wrong-equal.log" paper >/dev/null 2>&1); then
    die "WP-result self-test accepted 235/235"
  fi

  printf '[wp] Proved goals: 236 / 237\n' >"${test_dir}/wrong-total.log"
  if (check_wp_result "${test_dir}/wrong-total.log" paper >/dev/null 2>&1); then
    die "WP-result self-test accepted 236/237"
  fi

  printf '[wp] Proved goals: 0 / 0\n' >"${test_dir}/zero.log"
  if (check_wp_result "${test_dir}/zero.log" paper >/dev/null 2>&1); then
    die "WP-result self-test accepted 0/0"
  fi

  : >"${test_dir}/missing.log"
  if (check_wp_result "${test_dir}/missing.log" paper >/dev/null 2>&1); then
    die "WP-result self-test accepted a missing summary"
  fi

  for error_kind in failed unknown timeout; do
    printf '[wp] Proved goals: 236 / 236\n[wp] %s\n' "${error_kind}" >"${test_dir}/${error_kind}.log"
    if (check_wp_result "${test_dir}/${error_kind}.log" paper >/dev/null 2>&1); then
      die "WP-result self-test accepted ${error_kind} text"
    fi
  done

  info "WP-result self-test passed"
)

run_backend_error_self_test() (
  set -Eeuo pipefail

  local test_dir=""
  local test_parent="${TMPDIR:-/tmp}"
  local error_kind

  if [[ "${test_parent}" != /* ]]; then
    die "TMPDIR must be absolute for the backend-error self-test"
  fi

  # shellcheck disable=SC2317,SC2329
  cleanup_backend_error_self_test() {
    local status=$?
    trap - EXIT
    if [[ -n "${test_dir:-}" && -d "${test_dir}" ]]; then
      case "${test_dir}" in
        "${test_parent}"/autodeduct-backend-error-self-test.*)
          if ! rm -rf -- "${test_dir}"; then
            printf 'WARNING: could not remove backend-error self-test directory: %s\n' "${test_dir}" >&2
          fi
          ;;
        *)
          printf 'WARNING: refusing to remove backend-error self-test directory: %s\n' "${test_dir}" >&2
          ;;
      esac
    fi
    exit "${status}"
  }
  trap cleanup_backend_error_self_test EXIT

  test_dir="$(mktemp -d "${test_parent}/autodeduct-backend-error-self-test.XXXXXX")"
  printf 'int main(void) { return 0; }\n' >"${test_dir}/clean.c"
  check_tricera_result "${test_dir}/clean.c"

  for error_kind in \
    'parser error' \
    'translation error' \
    'Horn relation arity mismatch' \
    'solver error'; do
    printf '%s\n' "${error_kind}" >"${test_dir}/error.log"
    if check_tricera_result "${test_dir}/error.log" >/dev/null 2>&1; then
      die "backend-error self-test accepted ${error_kind}"
    fi
  done

  printf 'error handling is documented here\n' >"${test_dir}/unrelated.log"
  check_tricera_result "${test_dir}/unrelated.log"
  info "backend-error self-test passed"
)

run_phase_status_case() (
  set -Eeuo pipefail

  local expected_status=$1
  local test_dir=""
  local test_parent="${TMPDIR:-/tmp}"
  local actual_status

  # shellcheck disable=SC2317,SC2329
  cleanup_phase_status_self_test() {
    local status=$?
    trap - EXIT
    if [[ -n "${test_dir:-}" && -d "${test_dir}" ]]; then
      case "${test_dir}" in
        "${test_parent}"/autodeduct-phase-status-self-test.*)
          if ! rm -rf -- "${test_dir}"; then
            printf 'WARNING: could not remove phase-status self-test directory: %s\n' "${test_dir}" >&2
          fi
          ;;
        *)
          printf 'WARNING: refusing to remove phase-status self-test directory: %s\n' "${test_dir}" >&2
          ;;
      esac
    fi
    exit "${status}"
  }
  trap cleanup_phase_status_self_test EXIT

  test_dir="$(mktemp -d "${test_parent}/autodeduct-phase-status-self-test.XXXXXX")"
  # shellcheck disable=SC2317,SC2329
  phase_status_command() {
    return "$1"
  }

  if run_logged_command "simulated phase ${expected_status}" "${test_dir}/phase.log" phase_status_command "${expected_status}" >"${test_dir}/report.log" 2>&1; then
    actual_status=0
  else
    actual_status=$?
  fi
  [[ "${actual_status}" -eq "${expected_status}" ]] || exit 1
  exit "${actual_status}"
)

run_phase_status_self_test() (
  set -Eeuo pipefail

  local expected_status
  local actual_status

  for expected_status in 2 4 125; do
    actual_status=0
    run_phase_status_case "${expected_status}" || actual_status=$?
    [[ "${actual_status}" -eq "${expected_status}" ]] || die "phase-status self-test changed ${expected_status} to ${actual_status}"
  done
  info "phase-status self-test passed"
)

run_full_check() (
  set -Eeuo pipefail

  local profile=${AUTODEDUCT_SMOKE_PROFILE:-paper}
  local profile_args=()
  case "${profile}" in
    paper)
      ;;
    library-entry)
      profile_args+=(-lib-entry)
      ;;
    *)
      die "AUTODEDUCT_SMOKE_PROFILE must be paper or library-entry"
      ;;
  esac

  local examples_dir="${prefix}/src/auto-deduct-examples"
  local paper_source="${examples_dir}/ase-2024/stee.c"
  [[ -f "${paper_source}" ]] || die "pinned paper example is missing: ${paper_source}"

  local work=""
  local work_parent="${prefix}"
  work="$(mktemp -d "${work_parent}/.paper-smoke.XXXXXX")"
  # shellcheck disable=SC2317,SC2329
  cleanup_full_check() {
    local status=$?
    trap - EXIT
    cleanup_expected_work_directory "${work:-}" "${work_parent:-}"
    exit "${status}"
  }
  trap cleanup_full_check EXIT
  mkdir -p "${work}/input" "${work}/tmp"
  cp -- "${paper_source}" "${work}/input/stee.c"
  local input_file="${work}/input/stee.c"
  local saida_file="${work}/saida.c"
  local saida_log="${work}/saida.log"
  local isp_file="${work}/out.c"
  local isp_log="${work}/isp.log"
  local wp_log="${work}/wp.log"

  info "full check profile: ${profile}"
  info "checking the paper input with Frama-C"
  parse_source "Original paper input" "${input_file}" "${work}/parse.log" "${work}/tmp"
  assert_original_profile "${input_file}"

  # shellcheck disable=SC2317,SC2329
  run_saida_phase() {
    TMPDIR="${work}/tmp" opam_exec frama-c "${profile_args[@]}" \
      -autoload-plugins -saida -saida-keep-tmp \
      -saida-tricera-path "${BIN_ROOT}/tri" \
      -saida-out "${saida_file}" "${input_file}"
  }
  info "running Saida functional inference"
  run_logged_command "Saida inference" "${saida_log}" run_saida_phase
  [[ -s "${saida_file}" ]] || die "Saida did not produce ${saida_file}"
  local tricera_result
  tricera_result="$(find "${work}/input" -maxdepth 1 -type f -name 'saida_result_*.c' -print -quit)"
  [[ -n "${tricera_result}" ]] || die "Saida did not retain TriCera output"
  check_tricera_result "${tricera_result}"
  assert_inferred_helpers "${saida_file}"
  parse_source "Generated Saida source" "${saida_file}" "${work}/saida-parse.log" "${work}/tmp"

  # shellcheck disable=SC2317,SC2329
  run_isp_phase() {
    TMPDIR="${work}/tmp" opam_exec frama-c "${profile_args[@]}" \
      -autoload-plugins -isp -isp-entry-point main \
      -isp-print-file "${isp_file}" "${saida_file}"
  }
  info "running ISP auxiliary annotation inference"
  run_logged_command "ISP inference" "${isp_log}" run_isp_phase
  [[ -s "${isp_file}" ]] || die "ISP did not produce ${isp_file}"
  local saida_assigns isp_assigns
  saida_assigns="$(grep -Eic '^[[:space:]]*(assigns|requires)' "${saida_file}" || true)"
  isp_assigns="$(grep -Eic '^[[:space:]]*(assigns|requires)' "${isp_file}" || true)"
  (( isp_assigns > saida_assigns )) || die "ISP did not add auxiliary annotations"
  parse_source "Generated ISP source" "${isp_file}" "${work}/isp-parse.log" "${work}/tmp"

  # shellcheck disable=SC2317,SC2329
  run_wp_phase() {
    TMPDIR="${work}/tmp" WHY3CONFIG="${WHY3_CONFIG}" opam_exec frama-c "${profile_args[@]}" \
      -wp -wp-prover "${wp_provers}" "${isp_file}"
  }
  info "running WP"
  local wp_provers=${AUTODEDUCT_WP_PROVERS:-alt-ergo,z3,cvc4}
  run_logged_command "WP" "${wp_log}" run_wp_phase
  check_wp_result "${wp_log}" "${profile}"
  info "full paper-model check passed"
)

if [[ "${run_cleanup_self_test_mode}" == true ]]; then
  run_cleanup_self_test
fi
if [[ "${run_parser_self_test_mode}" == true ]]; then
  run_parser_self_test
fi
if [[ "${run_wp_result_self_test_mode}" == true ]]; then
  run_wp_result_self_test
fi
if [[ "${run_backend_error_self_test_mode}" == true ]]; then
  run_backend_error_self_test
fi
if [[ "${run_phase_status_self_test_mode}" == true ]]; then
  run_phase_status_self_test
fi
if [[ "${run_quick}" == true ]]; then
  run_quick_check
fi
if [[ "${run_full}" == true ]]; then
  run_full_check
fi
