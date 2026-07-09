{ pkgs, lib }:
let 
    runtimeDeps = with pkgs; [ iproute2 stress-ng ];
in
pkgs.buildGoModule { 
    name = "chaosd";
    src = builtins.fetchGit {
      url = "https://github.com/chaos-mesh/chaosd/";
      ref = "main";
      rev = "bc039aa483410318170a542f6cf120b7d3391931";
    };
    patches = [ ./dbstore.patch ];
    vendorHash = "sha256-sXkAcppDboqXrWobAlxsvJE9idagV7Xmqd++1FpGwKY=";
    subPackages = [ "cmd" ];
    buildInputs = with pkgs; [ makeWrapper ];
    postInstall = ''
        mv $out/bin/cmd $out/bin/chaosd
        wrapProgram $out/bin/chaosd \
            --set PATH ${lib.makeBinPath runtimeDeps}
    '';
    doCheck = false;
}
