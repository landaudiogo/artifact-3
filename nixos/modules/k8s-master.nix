{ pkgs, lib, config, ... }:
let
    localPathManifest = pkgs.stdenv.mkDerivation {
        name = "local-path-manifest";

        outputHashAlgo = "sha256";
        outputHashMode = "recursive";
        # outputHash = lib.fakeHash;
        outputHash = "sha256-YCAF+Jrr9Z9qVTr2UbkMLR6LSeF4fvMTa+e+7Go1PdE=";

        buildInputs = with pkgs; [ wget yq jq ];

        dontUnpack = true;

        buildPhase = ''
            wget --no-check-certificate -O local-path-storage.yaml https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.35/deploy/local-path-storage.yaml
            yq < local-path-storage.yaml | jq -s > local-path-storage.json
        '';

        installPhase = ''
            cp local-path-storage.json $out
        '';
    };
    localPathResources_ = builtins.fromJSON (builtins.readFile localPathManifest);
    addLabels = item: lib.recursiveUpdate item {
        metadata = {
          labels = {
            "addonmanager.kubernetes.io/mode" = "Reconcile";
            "kubernetes.io/cluster-service" = "true";
            "k8s-app" = "kube-storage";
          };
        };
    };
    localPathResources = builtins.map addLabels localPathResources_;
in
{
    services.kubernetes = {
        roles = [ "master" ];
        masterAddress = "k8s-master";

        # Self-Signed Certs
        easyCerts = false;
        caFile = "${config.services.kubernetes.secretsPath}/ca.pem";
        pki = {
            enable = true;
            genCfsslCACert = false;
            genCfsslAPIToken = false;
            cfsslAPIExtraSANs = [ "k8s-master" ];
        };

        clusterCidr = "10.42.0.0/16";
        controllerManager.extraOpts = "--service-cluster-ip-range=10.43.0.0/16";
        apiserver.serviceClusterIpRange = "10.43.0.0/16";
        apiserver.extraSANs = [ "k8s-master" ];
        apiserver.allowPrivileged = true;

        kubelet.extraOpts = "--fail-swap-on=false";

        addonManager.bootstrapAddons = {
            local-path-storage = {
                kind = "List";
                apiVersion = "v1";
                items = localPathResources;
            };
        };
    };

    systemd.tmpfiles.rules = [
    #    Type | Destination                                              | Mode | User  | Group  | Age | Source
        "C      ${config.services.kubernetes.pki.caCertPathPrefix}.pem     0600   cfssl   cfssl    -     ${../secrets/ca.pem}"
        "C      ${config.services.kubernetes.pki.caCertPathPrefix}-key.pem 0600   cfssl   cfssl    -     ${../secrets/ca-key.pem}"
        "C      ${config.services.cfssl.dataDir}/apitoken.secret           0600   cfssl   cfssl    -     ${../secrets/apitoken}"
    ];

    # For some reason, there is an issue when the SANs have colon's in their 
    # names, e.g., system:node:alcaraz. This led to requests to sign a 
    # certificates without the extra SANs. However, on re-inspection, certmgr 
    # would identify this mismatch and ask to sign another certificate, again
    # without the SAN. Ultimately, the repetition of this cycle caused kubelet
    # and the kube-apiserver to restart, and specified on the certmgr's 
    # configuration file.
    services.certmgr.specs.apiserverKubeletClient.request.hosts = [];
    services.certmgr.specs.serviceAccount.request.hosts = [];
    services.certmgr.specs.controllerManagerClient.request.hosts = [];
    services.certmgr.specs.kubeProxyClient.request.hosts = [];
    services.certmgr.specs.schedulerClient.request.hosts = [];
    services.certmgr.specs.kubeletClient.request.hosts = [];
    services.certmgr.specs.addonManager.request.hosts = [];

    networking.firewall.allowedTCPPorts = [ 6443 8888 ];

    # virtualisation.containerd.settings.plugins."io.containerd.grpc.v1.cri".registry = {
    #     mirrors = {
    #         "k8s-master:30002" = {
    #             endpoint = [ "http://k8s-master:30002" ];
    #         };
    #     };
    #     configs."k8s-master:30002".tls.insecure_skip_verify = true;
    # };
}
