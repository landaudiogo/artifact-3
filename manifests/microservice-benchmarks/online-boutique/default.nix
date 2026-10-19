{ pkgs, stdenv, lib, ... }:
stdenv.mkDerivation {
    name = "online-boutique-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-9kBViUYiHb9B+XGYYlUq1oh+YxzBpgF3K9QJ5NK/FK0=";

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
