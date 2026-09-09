#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <uploaded-snippet> <backup-config>" >&2
    exit 2
fi

snippet_source="$1"
backup_config="$2"
config="/etc/nginx/sites-available/default"
snippet_dest="/etc/nginx/snippets/mango74-static-v2.conf"
release_dir="/var/www/mango74-releases/472d988b"
release_link="/var/www/mango74"
expected_config_hash="5421a2eb22e3bb30db7e067881b52f43e8b6e271c7de9445dfada874fb448fd9"
expected_snippet_hash="1d75836affbe0b4843364eeae5cb4b6c1486e360e5ae2240ed8f1a72c0dc936a"
include_line="    include ${snippet_dest};"
server_pattern='^[[:space:]]*server_name[[:space:]]+www\.mangosgo\.com[[:space:]]+mangosgo\.com;'
modified=0
completed=0

restore_config() {
    trap - EXIT
    if [[ "$modified" -eq 1 && "$completed" -eq 0 ]]; then
        echo "ROLLBACK: restoring the recorded Nginx configuration"
        sudo cp -a "$backup_config" "$config"
        if sudo nginx -t; then
            sudo systemctl reload nginx
            echo "ROLLBACK PASS: known-good configuration restored"
        else
            echo "ROLLBACK FAILED: restored configuration did not validate" >&2
        fi
    fi
}
trap restore_config EXIT

for required in "$snippet_source" "$backup_config" "$config" "$release_dir/index.html"; do
    if [[ ! -f "$required" ]]; then
        echo "STOP: required file is missing: $required" >&2
        exit 1
    fi
done

if [[ "$(sha256sum "$snippet_source" | awk '{print $1}')" != "$expected_snippet_hash" ]]; then
    echo "STOP: uploaded snippet hash mismatch" >&2
    exit 1
fi

if [[ "$(sha256sum "$backup_config" | awk '{print $1}')" != "$expected_config_hash" ]]; then
    echo "STOP: backup configuration hash mismatch" >&2
    exit 1
fi

if [[ "$(sudo readlink -f "$release_link")" != "$release_dir" ]]; then
    echo "STOP: /var/www/mango74 does not point to the approved release" >&2
    exit 1
fi

if sudo test -e "$snippet_dest"; then
    installed_hash="$(sudo sha256sum "$snippet_dest" | awk '{print $1}')"
    if [[ "$installed_hash" != "$expected_snippet_hash" ]]; then
        echo "STOP: destination snippet exists with a different hash" >&2
        exit 1
    fi
else
    sudo install -o root -g root -m 0644 "$snippet_source" "$snippet_dest"
fi

if sudo grep -Fqx "$include_line" "$config"; then
    echo "INFO: Mango74 include is already present"
else
    current_hash="$(sudo sha256sum "$config" | awk '{print $1}')"
    if [[ "$current_hash" != "$expected_config_hash" ]]; then
        echo "STOP: active configuration changed after the recorded backup" >&2
        exit 1
    fi

    target_count="$(sudo grep -Ec "$server_pattern" "$config")"
    if [[ "$target_count" -ne 1 ]]; then
        echo "STOP: expected one www.mangosgo.com server_name, found $target_count" >&2
        exit 1
    fi

    target_line="$(sudo grep -nE "$server_pattern" "$config" | cut -d: -f1)"
    sudo sed -i "${target_line}a\\${include_line}" "$config"
    modified=1
fi

if [[ "$(sudo grep -Fxc "$include_line" "$config")" -ne 1 ]]; then
    echo "STOP: include line was not installed exactly once" >&2
    exit 1
fi

sudo nginx -t
sudo systemctl reload nginx

curl_origin=(curl --noproxy '*' -ksS --connect-timeout 1 --max-time 2 --resolve www.mangosgo.com:443:127.0.0.1)
probe_status() {
    "${curl_origin[@]}" -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || printf '000'
}

asset_file="$(find "$release_dir/_next/static" -type f -print -quit)"
asset_url="/mango74/${asset_file#"$release_dir/"}"

status_redirect="000"
status_index="000"
status_asset="000"
for attempt in $(seq 1 15); do
    status_redirect="$(probe_status https://www.mangosgo.com/mango74)"
    status_index="$(probe_status https://www.mangosgo.com/mango74/)"
    status_asset="$(probe_status "https://www.mangosgo.com${asset_url}")"
    if [[ "$status_redirect" == "308" && "$status_index" == "200" && \
          "$status_asset" == "200" ]]; then
        echo "INFO: reloaded Nginx worker ready after attempt $attempt"
        break
    fi
    sleep 1
done

status_root="$(probe_status https://www.mangosgo.com/)"
status_verse="$(probe_status https://www.mangosgo.com/verse)"

printf '%s\n' \
    "origin / status=$status_root" \
    "origin /verse status=$status_verse" \
    "origin /mango74 status=$status_redirect" \
    "origin /mango74/ status=$status_index" \
    "origin asset status=$status_asset"

if [[ "$status_root" != "200" || "$status_verse" != "301" || \
      "$status_redirect" != "308" || "$status_index" != "200" || \
      "$status_asset" != "200" ]]; then
    echo "STOP: origin acceptance failed" >&2
    exit 1
fi

if [[ "$(systemctl is-active nginx)" != "active" ]]; then
    echo "STOP: nginx is not active after reload" >&2
    exit 1
fi

completed=1
trap - EXIT
echo "PASS: Mango74 origin route activated without stopping Nginx"
