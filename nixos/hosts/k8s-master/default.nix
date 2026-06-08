{ pkgs, inputs, ... }:
{
  imports = [
    ./hardware-configuration.nix
    ../../modules/base.nix
    ../../modules/k8s-master.nix
  ];

  environment.systemPackages = with pkgs; [
    kubectl 
    kubernetes-helm
  ];
}
