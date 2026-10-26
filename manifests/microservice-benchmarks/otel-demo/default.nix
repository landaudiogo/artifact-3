{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "otel-demo-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-+wQ55fK+HkJO0bYUqbtJd+3Z+pv5myVRAzzB2CPXqDo=";

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
