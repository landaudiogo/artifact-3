{
    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
        nixpkgs-24.url = "github:nixos/nixpkgs/336eda0d07dc5e2be1f923990ad9fdb6bc8e28e3";

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
    outputs = { self, nixpkgs, nixpkgs-24, pyproject-nix, pyproject-build-systems, uv2nix }:
        let
            system = "x86_64-linux";

            pkgs = import nixpkgs { inherit system; config = { allowUnfree = true; }; };
            rcaeval = pkgs.callPackage ./rcaeval.nix { 
                inherit pyproject-build-systems pyproject-nix uv2nix;
            };
        in
        {
            packages.${system} = {
                rcaeval = rcaeval.package;
            };
        };
}
