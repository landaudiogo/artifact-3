{ pkgs ? import <nixpkgs> {}, stdenv ? pkgs.stdenv, lib ? pkgs.lib, ... }:
stdenv.mkDerivation {
    name = "media-microservices-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-HxDlEuodrLBJNIGz36PAx35vwWnnVRV3XcpLqTiFj7I=";

    buildInputs = with pkgs; [
        kubectl
        kubernetes-helm
    ];

    installPhase = ''
        kubectl kustomize --enable-helm ./ > $out
    '';
}
