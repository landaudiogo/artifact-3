{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "social-network-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-WFSmLljFweXOMxZCw0mCXbv8K8gaf/S9yx2V4Cj3R+k=";

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
