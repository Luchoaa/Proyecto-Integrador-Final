import json
import logging
import os
import subprocess
import time
import requests
from flask import Flask, request, jsonify, send_file
from threading import Thread
from wallet import Wallet, Transaction, DescentraCoin
from blockchain import Blockchain

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)


# Variables de entorno
CLUSTER_API_URL = "http://localhost:9094"
REGISTRY_FOLDER = 'registry'
REGISTRO_JSON = os.path.join(REGISTRY_FOLDER, 'registro_archivos.json')
MIN_PENDING_TRANSACTIONS = 3

class Node:
    # Initialization and Network Setup
    def __init__(self):
        # Configuración del logger
        self.logger = logging.getLogger('Node')
        self.logger.setLevel(logging.INFO)

        # Basic node configuration
        self.id = os.environ.get("NODE_ID")
        self.port = os.environ.get("NODE_PORT")
        self.app = Flask(__name__)

        self.descentrachain = Blockchain()

        self.wallet = Wallet(self.descentrachain, 10000)
        self.wallet_address = self.wallet.address

        self.wallet.files_name_hash_list = self.cargar_registros_desde_json() # Cargar registros desde el archivo JSON

        # Network configuration and Consul registration
        self.setup_routes()
        self.register_with_consul()
        time.sleep(5)

        self.node_addresses = self.discover_nodes()
        self.logger.info(f"Node addresses: {self.node_addresses}")

# Funciones almacenar registro IPFS ------------------------------------------------   

    # Cargar registros desde el archivo JSON si existe
    def cargar_registros_desde_json(self):
        if os.path.exists(REGISTRO_JSON):
            with open(REGISTRO_JSON, 'r') as archivo:
                return json.load(archivo)
        else:
            return []

    def guardar_registro(self, data):
        registro_tupla = (data.get('sender_address'), data.get('filename'), data.get('hash'))
        self.wallet.files_name_hash_list.append(registro_tupla)
        self.guardar_registros_en_json()

    def guardar_registros_en_json(self):
        if not os.path.exists(REGISTRY_FOLDER):
            os.makedirs(REGISTRY_FOLDER)
        else:
            with open(REGISTRO_JSON, 'w') as archivo:
                json.dump(self.wallet.files_name_hash_list, archivo)


# --------------------------------------------------------------------------------
    # Consul Registration and Node Discovery
    def register_with_consul(self):
        consul_url = 'http://consul:8500/v1/agent/service/register'
        service = {"Name": self.id, "Port": int(self.port), "Address": self.wallet_address}
        requests.put(consul_url, json=service)
        self.logger.info(f"Registered service with Consul: {service}")

    def discover_nodes(self):
        consul_url = 'http://consul:8500/v1/agent/services'
        response = requests.get(consul_url)
        services = response.json()

        node_addresses = []
        for svc_id, svc in services.items():
            if svc_id.startswith("node") and svc_id != self.id:
                node_info = {
                    "id": svc_id, 
                    "port": svc["Port"],
                    "address": svc["Address"]
                }
                node_addresses.append(node_info)
        self.logger.info(f"Discovered node addresses: {node_addresses}")
        return node_addresses

# --------------------------------------------------------------------------------
    # Método separado para ejecutar Flask en un hilo
    def run_flask_app(self):
        self.logger.info("Iniciando el servidor Flask en un hilo separado...")
        self.app.run(host="0.0.0.0", port=6000)

    # Método modificado 'run' para usar un hilo
    def run(self):
        self.logger.info("Iniciando el nodo...")
        # Iniciar Flask en un hilo separado
        flask_thread = Thread(target=self.run_flask_app)
        flask_thread.start()

        # Esperar a que Flask se inicie completamente
        self.logger.info("Esperando a que el servidor Flask se inicie...")
        time.sleep(10)  # Ajustar este tiempo según sea necesario

        # Luego de la espera, realizar la transacción inicial
        self.logger.info("Verificando si realizar broadcast o proceso de validacion...")

        if len(self.descentrachain.pending_transactions) >= MIN_PENDING_TRANSACTIONS:
            self.logger.info(f"Pending transactions are full.")
            self.validate_and_create_block_if_needed()
        else:
            self.broadcast_transaction(self.wallet.initialize_transaction_dict)

