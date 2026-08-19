{ pkgs, stdenv, lib }:
{
    packages = {
        cpu-stress = stdenv.mkDerivation {
            name = "host-cpu-stress";
            dontUnpack = true;
            
            buildInputs = with pkgs; [ 
                bash 
                makeWrapper
            ];

            installPhase = ''
                mkdir -p $out/bin
                install -Dm 555 ${./cpu-stress.sh} $out/bin/host-cpu-stress
                wrapProgram $out/bin/host-cpu-stress --prefix PATH : ${lib.makeBinPath [
                    pkgs.systemd
                    pkgs.stress-ng
                    pkgs.coreutils
                ]} 
            '';
        };
        block-latency = stdenv.mkDerivation {
            name = "host-block-latency";
            dontUnpack = true;
            
            buildInputs = with pkgs; [
                bash
                makeWrapper
            ];

            installPhase = ''
                mkdir -p $out/bin
                install -Dm 555 ${./block-latency.sh} $out/bin/host-block-latency
                wrapProgram $out/bin/host-block-latency --prefix PATH : ${lib.makeBinPath [
                    pkgs.coreutils
                    pkgs.lvm2
                    pkgs.gawk
                ]} 
            '';
        };
    };
}
