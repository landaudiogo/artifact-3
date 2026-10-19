{ pkgs, lib, pyproject-build-systems, pyproject-nix, uv2nix, kubeconfig, manifest_online_boutique }:
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
            PROMETHEUS_URL = "http://k8s-master:30954";

            MANIFEST_ONLINE_BOUTIQUE = manifest_online_boutique;
            LOCUST_ONLINE_BOUTIQUE = "http://k8s-master:30012";
        };

        KUBECONFIG = kubeconfig;
    };
    packages = {
        manager = virtualenv;
    };
}
