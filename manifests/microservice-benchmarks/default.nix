{ pkgs, ... }:
let 
    online-boutique = pkgs.callPackage ./online-boutique { };
    media-microservices = pkgs.callPackage ./media-microservices { };
    social-network = pkgs.callPackage ./social-network { };
in
{
    packages = {
        inherit online-boutique;
        inherit media-microservices;
        inherit social-network;
    };
}
