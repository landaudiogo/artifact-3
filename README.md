nix run github:landaudiogo/ripple-dsb#socialNetwork.initSocialGraph -- --ip k8s-master --port 30001


compose-post-service-576f648c8f-7jtsl     1/1     Running   0              39m   10.42.1.204   k8s-worker1   <none>           <none>
home-timeline-redis-59bbf98796-wmq2d      1/1     Running   0              39m   10.42.1.205   k8s-worker1   <none>           <none>
home-timeline-service-65888567b5-cgphm    1/1     Running   0              39m   10.42.1.206   k8s-worker1   <none>           <none>
jaeger-6dd657fc49-pjp8n                   1/1     Running   0              29m   10.42.3.63    k8s-worker3   <none>           <none>
media-frontend-8bfdb9896-rth75            1/1     Running   0              39m   10.42.1.207   k8s-worker1   <none>           <none>
media-memcached-cddbfd4f9-472cp           1/1     Running   0              39m   10.42.2.4     k8s-worker2   <none>           <none>
media-mongodb-8bc7859cd-m8jnd             1/1     Running   0              39m   10.42.1.208   k8s-worker1   <none>           <none>
media-service-54b96bfd8f-6x924            1/1     Running   0              39m   10.42.1.209   k8s-worker1   <none>           <none>
nginx-thrift-7bb9ff878f-6cnq9             1/1     Running   0              39m   10.42.3.56    k8s-worker3   <none>           <none>
post-storage-memcached-7d75ff7bf7-fhb28   1/1     Running   0              39m   10.42.1.210   k8s-worker1   <none>           <none>
post-storage-mongodb-5fc98df894-mmkmg     1/1     Running   0              39m   10.42.2.5     k8s-worker2   <none>           <none>
post-storage-service-7fdf458f5d-kx5s4     1/1     Running   0              39m   10.42.3.57    k8s-worker3   <none>           <none>
social-graph-mongodb-754db9c898-pw46t     1/1     Running   1 (2m4s ago)   39m   10.42.1.211   k8s-worker1   <none>           <none>
social-graph-redis-6676db777f-x7rr7       1/1     Running   0              39m   10.42.2.7     k8s-worker2   <none>           <none>
social-graph-service-649cf96696-62r9x     1/1     Running   0              39m   10.42.3.58    k8s-worker3   <none>           <none>
text-service-7745997f7d-k2cpp             1/1     Running   0              39m   10.42.1.212   k8s-worker1   <none>           <none>
unique-id-service-75f8b848b7-shc4w        1/1     Running   0              39m   10.42.3.59    k8s-worker3   <none>           <none>
url-shorten-memcached-7cf4fdbf7c-jww4p    1/1     Running   0              39m   10.42.2.8     k8s-worker2   <none>           <none>
url-shorten-mongodb-5d5d7c5b57-rbq9m      1/1     Running   0              39m   10.42.1.213   k8s-worker1   <none>           <none>
url-shorten-service-5b6887766c-5fcfw      1/1     Running   0              39m   10.42.1.214   k8s-worker1   <none>           <none>
user-memcached-65cf6f7dc-f6nx8            1/1     Running   0              39m   10.42.3.60    k8s-worker3   <none>           <none>
user-mention-service-7584497446-jl966     1/1     Running   0              39m   10.42.1.215   k8s-worker1   <none>           <none>
user-mongodb-54545df5-f88fk               1/1     Running   0              39m   10.42.2.9     k8s-worker2   <none>           <none>
user-service-7686bdb96b-xhrm7             1/1     Running   0              39m   10.42.1.216   k8s-worker1   <none>           <none>
user-timeline-mongodb-7599776989-q8lh5    1/1     Running   0              39m   10.42.3.61    k8s-worker3   <none>           <none>
user-timeline-redis-659d8f79bd-gv4qv      1/1     Running   0              39m   10.42.3.62    k8s-worker3   <none>           <none>
user-timeline-service-7f5b4df945-5gh5d    1/1     Running   0              39m   10.42.1.217   k8s-worker1   <none>           <none>

```
kubectl kustomize --enable-helm dependencies | kubectl apply -f - --server-side
kubectl kustomize --enable-helm monitor | kubectl apply -f - --server-side
kubectl kustomize --enable-helm application/social-network | kubectl apply -f - --server-side
kubectl kustomize --enable-helm load/social-network | kubectl apply -f - --server-side
```

```
kubectl kustomize --enable-helm load/social-network | kubectl delete -f -
kubectl kustomize --enable-helm application/social-network | kubectl delete -f -
kubectl kustomize --enable-helm monitor | kubectl delete -f -
kubectl kustomize --enable-helm dependencies | kubectl delete -f -
```

Create the chaos-mesh token
```
kubectl -n faults create token account-cluster-manager-jfheo
```

Get the limits for the pods in the "otel-demo" namespace
```
docker run \
    -e KUBECONFIG="/var/lib/kubernetes/kubeconfig" \
    -v "/nix/store/ychnyz3nz7dm4nlcfbickqyxjdsrhy4d-cluster-admin.pem:/nix/store/ychnyz3nz7dm4nlcfbickqyxjdsrhy4d-cluster-admin.pem:ro" \
    -v "/nix/store/6m7w6zdv3cf9d8ppc4zvi2viln8f5wcb-cluster-admin-key.pem:/nix/store/6m7w6zdv3cf9d8ppc4zvi2viln8f5wcb-cluster-admin-key.pem:ro" \
    -v "/nix/store/w3lr4z2yk92gm3bswq128rs8bn62yqf3-ca.pem:/nix/store/w3lr4z2yk92gm3bswq128rs8bn62yqf3-ca.pem:ro" \
    -v "/nix/store/4jdpgm2hcnswkrib2ff9smnva5cdg32x-cluster-admin-kubeconfig:/var/lib/kubernetes/kubeconfig:ro" \
    us-central1-docker.pkg.dev/genuine-flight-317411/devel/krr:v1.28.0 \
    python krr.py simple-limit -p http://k8s-master:30954 --namespace otel-demo --history-duration 24 --timeframe-duration 1 --width 900 --cpu_request=90 --cpu_limit=100 -q
```
