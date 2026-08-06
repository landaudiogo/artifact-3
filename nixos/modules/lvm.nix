{ pkgs, ... }:
let
    lvmStorage = "/var/lib/lvm";
    volumeGroup = "lvmvg";
in
{
  systemd.services."lvm-setup" = {
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };

    path = with pkgs; [ 
        util-linux 
        coreutils 
        lvm2
        busybox
    ];

    script = ''
      if [ ! -d ${lvmStorage} ]; then
        echo "Create director ${lvmStorage}"
        mkdir -p ${lvmStorage}
      fi

      # for i in 100 101; do
      for i in 100; do
          if [ ! -e "${lvmStorage}/loop$i.img" ]; then
            echo "Allocate 30G ${lvmStorage}/loop$i.img file"
            fallocate -l 30G "${lvmStorage}/loop$i.img"
          fi

          if ! losetup "/dev/loop$i"; then 
            echo "Setup /dev/loop$i"
            losetup "/dev/loop$i" "${lvmStorage}/loop$i.img"
          fi

          if [ ! -e "/dev/mapper/delay$i" ]; then
            echo "Setup /dev/mapper/delay$i"
            dmsetup create delay$i --table "0 $(blockdev --getsize /dev/loop$i) delay /dev/loop$i 0 0"
          fi

          if ! pvs "/dev/mapper/delay$i"; then
            echo "Create lvm physical volume: /dev/mapper/delay$i"
            pvcreate "/dev/mapper/delay$i"
            vgextend "${volumeGroup}" "/dev/mapper/delay$i" || {
                echo "Create lvm volume group: ${volumeGroup}"
                vgcreate "${volumeGroup}" "/dev/mapper/delay$i"
            }
          fi
      done
    '';
  };

  environment.etc."lvm/lvm.conf" = {
    text = ''
        devices { 
            filter= [ 
                "a|^/dev/mapper/delay.*|", 
                "r|.*|"
            ] 
        }
    '';
  };
}
