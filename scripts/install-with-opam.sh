#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VERSIONS_FILE="${REPO_ROOT}/opam/versions.env"
DOCKERFILE="${REPO_ROOT}/Dockerfiles/AutoDeductDockerfile"

if [[ ! -f "${VERSIONS_FILE}" ]]; then
  printf 'ERROR: version file is missing: %s\n' "${VERSIONS_FILE}" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${VERSIONS_FILE}"
: "${OPAM_ARCHIVE_MIRROR:?OPAM_ARCHIVE_MIRROR is missing from ${VERSIONS_FILE}}"

readonly DEFAULT_SWITCH_NAME=autodeduct-31
readonly DEFAULT_PREFIX="${HOME}/.local/share/autodeduct"

switch_name="${DEFAULT_SWITCH_NAME}"
prefix="${DEFAULT_PREFIX}"
install_system_deps=false
yes_mode=false
dry_run=false
disable_opam_sandboxing=false
proxy_host=''
proxy_port=''

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf 'INFO: %s\n' "$*" >&2
}

warn() {
  printf 'WARNING: %s\n' "$*" >&2
}

usage() {
  cat <<'EOF'
Usage: scripts/install-with-opam.sh [OPTIONS]

Install the AutoDeduct OPAM toolchain in a private prefix.

Options:
  --switch NAME              OPAM switch name (default: autodeduct-31)
  --prefix DIRECTORY         Managed prefix (default: $HOME/.local/share/autodeduct)
  --install-system-deps      Install Ubuntu system dependencies with sudo
  --skip-system-deps         Do not install system dependencies
  --yes                      Answer yes to package manager questions
  --dry-run                  Show the plan without changing files
  --disable-opam-sandboxing  Disable OPAM build sandboxing during OPAM init
  --proxy-host HOST          Proxy host for downloads and the SBT JVM
  --proxy-port PORT          Proxy port for downloads and the SBT JVM
  -h, --help                 Show this help

Supported in version 1: Ubuntu 24.04 and Ubuntu under WSL2.
EOF
}

on_error() {
  local status=$?
  printf 'ERROR: installation stopped at line %s with status %s.\n' "${BASH_LINENO[0]:-unknown}" "${status}" >&2
  exit "${status}"
}

