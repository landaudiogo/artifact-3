{
    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";

        # uv2nix dependencies
        pyproject-nix = {
          url = "github:pyproject-nix/pyproject.nix";
          inputs.nixpkgs.follows = "nixpkgs";
        };
        uv2nix = {
          url = "github:pyproject-nix/uv2nix";
          inputs.pyproject-nix.follows = "pyproject-nix";
          inputs.nixpkgs.follows = "nixpkgs";
        };
        pyproject-build-systems = {
          url = "github:pyproject-nix/build-system-pkgs";
          inputs.pyproject-nix.follows = "pyproject-nix";
          inputs.uv2nix.follows = "uv2nix";
          inputs.nixpkgs.follows = "nixpkgs";
        };
    };
    outputs = {self, nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ...}:
        let
            system = "x86_64-linux";
            pkgs = import nixpkgs { inherit system; };

            kubeconfig = pkgs.writeText "cluster-admin-kubeconfig" (
              builtins.toJSON {
                apiVersion = "v1";
                kind = "Config";
                clusters = [
                  {
                    name = "local";
                    cluster.certificate-authority = ./nixos/secrets/ca.pem;
                    cluster.server = "https://k8s-master:6443";
                  }
                ];
                users = [
                  {
                    name = "cluster-admin";
                    user = {
                      client-certificate = ./nixos/secrets/cluster-admin.pem;
                      client-key = ./nixos/secrets/cluster-admin-key.pem;
                    };
                  }
                ];
                contexts = [
                  {
                    context = {
                      cluster = "local";
                      user = "cluster-admin";
                    };
                    name = "local";
                  }
                ];
                current-context = "local";
              }
            );

            autothrottle = pkgs.callPackage ./autothrottle { inherit kubeconfig; };
            fault-manager = pkgs.callPackage ./faults/manager { inherit kubeconfig pyproject-nix uv2nix pyproject-build-systems; };
            injectors = pkgs.callPackage ./faults/injectors { };
            manifests = pkgs.callPackage ./manifests { };
        in
        {
            devShells.${system} = {
                default = pkgs.mkShell {
                    packages = with pkgs; [
                        kubectl
                        kubernetes-helm
                        clickhouse
                        k9s
                    ];
                    KUBECONFIG = kubeconfig;
                };
                autothrottle = autothrottle.devShell;
                fault-manager = fault-manager.devShell;
            };
            packages.${system} = {
                fault-manager = fault-manager.packages.manager;
                inherit injectors;
                manifests = manifests.packages;
            };
        };

}
