{ 
    pkgs ? import <nixpkgs> {},
}:
rec {
    packages = {
        postgres = pkgs.stdenv.mkDerivation {
            name = "postgres-fault";
            dontUnpack = true;

            buildInputs = [
                (pkgs.python3.withPackages (py-pkgs: with py-pkgs; [
                    psycopg2
                    click
                ]))
            ];

            installPhase = ''
                mkdir -p $out/bin
                install -Dm 555 ${./postgres.py} $out/bin/postgres-fault
            '';
        };
    };
    images = {
        postgres = pkgs.dockerTools.buildImage {
            name = "postgres-fault";
            tag = "latest";
            copyToRoot = [ packages.postgres ];
            config = {
                Entrypoint = [ "/bin/postgres-fault" ];
            };
        };
    };
}
