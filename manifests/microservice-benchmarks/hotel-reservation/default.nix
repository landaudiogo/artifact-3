{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "hotel-reservation-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-RPw6U+OpggIrxSnM4GfZASZQy+/NtUbEzs0c0ulq68k=";

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
