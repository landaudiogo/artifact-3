{ pkgs, ... }:
let 
    online-boutique = pkgs.callPackage ./online-boutique { };
in
{
    packages = {
        online-boutique = online-boutique;
    };
}
