{ pkgs, stdenv, lib, ... }:
stdenv.mkDerivation {
    name = "online-boutique-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-AJ3Fj3Z6k9X41pvzeZPycTFdMCJXGM0uJPu1h6xlQVc=";

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
