{ pkgs }:
let
    service = pkgs.callPackage ./service {};
    host = pkgs.callPackage ./host {};
in
pkgs.symlinkJoin {
    name = "injectors"; 
    paths = []
        ++ (builtins.attrValues service.packages)
        ++ (builtins.attrValues host.packages);
}
