To create certificate authority:
```
cfssl genkey -initca config/kube-pki-cacert-csr.json | cfssljson -bare ./secrets/ca
```


To create apitoken:
```
head -c 16 /dev/urandom | od -An -t x | tr -d ' ' > ./secrets/apitoken
```

Generate another cluster-admin certificate for the kubeconfig:
```
cfssl gencert -ca ./secrets/ca.pem -ca-key ./secrets/ca-key.pem config/cluster-admin-csr.json | cfssljson -bare ./secrets/cluster-admin
```

Debug cluster-admin public key: 
```
nix run nixpkgs#openssl -- x509 -in secrets/cluster-admin.pem -text
```

```bash
sudo nixos-rebuild --flake .#k8s-master --target-host k8s-master switch
sudo nixos-rebuild --flake .#k8s-worker1 --target-host k8s-worker1 switch
sudo nixos-rebuild --flake .#k8s-worker2 --target-host k8s-worker2 switch
sudo nixos-rebuild --flake .#k8s-worker3 --target-host k8s-worker3 switch
```
