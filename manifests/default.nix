{ pkgs, ... }:
let
    microservice-benchmarks = pkgs.callPackage ./microservice-benchmarks { };
in

{
    packages = {
        microservice-benchmarks = microservice-benchmarks.packages;
    };
}
