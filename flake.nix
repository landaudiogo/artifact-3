{
    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
    };
    outputs = {self, nixpkgs, ...}:
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
            };
        };

}
