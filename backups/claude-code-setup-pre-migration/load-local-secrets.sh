#!/bin/bash

SECRET_LOADER="${HOME}/.config/secret-env/load-keychain-secrets.sh"

if [ -f "$SECRET_LOADER" ]; then
    # shellcheck source=/dev/null
    source "$SECRET_LOADER"
fi

require_secret() {
    local var_name="$1"
    if [ -z "${!var_name:-}" ]; then
        echo "❌ 缺少必需环境变量: $var_name" >&2
        return 1
    fi
}

require_any_secret() {
    local var_name=""
    for var_name in "$@"; do
        if [ -n "${!var_name:-}" ]; then
            return 0
        fi
    done

    echo "❌ 缺少必需环境变量，至少需要以下之一: $*" >&2
    return 1
}