trap on_error ERR

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
    --install-system-deps)
      install_system_deps=true
      shift
      ;;
    --skip-system-deps)
      install_system_deps=false
      shift
      ;;
    --yes)
      yes_mode=true
      shift
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    --disable-opam-sandboxing)
      disable_opam_sandboxing=true
      shift
      ;;
    --proxy-host)
      [[ $# -ge 2 ]] || die "--proxy-host needs a value"
      proxy_host=$2
      shift 2
      ;;
    --proxy-port)
      [[ $# -ge 2 ]] || die "--proxy-port needs a value"
      proxy_port=$2
      shift 2
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

[[ -n "${switch_name}" ]] || die "the switch name must not be empty"
[[ -n "${prefix}" ]] || die "the prefix must not be empty"

if [[ -n "${proxy_host}" || -n "${proxy_port}" ]]; then
  [[ -n "${proxy_host}" && -n "${proxy_port}" ]] || die "--proxy-host and --proxy-port must be used together"
  [[ "${proxy_host}" != *'@'* && "${proxy_host}" != *'/'* && "${proxy_host}" != *':'* ]] || die "proxy host must not contain credentials or a URL"
  [[ "${proxy_port}" =~ ^[0-9]+$ ]] || die "proxy port must be numeric"
  (( proxy_port >= 1 && proxy_port <= 65535 )) || die "proxy port must be between 1 and 65535"
fi

docker_arg_value() {
  local key=$1
  awk -v key="${key}" '$1 == "ARG" && $2 ~ ("^" key "=") { value=$2; sub("^" key "=", "", value); gsub(/"/, "", value); print value; exit }' "${DOCKERFILE}"
}

check_ref_shape() {
  local name=$1
  local value=$2
  [[ "${value}" =~ ^[0-9a-f]{40}$ ]] || die "${name} must be a full 40-character Git commit: ${value}"
}

check_metadata_local() {
  [[ "${FRAMA_C_VERSION}" == "$(docker_arg_value FRAMA_C_VER)" ]] || die "FRAMA_C_VERSION disagrees with the Dockerfile"
  [[ "${SAIDA_REF}" == "$(docker_arg_value SAIDA_VER)" ]] || die "SAIDA_REF disagrees with the Dockerfile"
  [[ "${ISP_REF}" == "$(docker_arg_value ISP_VER)" ]] || die "ISP_REF disagrees with the Dockerfile"
  [[ "${TRICERA_REF}" == "$(docker_arg_value TRICERA_VER)" ]] || die "TRICERA_REF disagrees with the Dockerfile"
  grep -Fq 's/1.4.0/1.9.8/' "${DOCKERFILE}" || die "SBT_VERSION no longer matches the Dockerfile workaround"

  check_ref_shape SAIDA_COMMIT "${SAIDA_COMMIT}"
  check_ref_shape ISP_COMMIT "${ISP_COMMIT}"
  check_ref_shape TRICERA_REF "${TRICERA_REF}"
  check_ref_shape EXAMPLES_REF "${EXAMPLES_REF}"
  check_ref_shape EXAMPLES_COMMIT "${EXAMPLES_COMMIT}"
  check_ref_shape OPAM_REPOSITORY_REF "${OPAM_REPOSITORY_REF}"
  [[ "${EXAMPLES_REF}" == "${EXAMPLES_COMMIT}" ]] || die "EXAMPLES_REF and EXAMPLES_COMMIT must match"
  [[ "${SBT_VERSION}" == "1.9.8" ]] || die "SBT_VERSION must preserve the Dockerfile value 1.9.8"
}

check_metadata_remote() {
  local resolved
  resolved="$(git ls-remote --refs "${SAIDA_REPO_URL}" "refs/tags/${SAIDA_REF}" | awk 'NR == 1 { print $1 }')"
  [[ "${resolved}" == "${SAIDA_COMMIT}" ]] || die "Saida tag ${SAIDA_REF} resolves to ${resolved}, not ${SAIDA_COMMIT}"
  resolved="$(git ls-remote --refs "${ISP_REPO_URL}" "refs/tags/${ISP_REF}" | awk 'NR == 1 { print $1 }')"
  [[ "${resolved}" == "${ISP_COMMIT}" ]] || die "ISP tag ${ISP_REF} resolves to ${resolved}, not ${ISP_COMMIT}"
}

check_no_moving_source_refs() {
  local value
  for value in \
    "${SAIDA_REF}" \
    "${ISP_REF}" \
    "${TRICERA_REF}" \
    "${EXAMPLES_REF}" \
    "${EXAMPLES_COMMIT}" \
    "${OPAM_REPOSITORY_REF}"; do
    [[ ! "${value}" =~ ^(main|master|HEAD|head|latest)$ ]] || die "moving source reference is not allowed: ${value}"
  done
}

print_dry_run_opam_init_command() {
  local dry_prefix="${prefix}"
  if [[ "${dry_prefix}" != /* ]]; then
    dry_prefix="$(pwd -P)/${dry_prefix}"
  fi
  local command=(
    opam
    --cli=2.1
    init
    --root
    "${dry_prefix}/opam-root"
    --no-opamrc
    "--config=${dry_prefix}/opamrc"
    --bare
    --no-setup
    --kind=git
  )
  if [[ "${disable_opam_sandboxing}" == true ]]; then
    command+=(--disable-sandboxing)
  fi
  if [[ "${yes_mode}" == true ]]; then
    command+=(--yes)
  fi
  command+=(default "${OPAM_REPOSITORY_URL}#${OPAM_REPOSITORY_REF}")
  printf 'INFO: dry-run: OPAM init command:'
  printf ' %q' "${command[@]}"
  printf '\n'
}

check_switch_command_order() {
  local list_command=(switch --short list)
  [[ "${list_command[0]}" == switch ]] || die "switch-list command must start with switch"
  [[ "${list_command[1]}" == --short ]] || die "switch-list --short must precede list"
  [[ "${list_command[2]}" == list ]] || die "switch-list command must end with list"

  local create_command=(switch)
  if [[ "${yes_mode}" == true ]]; then
    create_command+=(--yes)
  fi
  create_command+=(--no-switch create "${switch_name}" "ocaml-base-compiler.${OCAML_VERSION}")

  local switch_index=-1
  local yes_index=-1
  local no_switch_index=-1
  local create_index=-1
  local name_index=-1
  local compiler_index=-1
  local index
  for index in "${!create_command[@]}"; do
    case "${create_command[index]}" in
      switch) switch_index=${index} ;;
      --yes) yes_index=${index} ;;
      --no-switch) no_switch_index=${index} ;;
      create) create_index=${index} ;;
      "${switch_name}") name_index=${index} ;;
      "ocaml-base-compiler.${OCAML_VERSION}") compiler_index=${index} ;;
    esac
  done
  (( switch_index < yes_index || yes_index == -1 )) || die "switch must precede --yes"
  (( switch_index < no_switch_index )) || die "switch must precede --no-switch"
  (( yes_index < create_index || yes_index == -1 )) || die "--yes must precede create"
  (( no_switch_index < create_index )) || die "--no-switch must precede create"
  (( create_index < name_index && create_index < compiler_index )) || die "create must precede switch name and compiler"
}

print_dry_run_switch_commands() {
  local dry_prefix="${prefix}"
  if [[ "${dry_prefix}" != /* ]]; then
    dry_prefix="$(pwd -P)/${dry_prefix}"
  fi
  local root_assignment
  root_assignment="OPAMROOT=$(printf '%q' "${dry_prefix}/opam-root")"
  info "dry-run: switch-list command: ${root_assignment} opam --cli=2.1 switch --short list"

  local create_command=(switch)
  if [[ "${yes_mode}" == true ]]; then
    create_command+=(--yes)
  fi
  create_command+=(--no-switch create "${switch_name}" "ocaml-base-compiler.${OCAML_VERSION}")
  printf 'INFO: dry-run: switch-create command: %s opam --cli=2.1' "${root_assignment}"
  printf ' %q' "${create_command[@]}"
  printf '\n'
}

check_platform() {
  command -v uname >/dev/null 2>&1 || die "uname is required to identify the platform"
  [[ "$(uname -s)" == "Linux" ]] || die "version 1 supports Ubuntu 24.04 only"
  [[ -f /etc/os-release ]] || die "cannot identify the operating system"
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]] || die "version 1 supports Ubuntu 24.04 only"
}

if [[ "${dry_run}" != true ]]; then
check_platform
fi
check_metadata_local
check_no_moving_source_refs
check_switch_command_order

if [[ "${dry_run}" == true ]]; then
  require_command_for_dry_run() {
    command -v "$1" >/dev/null 2>&1 || die "dry-run metadata check needs command '$1'"
  }
  require_command_for_dry_run git
  check_metadata_remote
  info "dry-run: version metadata is consistent with the current Dockerfile"
  info "dry-run: exact Saida and ISP tag checks passed"
  print_dry_run_opam_init_command
  print_dry_run_switch_commands
  info "dry-run: OPAM switch: ${switch_name}"
  info "dry-run: prefix: ${prefix}"
  info "dry-run: system dependencies: $([[ "${install_system_deps}" == true ]] && printf install || printf check)"
  info "dry-run: OPAM compiler: OCaml ${OCAML_VERSION}"
  info "dry-run: Frama-C: ${FRAMA_C_VERSION}"
  info "dry-run: Saida: ${SAIDA_REF} (${SAIDA_COMMIT})"
  info "dry-run: ISP: ${ISP_REF} (${ISP_COMMIT})"
  info "dry-run: TriCera: ${TRICERA_REF} with SBT ${SBT_VERSION}"
  info "dry-run: examples: ${EXAMPLES_COMMIT}"
  if [[ -n "${proxy_host}" ]]; then
    info "dry-run: proxy options supplied; values are not printed"
  else
    info "dry-run: existing proxy environment is preserved"
  fi
  exit 0
fi

if [[ "${prefix}" != /* ]]; then
  prefix="$(pwd -P)/${prefix}"
fi
prefix="$(mkdir -p "${prefix}" && cd -- "${prefix}" && pwd -P)"

[[ "${prefix}" != "/" ]] || die "refusing to use / as the managed prefix"
[[ "${prefix}" != "${HOME}" ]] || die "refusing to use HOME as the managed prefix"
case "${prefix}/" in
  "${REPO_ROOT}/"*) die "the managed prefix must not be inside the repository" ;;
esac

OPAM_ROOT="${prefix}/opam-root"
OPAM_INIT_CONFIG="${prefix}/opamrc"
SOURCE_ROOT="${prefix}/src"
BUILD_ROOT="${prefix}/build"
CACHE_ROOT="${prefix}/cache"
TOOLS_ROOT="${prefix}/tools"
BIN_ROOT="${prefix}/bin"
MANIFEST_FILE="${prefix}/installation-manifest.txt"
PACKAGE_LIST_FILE="${prefix}/opam-package-list.txt"
WHY3_CONFIG="${prefix}/why3.conf"
TRICERA_SOURCE_DIR="${SOURCE_ROOT}/tricera"
TRICERA_BUILD_DIR="${BUILD_ROOT}/tricera-${TRICERA_REF}"
TRICERA_TRI_PATH="${TRICERA_BUILD_DIR}/tri"
TRICERA_TRI_PP_PATH="${TRICERA_BUILD_DIR}/tri-pp"
TRICERA_TRI_CLIENT_PATH="${TRICERA_BUILD_DIR}/tri-client"

mkdir -p "${SOURCE_ROOT}" "${BUILD_ROOT}" "${CACHE_ROOT}" "${TOOLS_ROOT}" "${BIN_ROOT}"

configure_proxy() {
  if [[ -n "${proxy_host}" ]]; then
    local proxy_url="http://${proxy_host}:${proxy_port}"
    export HTTP_PROXY="${HTTP_PROXY:-${proxy_url}}"
    export HTTPS_PROXY="${HTTPS_PROXY:-${proxy_url}}"
    export http_proxy="${http_proxy:-${proxy_url}}"
    export https_proxy="${https_proxy:-${proxy_url}}"
  fi
}

configure_proxy

system_packages=(
  adwaita-icon-theme-full
  autoconf
  ca-certificates
  curl
  cvc4
  git
  graphviz
  libcairo2-dev
  libexpat1-dev
  libgmp-dev
  libgtk-3-dev
  libgtksourceview-3.0-dev
  opam
  openjdk-21-jdk
  pkg-config
  python3
  sudo
  vim
  yaru-theme-icon
  z3
  zlib1g-dev
  build-essential
)

install_system_dependencies() {
  local apt_yes=()
  if [[ "${yes_mode}" == true ]]; then
    apt_yes+=(--yes)
  fi
  if [[ "${EUID}" -eq 0 ]]; then
    apt-get update
    apt-get install "${apt_yes[@]}" "${system_packages[@]}"
  else
    command -v sudo >/dev/null 2>&1 || die "sudo is required for --install-system-deps"
    sudo apt-get update
    sudo apt-get install "${apt_yes[@]}" "${system_packages[@]}"
  fi
}

if [[ "${install_system_deps}" == true ]]; then
  info "installing system dependencies"
  install_system_dependencies
else
  info "checking existing system dependencies"
fi

require_command() {
  local command_name=$1
  command -v "${command_name}" >/dev/null 2>&1 || die "missing command '${command_name}'. Re-run with --install-system-deps or install it manually"
}

require_command git
require_command curl
require_command tar
require_command sha256sum
require_command opam
require_command java
require_command python3
require_command make
require_command cc
require_command z3
require_command cvc4

opam_wrapper() {
  opam --cli=2.1 "$@"
}

opam_version="$(opam_wrapper --version)"
if [[ "$(printf '%s\n' "${opam_version}" 2.1 | sort -V | head -n1)" != "2.1" ]]; then
  die "OPAM CLI 2.1 or later is required; found ${opam_version}"
fi

check_metadata_remote

opam_root_cmd() {
  OPAMROOT="${OPAM_ROOT}" opam_wrapper "$@"
}

opam_switch_cmd() {
  OPAMROOT="${OPAM_ROOT}" OPAMSWITCH="${switch_name}" opam_wrapper "$@"
}

opam_exec() {
  OPAMROOT="${OPAM_ROOT}" OPAMSWITCH="${switch_name}" opam_wrapper exec -- "$@"
}

check_archive_mirror() {
  local mirrors
  if ! mirrors="$(opam_root_cmd option --global archive-mirrors 2>&1)"; then
    printf 'OPAM archive-mirrors output:\n%s\n' "${mirrors}" >&2
    die "could not read OPAM archive-mirrors for root ${OPAM_ROOT}"
  fi
  grep -Fqx "\"${OPAM_ARCHIVE_MIRROR}\"" <<<"${mirrors}" || die "OPAM archive-mirrors does not contain ${OPAM_ARCHIVE_MIRROR}; refusing to edit the OPAM root"
}

write_managed_opamrc() {
  [[ ! -L "${OPAM_INIT_CONFIG}" ]] || die "managed OPAM init config must not be a symbolic link: ${OPAM_INIT_CONFIG}"
  local temporary
  temporary="$(mktemp "${prefix}/.opamrc.XXXXXX")"
  cat >"${temporary}" <<EOF
opam-version: "2.0"
archive-mirrors: [
  "${OPAM_ARCHIVE_MIRROR}"
]
EOF
  if [[ -e "${OPAM_INIT_CONFIG}" ]]; then
    if ! cmp -s "${temporary}" "${OPAM_INIT_CONFIG}"; then
      rm -f -- "${temporary}"
      die "managed OPAM init config does not match ${OPAM_ARCHIVE_MIRROR}: ${OPAM_INIT_CONFIG}"
    fi
  else
    install -m 0644 "${temporary}" "${OPAM_INIT_CONFIG}"
  fi
  rm -f -- "${temporary}"
}

init_opam() {
  write_managed_opamrc
  if [[ -f "${OPAM_ROOT}/config" ]]; then
    check_archive_mirror
    return
  fi
  if [[ -n "$(find "${OPAM_ROOT}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    die "OPAM root exists but is not initialized: ${OPAM_ROOT}"
  fi
  mkdir -p "${OPAM_ROOT}"
  local init_options=(--no-opamrc "--config=${OPAM_INIT_CONFIG}" --bare --no-setup --kind=git)
  if [[ "${disable_opam_sandboxing}" == true ]]; then
    init_options+=(--disable-sandboxing)
  fi
  if [[ "${yes_mode}" == true ]]; then
    init_options+=(--yes)
  fi
  info "initializing the private OPAM root"
  opam_wrapper init --root "${OPAM_ROOT}" "${init_options[@]}" default "${OPAM_REPOSITORY_URL}#${OPAM_REPOSITORY_REF}"
  check_archive_mirror
}

switch_exists() {
  opam_root_cmd switch --short list | awk -v name="${switch_name}" '$1 == name { found=1 } END { exit found ? 0 : 1 }'
}

create_or_check_switch() {
  if switch_exists; then
    info "reusing OPAM switch ${switch_name}"
  else
    info "creating OPAM switch ${switch_name} with OCaml ${OCAML_VERSION}"
    local args=(switch)
    if [[ "${yes_mode}" == true ]]; then
      args+=(--yes)
    fi
    args+=(--no-switch create "${switch_name}" "ocaml-base-compiler.${OCAML_VERSION}")
    opam_root_cmd "${args[@]}"
  fi

  local actual
  actual="$(opam_exec ocamlc -version)"
  [[ "${actual}" == "${OCAML_VERSION}" ]] || die "switch ${switch_name} has OCaml ${actual}, expected ${OCAML_VERSION}"
}

install_opam_packages() {
  local yes_args=()
  if [[ "${yes_mode}" == true ]]; then
    yes_args+=(--yes)
  fi
  info "installing Frama-C, Why3, and Alt-Ergo through OPAM"
  opam_switch_cmd install "${yes_args[@]}" \
    "frama-c.${FRAMA_C_VERSION}" \
    "why3.${WHY3_VERSION}" \
    "${ALT_ERGO_PACKAGE}.${ALT_ERGO_VERSION}"

  info "pinning Saida and ISP through upstream OPAM metadata"
  opam_switch_cmd pin add "${yes_args[@]}" --no-action \
    frama-c-saida "git+${SAIDA_REPO_URL}#${SAIDA_COMMIT}"
  opam_switch_cmd pin add "${yes_args[@]}" --no-action \
    frama-c-isp "git+${ISP_REPO_URL}#${ISP_COMMIT}"
  opam_switch_cmd install "${yes_args[@]}" frama-c-saida frama-c-isp
}

install_why3_config() {
  mkdir -p "${prefix}"
  info "detecting Why3 provers"
  WHY3CONFIG="${WHY3_CONFIG}" opam_exec why3 config detect
}

init_git_checkout() {
  local directory=$1
  local repository=$2
  local commit=$3

  if [[ -e "${directory}" ]]; then
    [[ -d "${directory}/.git" ]] || die "managed source directory is not a Git checkout: ${directory}"
    local actual
    actual="$(git -C "${directory}" rev-parse HEAD)"
    [[ "${actual}" == "${commit}" ]] || die "managed checkout ${directory} is at ${actual}, expected ${commit}"
    return
  fi

  mkdir -p "$(dirname -- "${directory}")"
  git init -q "${directory}"
  git -C "${directory}" remote add origin "${repository}"
  git -C "${directory}" fetch --depth 1 origin "${commit}"
  git -C "${directory}" checkout -q --detach "${commit}"
}

install_sbt() {
  local install_dir="${TOOLS_ROOT}/sbt-${SBT_VERSION}"
  local sbt_bin="${install_dir}/bin/sbt"
  if [[ -x "${sbt_bin}" ]]; then
    printf '%s\n' "${sbt_bin}"
    return
  fi
  [[ ! -e "${install_dir}" ]] || die "incomplete managed SBT installation: ${install_dir}"

  local archive="${CACHE_ROOT}/sbt-${SBT_VERSION}.tgz"
  if [[ -e "${archive}" ]]; then
    printf '%s  %s\n' "${SBT_SHA256}" "${archive}" | sha256sum -c - >/dev/null || die "SBT archive checksum failed: ${archive}"
  else
    local temporary
    temporary="$(mktemp "${CACHE_ROOT}/sbt-${SBT_VERSION}.XXXXXX")"
    curl --fail --location --retry 3 --output "${temporary}" "${SBT_TARBALL_URL}"
    printf '%s  %s\n' "${SBT_SHA256}" "${temporary}" | sha256sum -c - >/dev/null || die "downloaded SBT archive checksum failed"
    mv -- "${temporary}" "${archive}"
  fi

  mkdir -p "${install_dir}"
  tar -xzf "${archive}" -C "${install_dir}" --strip-components=1
  [[ -x "${sbt_bin}" ]] || die "SBT archive did not contain bin/sbt"
  printf '%s\n' "${sbt_bin}"
}

build_tricera() {
  init_git_checkout "${TRICERA_SOURCE_DIR}" "${TRICERA_REPO_URL}" "${TRICERA_REF}"

  if [[ ! -d "${TRICERA_BUILD_DIR}" ]]; then
    local temporary
    temporary="$(mktemp -d "${BUILD_ROOT}/tricera-build.XXXXXX")"
    cp -a "${TRICERA_SOURCE_DIR}/." "${temporary}/"
    sed -i -E "s/^sbt\.version=.*/sbt.version=${SBT_VERSION}/" "${temporary}/project/build.properties"
    {
      printf 'TRICERA_COMMIT=%s\n' "${TRICERA_REF}"
      printf 'SBT_VERSION=%s\n' "${SBT_VERSION}"
    } >"${temporary}/.autodeduct-build"
    mv -- "${temporary}" "${TRICERA_BUILD_DIR}"
  fi

  [[ -f "${TRICERA_BUILD_DIR}/.autodeduct-build" ]] || die "TriCera build metadata is missing: ${TRICERA_BUILD_DIR}"
  grep -Fxq "TRICERA_COMMIT=${TRICERA_REF}" "${TRICERA_BUILD_DIR}/.autodeduct-build" || die "TriCera build commit does not match the version file"
  grep -Fxq "SBT_VERSION=${SBT_VERSION}" "${TRICERA_BUILD_DIR}/.autodeduct-build" || die "TriCera SBT version does not match the version file"

  local sbt_bin
  sbt_bin="$(install_sbt)"
  if [[ ! -x "${TRICERA_TRI_PATH}" || ! -x "${TRICERA_TRI_PP_PATH}" || ! -x "${TRICERA_TRI_CLIENT_PATH}" ]]; then
    info "building TriCera at ${TRICERA_REF}"
    local old_sbt_opts=${SBT_OPTS:-}
    local proxy_opts=''
    if [[ -n "${proxy_host}" ]]; then
      proxy_opts=" -Dhttp.proxyHost=${proxy_host} -Dhttp.proxyPort=${proxy_port} -Dhttps.proxyHost=${proxy_host} -Dhttps.proxyPort=${proxy_port}"
    fi
    local cache_opts=" -Dsbt.global.base=${CACHE_ROOT}/sbt-global -Dsbt.boot.directory=${CACHE_ROOT}/sbt-boot -Dsbt.ivy.home=${CACHE_ROOT}/ivy2"
    local combined_sbt_opts="${old_sbt_opts}${proxy_opts}${cache_opts}"
    (
      cd "${TRICERA_BUILD_DIR}"
      COURSIER_CACHE="${CACHE_ROOT}/coursier" \
        COURSIER_HOME="${CACHE_ROOT}/coursier-home" \
        SBT_OPTS="${combined_sbt_opts}" "${sbt_bin}" -batch assembly
    )
  fi

  [[ -x "${TRICERA_TRI_PATH}" ]] || die "TriCera did not produce tri: ${TRICERA_TRI_PATH}"
  [[ -x "${TRICERA_TRI_PP_PATH}" ]] || die "TriCera did not produce tri-pp: ${TRICERA_TRI_PP_PATH}"
  [[ -x "${TRICERA_TRI_CLIENT_PATH}" ]] || die "TriCera did not produce tri-client: ${TRICERA_TRI_CLIENT_PATH}"
}

validate_tricera_executable_path() {
  local path=$1
  local name=$2
  local resolved
  local managed_root="${TRICERA_BUILD_DIR%/}/"

  [[ -n "${path}" ]] || die "TriCera ${name} path is empty"
  [[ "${path}" != *$'\n'* && "${path}" != *$'\r'* ]] || die "TriCera ${name} path contains a newline"
  [[ "${path}" == /* ]] || die "TriCera ${name} path is not absolute: ${path}"
  case "${path}" in
    "${managed_root}"*) ;;
    *) die "TriCera ${name} path is outside the managed build directory: ${path}" ;;
  esac
  [[ -e "${path}" ]] || die "TriCera ${name} path does not exist: ${path}"
  [[ -x "${path}" ]] || die "TriCera ${name} path is not executable: ${path}"

  resolved="$(readlink -f -- "${path}")" || die "could not resolve TriCera ${name} path: ${path}"
  [[ "${resolved}" != *$'\n'* && "${resolved}" != *$'\r'* ]] || die "resolved TriCera ${name} path contains a newline"
  [[ "${resolved}" == /* ]] || die "resolved TriCera ${name} path is not absolute: ${resolved}"
  case "${resolved}" in
    "${managed_root}"*) ;;
    *) die "resolved TriCera ${name} path is outside the managed build directory: ${resolved}" ;;
  esac
}

install_link() {
  local source=$1
  local destination=$2
  local source_resolved
  local destination_resolved

  [[ "${source}" != *$'\n'* && "${source}" != *$'\r'* ]] || die "TriCera source path contains a newline: ${source}"
  [[ "${destination}" != *$'\n'* && "${destination}" != *$'\r'* ]] || die "TriCera destination path contains a newline: ${destination}"
  [[ "${source}" == /* ]] || die "TriCera source path is not absolute: ${source}"
  [[ "${destination}" == /* ]] || die "TriCera destination path is not absolute: ${destination}"
  [[ -L "${destination}" || ! -e "${destination}" ]] || die "refusing to replace an existing file in the managed prefix: ${destination}"

  ln -sfn -- "${source}" "${destination}"
  [[ -L "${destination}" ]] || die "TriCera link was not created: ${destination}"
  source_resolved="$(readlink -f -- "${source}")" || die "could not resolve TriCera source: ${source}"
  destination_resolved="$(readlink -f -- "${destination}")" || die "could not resolve TriCera link: ${destination}"
  [[ "${destination_resolved}" == "${source_resolved}" ]] || die "TriCera link target is incorrect: ${destination}"
  [[ -x "${destination}" ]] || die "TriCera link is not executable: ${destination}"
}

install_helpers() {
  local source_bin="${REPO_ROOT}/Dockerfiles/bin"
  local executable
  local module
  for executable in autodeduct-contract-assistant autodeduct-contract-assistant-gui; do
    [[ -f "${source_bin}/${executable}" ]] || die "helper source is missing: ${source_bin}/${executable}"
    install -m 0755 "${source_bin}/${executable}" "${BIN_ROOT}/${executable}"
  done
  for module in \
    autodeduct_contract_assistant_draft.py \
    autodeduct_contract_assistant_framac.py \
    autodeduct_contract_assistant_openai.py \
    autodeduct_contract_assistant_project.py; do
    [[ -f "${source_bin}/${module}" ]] || die "helper source is missing: ${source_bin}/${module}"
    install -m 0644 "${source_bin}/${module}" "${BIN_ROOT}/${module}"
  done
}

write_opam_wrapper() {
  local command_name=$1
  local destination="${BIN_ROOT}/${command_name}"
  local opam_path
  opam_path="$(command -v opam)"
  local temporary
  temporary="$(mktemp "${prefix}/.wrapper.XXXXXX")"
  cat >"${temporary}" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
OPAMROOT=$(printf '%q' "${OPAM_ROOT}") OPAMSWITCH=$(printf '%q' "${switch_name}") exec "${opam_path}" --cli=2.1 exec -- "${command_name}" "\$@"
EOF
  install -m 0755 "${temporary}" "${destination}"
  rm -f -- "${temporary}"
}

write_env_file() {
  local temporary
  temporary="$(mktemp "${prefix}/.env.XXXXXX")"
  cat >"${temporary}" <<EOF
# Source this file to use the AutoDeduct OPAM installation.
export AUTODEDUCT_PREFIX=$(printf '%q' "${prefix}")
export OPAMROOT=$(printf '%q' "${OPAM_ROOT}")
export AUTODEDUCT_SWITCH=$(printf '%q' "${switch_name}")
export WHY3CONFIG=$(printf '%q' "${WHY3_CONFIG}")
eval "\$(OPAMROOT=$(printf '%q' "${OPAM_ROOT}") OPAMSWITCH=$(printf '%q' "${switch_name}") opam --cli=2.1 env --set-switch)"
export PATH=$(printf '%q' "${BIN_ROOT}"):\${PATH}
EOF
  install -m 0644 "${temporary}" "${prefix}/env.sh"
  rm -f -- "${temporary}"
}

write_package_list() {
  local temporary
  temporary="$(mktemp "${prefix}/.packages.XXXXXX")"
  {
    printf '# OPAM packages in switch %s\n' "${switch_name}"
    opam_switch_cmd list --installed --short
    printf '\n# OPAM pins\n'
    opam_switch_cmd pin list
  } >"${temporary}"
  install -m 0644 "${temporary}" "${PACKAGE_LIST_FILE}"
  rm -f -- "${temporary}"
}

write_manifest() {
  local tricera_dir="${SOURCE_ROOT}/tricera"
  local examples_dir="${SOURCE_ROOT}/auto-deduct-examples"
  local temporary
  temporary="$(mktemp "${prefix}/.manifest.XXXXXX")"
  {
    printf 'MANIFEST_VERSION=1\n'
    printf 'PREFIX=%s\n' "${prefix}"
    printf 'OPAM_ROOT=%s\n' "${OPAM_ROOT}"
    printf 'SWITCH=%s\n' "${switch_name}"
    printf 'OPAM_VERSION=%s\n' "${opam_version}"
    printf 'OPAM_REPOSITORY_REF=%s\n' "${OPAM_REPOSITORY_REF}"
    printf 'OPAM_ARCHIVE_MIRROR=%s\n' "${OPAM_ARCHIVE_MIRROR}"
    printf 'OPAM_INIT_CONFIG=%s\n' "${OPAM_INIT_CONFIG}"
    printf 'OCAML_VERSION=%s\n' "$(opam_exec ocamlc -version)"
    printf 'FRAMA_C_VERSION=%s\n' "$(opam_exec frama-c -version | head -n1)"
    printf 'WHY3_VERSION=%s\n' "${WHY3_VERSION}"
    printf 'ALT_ERGO_PACKAGE=%s\n' "${ALT_ERGO_PACKAGE}"
    printf 'ALT_ERGO_VERSION=%s\n' "${ALT_ERGO_VERSION}"
    printf 'SAIDA_REF=%s\n' "${SAIDA_REF}"
    printf 'SAIDA_COMMIT=%s\n' "${SAIDA_COMMIT}"
    printf 'ISP_REF=%s\n' "${ISP_REF}"
    printf 'ISP_COMMIT=%s\n' "${ISP_COMMIT}"
    printf 'TRICERA_REF=%s\n' "$(git -C "${tricera_dir}" rev-parse HEAD)"
    printf 'SBT_VERSION=%s\n' "${SBT_VERSION}"
    printf 'EXAMPLES_REF=%s\n' "${EXAMPLES_REF}"
    printf 'EXAMPLES_COMMIT=%s\n' "$(git -C "${examples_dir}" rev-parse HEAD)"
    printf 'Z3_APT_VERSION=%s\n' "$(dpkg-query -W -f='${Version}' "${Z3_APT_PACKAGE}" 2>/dev/null || printf unavailable)"
    printf 'CVC4_APT_VERSION=%s\n' "$(dpkg-query -W -f='${Version}' "${CVC4_APT_PACKAGE}" 2>/dev/null || printf unavailable)"
    printf 'JAVA_VERSION=%s\n' "$(java -version 2>&1 | head -n1)"
    printf 'WHY3_CONFIG=%s\n' "${WHY3_CONFIG}"
  } >"${temporary}"
  install -m 0644 "${temporary}" "${MANIFEST_FILE}"
  rm -f -- "${temporary}"
}

init_opam
create_or_check_switch
install_opam_packages
install_why3_config

build_tricera
validate_tricera_executable_path "${TRICERA_TRI_PATH}" tri
validate_tricera_executable_path "${TRICERA_TRI_PP_PATH}" tri-pp
validate_tricera_executable_path "${TRICERA_TRI_CLIENT_PATH}" tri-client
install_link "${TRICERA_TRI_PATH}" "${BIN_ROOT}/tri"
install_link "${TRICERA_TRI_PP_PATH}" "${BIN_ROOT}/tri-pp"
install_link "${TRICERA_TRI_CLIENT_PATH}" "${BIN_ROOT}/tri-client"

examples_dir="${SOURCE_ROOT}/auto-deduct-examples"
init_git_checkout "${examples_dir}" "${EXAMPLES_REPO_URL}" "${EXAMPLES_COMMIT}"

install_helpers
for command_name in frama-c why3 alt-ergo; do
  write_opam_wrapper "${command_name}"
done
write_env_file
write_package_list
write_manifest

info "installation complete"
info "source ${prefix}/env.sh to activate the toolchain"
