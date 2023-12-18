FROM python:3.11.5
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "./new_node.py"]

# FROM python:3.11.5

# # Instalar wget y unzip
# RUN apt-get update && apt-get install -y wget unzip

# # Descargar y descomprimir ipfs-cluster-ctl
# RUN wget https://dist.ipfs.tech/ipfs-cluster-ctl/v1.0.7/ipfs-cluster-ctl_v1.0.7_windows-amd64.zip \
#     && unzip ipfs-cluster-ctl_v1.0.7_windows-amd64.zip -d ipfs-cluster-ctl \
#     && mv ipfs-cluster-ctl/ipfs-cluster-ctl /usr/local/bin/ \
#     && chmod +x /usr/local/bin/ipfs-cluster-ctl \
#     && rm -rf ipfs-cluster-ctl_v1.0.7_windows-amd64.zip ipfs-cluster-ctl

# WORKDIR /app
# COPY . /app
# RUN pip install -r requirements.txt
# CMD ["python", "./new_node.py"]
