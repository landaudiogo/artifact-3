#! bash

# This script depends on:
# - coreutils: basename
# - lvm2: dmsetup
# - gawk: awk

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
    delay_device="delay100"
    if ! dmsetup info "$delay_device"; then
        echo "unknown delay device: $delay_device"
        exit 1
    fi

    blocksize="$(dmsetup table "$delay_device" | awk '{print $2}')"
    bgdevice="$(dmsetup table "$delay_device" | awk '{print $4}')"

    dmsetup reload "$delay_device" --table "0 $blocksize delay $bgdevice 0 500 $bgdevice 0 500 $bgdevice 0 500"
    dmsetup resume "$delay_device" 
}

recover () {
    delay_device="delay100"
    if ! dmsetup info "$delay_device"; then
        echo "unknown delay device: $delay_device"
        exit 1
    fi

    blocksize="$(dmsetup table "$delay_device" | awk '{print $2}')"
    bgdevice="$(dmsetup table "$delay_device" | awk '{print $4}')"

    dmsetup reload "$delay_device" --table "0 $blocksize delay $bgdevice 0 0"
    dmsetup resume "$delay_device" 
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
