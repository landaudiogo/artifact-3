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
        mongodb = pkgs.stdenv.mkDerivation {
            name = "mongodb-fault";
            dontUnpack = true;

            buildInputs = [
                (pkgs.python3.withPackages (py-pkgs: with py-pkgs; [
                    psycopg2
                    click
                    pymongo
                ]))
            ];

            installPhase = ''
                mkdir -p $out/bin
                install -Dm 555 ${./mongodb.py} $out/bin/mongodb-fault
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
        mongodb = pkgs.dockerTools.buildImage {
            name = "mongodb-fault";
            tag = "latest";
            copyToRoot = [ packages.mongodb ];
            config = {
                Entrypoint = [ "/bin/mongodb-fault" ];
            };
        };
    };
}
