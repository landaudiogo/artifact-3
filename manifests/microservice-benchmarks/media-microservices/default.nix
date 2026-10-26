{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "media-microservices-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-jjAElUC0MZ2yioV1tICszZJido1JiWVTL6ABwKTG5qE=";

    buildInputs = with pkgs; [
        kubectl
        kubernetes-helm
    ];

    installPhase = ''
        mkdir $out
        kubectl kustomize --enable-helm ./application > $out/application.yaml
        kubectl kustomize --enable-helm ./load > $out/load.yaml
    '';
}
