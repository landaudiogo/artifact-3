{ pkgs, stdenv, lib, ... }:
stdenv.mkDerivation {
    name = "online-boutique-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-FQ4rKCU/wPG0uqBwmeIZcu6u+R/XSm7tnqm2QMjG/X4=";

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
