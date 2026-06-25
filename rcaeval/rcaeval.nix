{ pkgs, lib, pyproject-build-systems, pyproject-nix, uv2nix }:
let 
  python = pkgs.python312;
  rcaeval = pkgs.stdenv.mkDerivation {
    name = "rcaeval";
    src = builtins.fetchGit {
      url = "https://github.com/phamquiluan/RCAEval";
      ref = "main";
      rev = "5e96b700445bfb5c599e505ecf37d53bf847bbeb";
    };
    buildPhase = ''
        cp ${./pyproject.toml} ./pyproject.toml
        cp ${./uv.lock} ./uv.lock
    '';
    installPhase = ''
        cp -r ./ $out
    '';
  };
  workspace = uv2nix.lib.workspace.loadWorkspace { 
    workspaceRoot = rcaeval; 
  };
  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };
  pyprojectOverrides = final: prev: {
        causal-learn = prev.causal-learn.overrideAttrs (old: {
            postInstall = ''
                cp "${rcaeval}/lib/causallearn/utils/PCUtils/SkeletonDiscovery.py" "$out/lib/python3.12/site-packages/causallearn/utils/PCUtils/"
                cp "${rcaeval}/lib/causallearn/graph/GraphClass.py" "$out/lib/python3.12/site-packages/causallearn/graph/"
                cp "${rcaeval}/lib/causallearn/search/ConstraintBased/FCI.py" "$out/lib/python3.12/site-packages/causallearn/search/ConstraintBased/"
                cp "${rcaeval}/lib/causallearn/utils/Fas.py" "$out/lib/python3.12/site-packages/causallearn/utils/"
            '';
        });

        pyagrum = prev.pyagrum.overrideAttrs (old: {
            postInstall = ''
                cp "${rcaeval}/lib/pyAgrum/lib/image.py" "$out/lib/python3.12/site-packages/pyAgrum/lib/"
            '';
        });

        torch = prev.torch.overrideAttrs (old:
        let
          cudaPkgs = [
            final.nvidia-cuda-runtime
            final.nvidia-cusparselt-cu13
            final.nvidia-cusparse
            final.nvidia-cufile
            final.nvidia-cublas
            final.nvidia-cusolver
            final.nvidia-cudnn-cu13
            final.nvidia-cuda-cupti
            final.nvidia-cuda-nvrtc
            final.nvidia-cufft
            final.nvidia-nvshmem-cu13
            final.nvidia-curand
            final.nvidia-nccl-cu13
            final.nvidia-cusolver
          ];
        in {

          propagatedBuildInputs = (old.propagatedBuildInputs or []) ++ cudaPkgs;

          autoPatchelfIgnoreMissingDeps = (old.autoPatchelfIgnoreMissingDeps or []) ++ [ "libcuda.so.1" ];
          preFixup = (old.preFixup or "") + ''
            addAutoPatchelfSearchPath ${final.nvidia-cuda-runtime}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cusparselt-cu13}/${python.sitePackages}/nvidia/cusparselt/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cusparse}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cufile}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cublas}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cudnn-cu13}/${python.sitePackages}/nvidia/cudnn/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cuda-cupti}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cuda-nvrtc}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cufft}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-nvshmem-cu13}/${python.sitePackages}/nvidia/nvshmem/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-curand}/${python.sitePackages}/nvidia/cu13/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-nccl-cu13}/${python.sitePackages}/nvidia/nccl/lib || true
            addAutoPatchelfSearchPath ${final.nvidia-cusolver}/${python.sitePackages}/nvidia/cu13/lib || true
          '';
        });

      nvidia-cusolver = prev.nvidia-cusolver.overrideAttrs (old: {
            propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
              final.nvidia-nvjitlink
              final.nvidia-cublas

              final.nvidia-cusparse
            ];

            preFixup = (old.preFixup or "") + ''
              addAutoPatchelfSearchPath ${final.nvidia-nvjitlink}/${python.sitePackages}/nvidia/cu13/lib || true
              addAutoPatchelfSearchPath ${final.nvidia-cublas}/${python.sitePackages}/nvidia/cu13/lib || true

              addAutoPatchelfSearchPath ${final.nvidia-cusparse}/${python.sitePackages}/nvidia/cu13/lib || true
            '';
      });

      nvidia-nvshmem-cu13 = prev.nvidia-nvshmem-cu13.overrideAttrs (old: {
            propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
              pkgs.rdma-core
              pkgs.openmpi
            ];
      });

      nvidia-cusparse = prev.nvidia-cusparse.overrideAttrs (old: {
            propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
              final.nvidia-nvjitlink
            ];

            preFixup = (old.preFixup or "") + ''
              addAutoPatchelfSearchPath ${final.nvidia-nvjitlink}/${python.sitePackages}/nvidia/cu13/lib || true
            '';
      });
    
      nvidia-cufile = prev.nvidia-cufile.overrideAttrs (old: {
        propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
          pkgs.rdma-core
        ];
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
in
{
    package = pythonSet.mkVirtualEnv "rcaeval-env" workspace.deps.default;
}
