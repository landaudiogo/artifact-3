#! bash

# This script depends on the following nix packages:
# - systemd: systemd-run, systemctl
# - stress-ng: stress-ng
# - coreutils: nproc, basename

set -e

script=$(basename "$0")

USAGE="
Usage: $script <action>

Positional parameters:
    action: can either be 'attack' or 'recover'
"

if (( $# != 1 )); then
    echo "$USAGE"
    exit 1
fi

attack () {
    systemd-run \
        --slice kubepods.slice \
        --unit host-cpu-stress.service \
        -p CPUWeight=10000 \
        stress-ng --cpu "$(nproc --all)" -l 100
}

recover () {
    systemctl stop host-cpu-stress.service
}


action="$1"

case "$action" in
    "attack")
        attack
        ;;
    "recover")
        recover
        ;; 
    *)
        echo "$USAGE"
        exit 1
        ;;
esac
