#! bash

# This script depends on:
# - coreutils: basename
# - lvm2: dmsetup
# - gawk: awk

set -e

script=$(basename "$0")

USAGE="
Usage: $script <action> <pod-uid>

Positional parameters:
    action: can either be 'attack' or 'recover'
    pod-uid: The pod uid that can be obtained from its metadata.uid attribute
"

if (( $# != 2 )); then
    echo "$USAGE"
    exit 1
fi

attack () {
    if [[ -z "$1" ]]; then
        echo "attack called without arguments"
        exit 1
    fi

    delay_device="poddelay_$1"
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
    if [[ -z "$1" ]]; then
        echo "recover called without arguments"
        exit 1
    fi

    delay_device="poddelay_$1"
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
pod_uid="$2"

case "$action" in
    "attack")
        attack "$pod_uid"
        ;;
    "recover")
        recover "$pod_uid"
        ;; 
    *)
        echo "$USAGE"
        exit 1
        ;;
esac
