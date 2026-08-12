{ pkgs, stdenv, lib }:
{
    devShell = pkgs.mkShell {
        packages = with pkgs; [
            (python3.withPackages (py-pkgs: with py-pkgs; [
                click
            ]))
        ];
    };
    packages = {
        cpu-stress = stdenv.mkDerivation {
            name = "service-cpu-stress";
            dontUnpack = true;
            
            buildInputs = with pkgs; [
                (python3.withPackages (py-pkgs: with py-pkgs; [
                    click
                ]))
                makeWrapper
            ];

            installPhase = ''
                mkdir -p $out/bin
                install -Dm 555 ${./cpu.py} $out/bin/service-cpu-stress
                wrapProgram $out/bin/service-cpu-stress --prefix PATH : ${lib.makeBinPath [
                    pkgs.libcgroup # cgexec
                    pkgs.stress-ng
                ]} 
            '';
        };
    };

}
