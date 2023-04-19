#!/bin/bash

### Definire parametrii primiti la intrare
declare jenkins_addr=${jenkins_addr:-127.0.0.1}
declare gitea_addr=${gitea_addr:-127.0.0.1}
declare artifactory_addr=${artifactory_addr:-127.0.0.1}

### Parsare parametrii
while [ $# -gt 0 ]; do
    if [[ $1 == *"--"* ]]; then
        param="${1/--/}"
        declare $param="$2"
    fi
    shift
done

sed "s/\${jenkins_addr}/${jenkins_addr}/" ./resources/nginx/nginx.conf
sed "s/\${gitea_addr}/${gitea_addr}/" ./resources/nginx/nginx.conf
sed "s/\${artifactory_addr}/${artifactory_addr}/" ./resources/nginx/nginx.conf


mkdir -p ./resources/nginx/certs


cat <<EOF > ./resources/nginx/certs/dot.local.cfg
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = req_distinguished_name
x509_extensions = v3_req
[req_distinguished_name]
C = RO
ST = Bucharest
L = Bucharest
O = dot.local
OU = IT
CN = dot.local
[v3_req]
keyUsage = digitalSignature, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = dot.local
EOF

openssl req -new -nodes -x509 -days 3650 -newkey rsa:4096 \
        -keyout ./resources/nginx/certs/dot.local.key -out ./resources/nginx/certs/dot.local.crt \
        -config ./resources/nginx/certs/dot.local.cfg -extensions v3_req

docker-compose -f "$(dirname $0)/docker-compose.yaml" up -d