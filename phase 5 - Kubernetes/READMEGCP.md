# Payment Service - Instruções de Deployment (GCP)

## Arquitetura e Armazenamento (Cloud Native)

Ao contrário de uma abordagem de "Lift & Shift" com volumes persistentes, o **Payment Service** foi migrado para uma arquitetura 100% gerida e *Cloud Native*. 

O serviço consome os dados diretamente do **Google BigQuery**, o Data Warehouse da Google.
* **Vantagens:** Não requer a criação de PersistentVolumeClaims (PVCs), não precisa de bases de dados locais a correr no cluster (PostgreSQL) e não exige a injeção manual de dados via ficheiros `.csv` ou scripts de `seed.py`.
* **Padrão Utilizado:** Seguindo as boas práticas de microserviços sugeridas (Phase 6), utilizámos o padrão *Database per Service*.

## Como Fazer o Deployment no GKE

Como o serviço não tem dependências de armazenamento local, o deployment é direto e não requer upload prévio de ficheiros para o Cloud Shell.

### 1 - Criar o cluster
Ação que pode demorar 3-5 minutos:
```bash
gcloud container clusters create-auto urbanpulse-cluster --region europe-west4
```

### 2 - Ligar kubectl ao cluster

```bash
gcloud container clusters get-credentials urbanpulse-cluster --region europe-west4
```

### 3 - O Namespace
Garantir que o namespace partilhado da equipa está criado:

```bash
kubectl create namespace urbanpulse
```

### 4 - Autenticação no Docker Hub (Obrigatório)

Como a imagem do Payment Service está num repositório privado para garantir a segurança das credenciais GCP (Google Cloud), é necessário criar o Secret de leitura no cluster antes de aplicar os manifestos:

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=pedrorosa3 \
  --docker-password=***REMOVED*** \
  --docker-email=pedromjrosa333@gmail.com \
  -n urbanpulse
```

### 5 - Aplicar os YAMLs
Aplicar o manifesto do Payment Service (que já inclui o Deployment, o Service, o HPA e o Ingress):

```bash
kubectl apply -f payment-k8s.yaml
```

### 6 - Verificar os pods
Esperar que o pod inicie e passe para o estado Running, ação que pode demorar entre 2-4 minutos:

```bash
kubectl get pods -n urbanpulse
```
ou para ver em tempo real:

```bash
kubectl get pods -n urbanpulse -w
```
Quando quiseres sair deste visualizador em tempo real faz CTRL+C


### 7 - Descobrir o ingress

```bash
kubectl get ingress -n urbanpulse
```



Para correr e testar:

Coloca no browser:

http://IP-dado-pelo-ingress

http://IP-dado-pelo-ingress/docs


Para ver os logs:

```bash
kubectl logs -l app=payment-service -n urbanpulse -f
```

Para apagar o cluster, fazendo com que o GCP não cobre créditos por consumo:

```bash
gcloud container clusters delete urbanpulse-cluster --region europe-west4 --quiet
```





Acesso Seguro à Imagem DockerPara evitar conflitos de permissões entre contas GCP individuais da equipa (Artifact Registry), a imagem do Payment Service está alojada de forma segura no Docker Hub.O ficheiro payment-k8s.yaml já está configurado para puxar a imagem pública pedrorosa3/payment-service:v5.Portas e ProtocolosNesta iteração da arquitetura, o serviço de pagamentos comunica exclusivamente via REST HTTP, não expondo endpoints gRPC.
