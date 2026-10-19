{ pkgs, lib, pyproject-build-systems, pyproject-nix, uv2nix, kubeconfig, benchmark_manifests_dir }:
let 
      python = pkgs.python312;
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };
      pyprojectOverrides = final: prev: { 
        logging = prev.logging.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ final.resolveBuildSystem {
            setuptools = [ ];
          };
        });
      };
      pythonSet = (pkgs.callPackage pyproject-nix.build.packages { inherit python; }).overrideScope
          (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
              pyprojectOverrides
            ]
          );
      virtualenv = pythonSet.mkVirtualEnv "dev-env" workspace.deps.all;
in
{
    devShell = pkgs.mkShell {
        packages = with pkgs; [ 
            python3 
            uv 
            kubectl
        ];

        env = {
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
                pkgs.stdenv.cc.cc.lib
            ];

            BENCHMARK_MANIFESTS_DIR = benchmark_manifests_dir;
            PROMETHEUS_URL = "http://k8s-master:30954";
            LOCUST_SOCIAL_NETWORK = "http://k8s-master:30006";
            LOCUST_OTEL_DEMO = "http://k8s-master:30008";
            LOCUST_HOTEL_RESERVATION = "http://k8s-master:30009";
            LOCUST_ONLINE_BOUTIQUE = "http://k8s-master:30012";
            LOCUST_MEDIA_MICROSERVICES = "http://k8s-master:30013";
        };

        KUBECONFIG = kubeconfig;
    };
    packages = {
        manager = virtualenv;
    };
}
