{ pkgs }:
let
    service = pkgs.callPackage ./service {};
in
pkgs.symlinkJoin {
    name = "injectors"; 
    paths = [ 
        service.packages.cpu-stress
        service.packages.cpu-reduce
    ];
}