# --------------------------------------------------------------------------------

    # Flask Routes Setup for Node Communication
    def setup_routes(self):


        # Validar y crear bloque si es necesario
        @self.app.route('/validate-block', methods=['GET'])
        def validate_block():
            self.validate_and_create_block_if_needed()
            return jsonify({"status": "ok"}), 200
        

        # Realizar distintas acciones en la wallet, stake, unstake, become_validator, cease_validator
        @self.app.route('/wallet-action', methods=['POST'])
        def wallet_action():
            data = request.json
            action = data.get('action')
            amount = data.get('amount', 0)

            # Log the received action
            self.logger.info(f"Received wallet action: {action}")

            if action == 'stake':
                transaction_dict = self.wallet.stake(DescentraCoin(amount))
            elif action == 'unstake':
                transaction_dict = self.wallet.unstake(DescentraCoin(amount))
            elif action == 'become_validator':
                transaction_dict = self.wallet.become_validator()
            elif action == 'cease_validator':
                transaction_dict = self.wallet.cease_validator()
            else:
                return jsonify({"status": "Unrecognized action"}), 400
            
            transaction = Transaction.from_dict(transaction_dict)
            self.descentrachain.add_transaction(transaction)

            # Check if the pending transactions queue is full
            if len(self.descentrachain.pending_transactions) >= MIN_PENDING_TRANSACTIONS:
               self.logger.info(f"Pending transactions are full.")
               self.validate_and_create_block_if_needed()
            else:
                # If not full, broadcast the transaction
                self.broadcast_transaction(transaction_dict)

            response = {
                "status": "Action completed and transaction broadcasted",
                "transaction_info": transaction_dict
            }

            return jsonify(response), 200


        # Recibir transaccion
        @self.app.route('/transaction', methods=['POST'])
        def receive_transaction():
            transaction_dict = request.json
            self.process_received_transaction(transaction_dict)

            self.logger.info(f"Processed transaction: {transaction_dict}")

            response = {
                "status": "Transaction received and processed",
                "transaction_info": transaction_dict
            }
            return jsonify(response), 200
        

        # Actualizar blockchain tras validacion
        @self.app.route('/update_blockchain', methods=['POST'])
        def update_blockchain():
            self.descentrachain.pending_transactions = [] # Reset pending transactions 
            data = request.json

            blockchain_data = data.get("blockchain")
            target_node_data = data.get("target_node")

            self.logger.info(f"Received blockchain update: {blockchain_data}")
            # Crear una nueva instancia de Blockchain a partir del diccionario recibido
            nueva_blockchain = Blockchain.from_dict(blockchain_data)
            self.logger.info(f"New blockchain type: {type(nueva_blockchain)} ------------------")

            # Actualizar la instancia actual con la nueva instancia creada
            self.descentrachain = nueva_blockchain
            self.logger.info(f"Blockchain actualizada: {self.descentrachain.to_dict()}")
            self.logger.info(f"Blockchain actualizada type: {type(self.descentrachain)} ------------------")

            # Crear una nueva instancia de Wallet a partir del diccionario recibido
            new_Wallet = Wallet.from_dict(target_node_data, self.descentrachain)
            self.logger.info(f"New wallet type: {type(new_Wallet)} ------------------")
            self.wallet.blockchain = self.descentrachain # Actualizar blockchain de la wallet

            # Actualizar la instancia actual con la nueva instancia creada
            self.wallet = new_Wallet
            self.logger.info(f"Wallet actualizada: {self.wallet.to_dict()}")
            self.wallet.set_blockchain(self.descentrachain)
            self.logger.info(f"Blockchain de la wallet actualizada type: {type(self.wallet.blockchain)} ------------------")


            # wallet_info = self.descentrachain.get_wallet_info(self.wallet_address)
            # self.logger.info(f"Wallet info: {wallet_info}")
            # self.wallet.update_wallet_info(wallet_info) # Update wallet info after blockchain update
            # Definir títulos intermedios
            # wallets_title = "Wallets de la blockchain tras validar"
            # validated_transactions_title = "Transacciones validadas"
            # invalid_transactions_title = "Transacciones no validadas"

            # # Construir el mensaje de registro
            # log_message = (
            #     "\n\n"
            #     f"{wallets_title}: {self.descentrachain.print_wallets()}\n"
            #     f"{validated_transactions_title}: {self.descentrachain.print_validated_transactions()}\n"
            #     f"{invalid_transactions_title}: {self.descentrachain.print_invalid_transactions()}\n\n"
            # )

            # # Registra el mensaje
            # self.logger.info(log_message)
            return jsonify({"status": "Blockchain updated"}), 200

        # Endpoints IPFS / IPFS Cluster --------------------------------------------

        # Mensaje inicio de la API / Node
        @self.app.route('/')
        def home():
            return jsonify({"message": "API/Node Running"}), 200
        

        @self.app.route('/upload', methods=['POST'])
        def upload_file():
            self.logger.info("Received file upload request")
            if 'file' not in request.files:
                return jsonify({"error": "No file part"}), 400

            file = request.files['file']
            sender_address = request.form.get('sender_address')
            file_size_mb = request.form.get('file_size_mb')
            file_size_mb = float(file_size_mb)

            if file.filename == '':
                return jsonify({"error": "No selected file"}), 400

            # Guardar temporalmente el archivo
            temp_path = os.path.join("temp_files", file.filename)
            if not os.path.exists("temp_files"):
                os.makedirs("temp_files")
            file.save(temp_path)

            if not os.path.exists(temp_path):
                return jsonify({"error": "Error saving file"}), 500
            else:
                self.logger.info(f"File saved to {temp_path}")

            try:

                add_url = f'http://cluster1:9094/add'

                # Enviar el archivo al Cluster 1 a través de una solicitud HTTP POST
                response = requests.post(f"{add_url}", files={"file": (file.filename, open(temp_path, 'rb'))})

                if response.status_code == 200:
                    # La solicitud fue exitosa, puedes obtener el resultado si es necesario
                    result = response.json()
                    file_hash = result.get("cid", None)
                    print(f"File hash (cid): {file_hash}")
                else:
                    # La solicitud falló, maneja el error según sea necesario
                    print("Error al agregar el archivo:", response.status_code, response.text)
                    file_hash = None

            except Exception as e:
                return jsonify({"error": f"Error uploading to IPFS: {str(e)}"}), 500
            finally:
                # Limpiar el archivo temporal
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            if file_hash:
                self.guardar_registro({'sender_address': sender_address, 'filename': file.filename, 'hash': file_hash})


            # Implementar generar transaccion, anadirla a transacciones pendientes y realizar broadcast de transaccion

            self.logger.info(f"File size: {file_size_mb}")
            #Utilizar file_size para crear transaction de upload IPFS
            upload_file_transaction = self.wallet.upload_file(file_size=file_size_mb)
            self.descentrachain.add_transaction(upload_file_transaction)  #, ya se agrega en el metodo upload_file
            
            self.logger.info(f"Pending transactions: {len(self.descentrachain.pending_transactions)} / {MIN_PENDING_TRANSACTIONS}")
            if len(self.descentrachain.pending_transactions) >= MIN_PENDING_TRANSACTIONS:
                
                self.logger.info(f"Pending transactions are full.")
                self.validate_and_create_block_if_needed()
            else:
                self.broadcast_transaction(upload_file_transaction)


            return jsonify({"hash": file_hash, "filename": file.filename, "sender_address": sender_address})
        
        
        # Descargar archivo desde IPFS
        @self.app.route('/retrieve/<cid>/<filename>', methods=['GET'])
        def retrieve_file(cid, filename):

            try:
                # Reemplaza 'ipfs1' con el nombre del servicio IPFS en tu docker-compose.yml, si es diferente.
                ipfs_gateway_url = f'http://ipfs1:8080/ipfs/{cid}'

                # Realizar la solicitud para descargar el archivo desde el gateway IPFS
                response = requests.get(ipfs_gateway_url, stream=True)

                if response.status_code == 200:
                    print(f"Downloading file: {filename}")
                    file_path = os.path.join("downloaded_files", filename)
                    if not os.path.exists("downloaded_files"):
                        os.makedirs("downloaded_files")

                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    retrieve_file_transaction = self.wallet.download_file()
                    
                    self.descentrachain.add_transaction(retrieve_file_transaction)#, ya se agrega en el metodo download_file
            
                    if len(self.descentrachain.pending_transactions) >= MIN_PENDING_TRANSACTIONS:
                        self.logger.info(f"Pending transactions are full.")
                        self.validate_and_create_block_if_needed()
                    else:
                        self.broadcast_transaction(retrieve_file_transaction)

                    return send_file(file_path, as_attachment=True)
                
                else:
                    print(f"Error downloading file: {response.text}, {response.status_code}")
                    return jsonify({"error": "File not found or error in IPFS gateway"}), response.status_code
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            

        # Obtener archivos de un usuario
        @self.app.route('/files', methods=['GET'])
        def get_files():
            try:
                # Obtener todos los archivos, ya que no se filtra por 'address'
                archivos_usuario = self.wallet.files_name_hash_list
                return jsonify(archivos_usuario)
            except Exception as e:
                self.logger.error(f"Error al obtener archivos: {e}")
                return jsonify({"error": str(e)}), 500
            
        


