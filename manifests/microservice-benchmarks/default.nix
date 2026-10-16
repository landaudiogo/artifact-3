{ pkgs, ... }:
let 
    online-boutique = pkgs.callPackage ./online-boutique { };
    media-microservices = pkgs.callPackage ./media-microservices { };
    social-network = pkgs.callPackage ./social-network { };
    hotel-reservation = pkgs.callPackage ./hotel-reservation { };
in
{
    packages = {
        inherit online-boutique;
        inherit media-microservices;
        inherit social-network;
        inherit hotel-reservation;
    };
}
