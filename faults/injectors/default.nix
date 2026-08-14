{ pkgs }:
let
    service = pkgs.callPackage ./service {};
in
pkgs.symlinkJoin {
    name = "injectors"; 
    paths = builtins.attrValues service.packages;
}