# --------------------------------------------------------------------------------

# Other Functions

    # Send Blockchain Update to a Specific Node
    def send_blockchain_to_node(self, target_node, blockchain_dict):
        url = f"http://{target_node['id']}:6000/update_blockchain"
        self.logger.info(f"Sending blockchain update to {url}")

        target_node_wallet = self.descentrachain.wallets.get(target_node['address'])
        target_node_dict = Wallet.to_dict(target_node_wallet)

        data_to_send = {
        "blockchain": blockchain_dict,
        "target_node": target_node_dict
        }

        try:
            response = requests.post(url, json=data_to_send)
            response_json = response.json()
            self.logger.info(f"Blockchain update sent from {self.id} to {target_node['id']}: {response_json}")
        except Exception as e:
            self.logger.error(f"Error sending blockchain update from {self.id} to {target_node['id']}: {e}")

    # Send Transaction to a Specific Node (remain unchanged)
    def send_transaction_to_node(self, target_node, transaction_dict):
        url = f"http://{target_node['id']}:6000/transaction"
        self.logger.info(f"Sending transaction to {url}")
        try:
            response = requests.post(url, json=transaction_dict)
            response_json = response.json()
            self.logger.info(f"Transaction sent from {self.id} to {target_node['id']}: {response_json}")
        except Exception as e:
            self.logger.error(f"Error sending transaction from {self.id} to {target_node['id']}: {e}")

    # Process Received Transaction
    def process_received_transaction(self, transaction_dict):
        #self.logger.info(f"\nProcessing received transaction dict: {transaction_dict}")
        transaction = Transaction.from_dict(transaction_dict)
        #self.logger.info(f"\nProcessing received transaction: {transaction}")
        # Add transaction to pending list or other processing
        self.descentrachain.add_transaction(transaction)

        # # Check if the pending transactions queue is full
        # if len(self.descentrachain.pending_transactions) >= 5:
        #     self.logger.info(f"Pending transactions are full.")
        #     self.validate_and_create_block_if_needed()

        #self.logger.info(f"\nTransacciones pendientes tras anadir transaccion: {len(self.descentrachain.pending_transactions)}\n")
        #self.logger.info(f"\n\nDiccionario de wallets tras recibir transaccion: {self.descentrachain.print_wallets()}\n\n")

    def validate_and_create_block_if_needed(self):
        validator_address = self.descentrachain.choose_validator()
        validator_wallet = self.descentrachain.wallets.get(validator_address)
        self.logger.info(f"Validating and creating block with validator {validator_wallet.address}")
        reward_transaction = self.descentrachain.validate_and_create_block(validator_wallet)
        #self.logger.info(f"Wallets de la blockchain tras validar: {self.descentrachain.print_wallets()}\nTransacciones validadas: {self.descentrachain.print_validated_transactions()}\nTransacciones no validadas: {self.descentrachain.print_invalid_transactions()}")
        self.broadcast_blockchain()

        if reward_transaction != 0:
            self.broadcast_transaction(reward_transaction)

# --------------------------------------------------------------------------------

# Broadcasting Functions

    # Broadcast Blockchain to All Known Nodes
    def broadcast_blockchain(self):
        self.logger.info("Broadcasting blockchain...")
        blockchain_dict = self.descentrachain.to_dict()
        self.logger.info(f"\nBlockchain dict, broadcasting blockchain from node:{self.id}:\n{blockchain_dict}\n")
        for peer in self.node_addresses:
            self.send_blockchain_to_node(peer, blockchain_dict)
        self.logger.info("Blockchain broadcasted.")

    # Broadcast Transaction to All Known Nodes (remain unchanged)
    def broadcast_transaction(self, transaction_dict):
        for peer in self.node_addresses:
            self.send_transaction_to_node(peer, transaction_dict)

    

if __name__ == "__main__":
    node = Node()
    node.run()
