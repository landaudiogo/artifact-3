{ pkgs, stdenv, lib, ... }:
stdenv.mkDerivation {
    name = "online-boutique-manifest";
    src = ./.;
    dontBuild = true;

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    # outputHash = lib.fakeHash;
    outputHash = "sha256-Flu1rjgKANLIXSaoekXqYXx9FLD3it3E4Oq+3YWsBlc=";

    buildInputs = with pkgs; [
        kubectl
        kubernetes-helm
    ];

    installPhase = ''
        kubectl kustomize --enable-helm ./ > $out
    '';
}
