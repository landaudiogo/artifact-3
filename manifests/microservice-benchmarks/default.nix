{ pkgs, stdenv, ... }:
let 
    online-boutique = pkgs.callPackage ./online-boutique { };
    media-microservices = pkgs.callPackage ./media-microservices { };
    social-network = pkgs.callPackage ./social-network { };
    hotel-reservation = pkgs.callPackage ./hotel-reservation { };
    otel-demo = pkgs.callPackage ./otel-demo { };
in
{
    packages = rec {
        default = stdenv.mkDerivation {
            name = "manifests";
            dontUnpack = true;
            
            installPhase = ''
                mkdir $out
                ln -s ${online-boutique} $out/online-boutique
                ln -s ${social-network} $out/social-network
                ln -s ${hotel-reservation} $out/hotel-reservation
                ln -s ${media-microservices} $out/media-microservices
                ln -s ${otel-demo} $out/otel-demo
            '';
        };
        inherit online-boutique;
        inherit media-microservices;
        inherit social-network;
        inherit hotel-reservation;
        inherit otel-demo;
    };
}
