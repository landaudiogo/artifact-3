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
      service-cpu-stress = pkgs.callPackage ./src/injector/service { };
in
{
    devShell = pkgs.mkShell {
        packages = with pkgs; [ 
            python3 
            uv 
        ];

        KUBECONFIG = kubeconfig;
    };
    packages = {
        manager = virtualenv;
        service-cpu-stress = service-cpu-stress.package;
    };
}
