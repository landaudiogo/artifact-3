{
    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    };

    outputs = { self, nixpkgs, ... }@inputs:
        let
            system = "x86_64-linux";
            pkgs = import nixpkgs { inherit system; };
        in rec {
            devShells.${system} = {
                default = pkgs.mkShell {
                    packages = with pkgs; [
                        cfssl
                        certmgr
                    ];
                };
            };
            nixosConfigurations = {
                k8s-master = nixpkgs.lib.nixosSystem {
                    specialArgs = { inherit inputs; };
                    modules = [
                        ./hosts/k8s-master
                    ];
                };
                k8s-worker1 = nixpkgs.lib.nixosSystem {
                    specialArgs = { inherit inputs; };
                    modules = [
                        ./hosts/k8s-worker1
                    ];
                };
                k8s-worker2 = nixpkgs.lib.nixosSystem {
                    specialArgs = { inherit inputs; };
                    modules = [
                        ./hosts/k8s-worker2
                    ];
                };
                k8s-worker3 = nixpkgs.lib.nixosSystem {
                    specialArgs = { inherit inputs; };
                    modules = [
                        ./hosts/k8s-worker3
                    ];
                };
            };
        };
}
