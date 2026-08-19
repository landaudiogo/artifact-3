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
    };
}
