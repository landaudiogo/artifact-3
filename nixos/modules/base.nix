{ pkgs, inputs, ... }:
{
  imports = [
    "${inputs.nixpkgs}/nixos/modules/profiles/minimal.nix"
  ];

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  nix = {
    settings.experimental-features = ["flakes" "nix-command"];
  };
  nixpkgs.config.allowUnfree = true;

  networking.networkmanager.enable = true;

  services.logind.lidSwitch = "ignore";
  services.openssh = {
    enable = true;
    hostKeys = [{
      path = "/etc/ssh/ssh_host_ed25519_key";
      type = "ed25519";
      comment = "machine-key";
    }];
  };
  environment.systemPackages = with pkgs; [
    vim
  ];


  users.users.root.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJWjd0HS5ustz5grB4u8vtQcz1aINzESPu1ybrN+u6dy root"
  ];

}
