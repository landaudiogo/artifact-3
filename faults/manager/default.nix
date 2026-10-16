{ pkgs, pyproject-build-systems, pyproject-nix, lib, uv2nix, kubeconfig }:
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
        ];

        env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
        ];

        KUBECONFIG = kubeconfig;
    };
    packages = {
        manager = virtualenv;
    };
}
