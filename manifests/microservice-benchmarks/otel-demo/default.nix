{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "social-network-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-QzmetCegxjyYeO4+NR64u1IYx4WXik43nC9mDylUx8E=";

    buildInputs = with pkgs; [
        kubectl
        kubernetes-helm
    ];

    installPhase = ''
        kubectl kustomize --enable-helm ./ > $out
    '';
}
