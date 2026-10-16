{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "social-network-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-X07Dbt4Mcyk8YPcof8/w0Vg7MJ/rxIfBG/STr5Bqx3A=";

    buildInputs = with pkgs; [
        kubectl
        kubernetes-helm
    ];

    installPhase = ''
        kubectl kustomize --enable-helm ./ > $out
    '';
}
