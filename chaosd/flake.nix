{
    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    };
    outputs = {self, nixpkgs}:
    let
        system = "x86_64-linux";
        pkgs = import nixpkgs {inherit system; };
    in {
        packages.${system} = rec {
            default = self.packages.${system}.chaosd;
            chaosd = pkgs.callPackage ./. { };
        };

    };
}
