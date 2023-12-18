import logging
import hashlib
import json
import random
import time
import sys
from block import Block
from transaction import Transaction
from descentracoin import DescentraCoin
from wallet import Wallet

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

GENESIS_ADDRESS = "0" * 64  # Cadena de 64 ceros
STAKING_ADDRESS = "S" * 64  # Cadena de 64 caracteres 'S' para representar el staking
FIRST_VALIDATOR_ADDRESS = "V" * 64 # Cadena de 64 caracteres 'V' para representar el primer validador

BLOCKCHAIN_BALANCE = 1000000  # 1 millón de DSC
MIN_PENDING_TRANSACTIONS = 1  # Minimo de transacciones pendientes para crear un bloque
BLOCK_REWARD = 50 # Recompensa por crear un bloque
STAKE_REWARD = 10 # Recompensa por hacer stake
MIN_STAKE_AMOUNT = 100

class Blockchain:

    def __init__(self, existing_chain=None):
        
        # Configuración del logger
        self.logger = logging.getLogger('Blockchain')
        self.logger.setLevel(logging.INFO)

        self.pending_transactions = []  # Lista de transacciones pendientes
        self.validated_transactions = [] # Lista de transacciones validadas
        self.invalid_transactions = [] # Lista de transacciones invalidadas
        self.wallets = {}  # Diccionario de wallets
        self.stakeholders = [] # Lista de stakeholders
        self.validators = [] # Lista de validators
        self.balances = {} # Registro de los saldos y el ultimo bloque en el que una direccion estuvo involucrada

        if existing_chain:
            self.chain = existing_chain
        else:
            # La cadena de bloques se inicia con un bloque génesis
            self.chain = []
            self.create_genesis_block()

    def return_chain(self):
        return self.chain

    def create_genesis_block(self):

        # Crear una wallet genesis y agregarla al diccionario de billeteras
        genesis_wallet = Wallet(blockchain=self, balance=0, is_genesis=True)
        self.wallets[GENESIS_ADDRESS] = genesis_wallet

        # Crear una wallet staking y agregarla al diccionario de billeteras
        staking_wallet = Wallet(self, balance=0, is_staking=True)
        self.wallets[STAKING_ADDRESS] = staking_wallet

        # Crear una wallet validador y agregarla al diccionario de billeteras
        validator_wallet = Wallet(self, balance=0, is_first_validator=True)
        self.wallets[FIRST_VALIDATOR_ADDRESS] = validator_wallet

        # Crear una transacción génesis que asigna todas las monedas iniciales a una dirección
        genesis_transaction = Transaction(None, GENESIS_ADDRESS, DescentraCoin(BLOCKCHAIN_BALANCE), "Genesis transaction")
        initialize_staking_transaction = Transaction(None, STAKING_ADDRESS, DescentraCoin(1000), "Staking transaction")
        initialize_validator_transaction = Transaction(None, FIRST_VALIDATOR_ADDRESS, DescentraCoin(2000), "Validator transaction")
        
        transactions = []
        transactions.append(genesis_transaction)
        transactions.append(initialize_staking_transaction)
        transactions.append(initialize_validator_transaction)

        # Crear un bloque génesis con la transacción genesis y staking con hash previo como 0
        timeStamp = time.time()
        block = Block(0, "0", transactions, timeStamp, None)

        # Ejecutar las transacciones tras crear el bloque
        for transaction in transactions:
            self.execute_transaction(transaction)
            # Actualizar balance de las wallets
            recipient = self.wallets.get(transaction.recipient)
            recipient.set_blockchain(self)
            recipient.update_balance()

        # Retornar el bloque genesis
        self.chain.append(block)

    def get_last_block(self):
        # Obtener el último bloque en la cadena
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction):
        # Añadir una transacción a la lista de transacciones pendientes
        self.pending_transactions.append(transaction)

   # Obtiene el balance de una direccion recorriendo todos los bloques de la blockchain
    def get_balance_blockchain(self, address):
        # Calcular el saldo de una dirección en particular
        balance = DescentraCoin(0)
        for block in self.chain:
            for tx_json in block.transactions:
                # Parseamos la cadena JSON de la transacción de vuelta a un diccionario
                transaction = json.loads(tx_json)
                if transaction['sender'] == address:
                    balance -= DescentraCoin(transaction['amount'])
                if transaction['recipient'] == address:
                    balance += DescentraCoin(transaction['amount'])
        return balance
    
    def get_balance(self, address):
        # Obtenemos el balance de una direccion a partir del registro de balances
        balance_entry = self.balances.get(address, {"balance": 0, "last_block_index": 0})
        return DescentraCoin(balance_entry["balance"])

    def initialize_wallet(self, wallet_address, amount, wallet): # Inicializa una wallet con una cantidad de DSC

        genesis_wallet = self.wallets.get(GENESIS_ADDRESS)
        genesis_wallet.set_blockchain(self)
        self.logger.info(f"Diccionario wallet a anadir a la blockchain: {wallet.to_dict()}")
        return genesis_wallet.send_transaction(wallet_address, amount, type="Initialize wallet", wallet=wallet) # Se envia la cantidad de DSC a la wallet creada
         
    # Funciones para anadir o eliminar validadores y stakeholders
    def add_stakeholder(self, address):
        if address not in self.stakeholders:
            self.stakeholders.append(address)

    def remove_stakeholder(self, address):
        if address in self.stakeholders:
            self.stakeholders.remove(address)

    def add_validator(self, address):
        if address not in self.validators:
            self.validators.append(address)

    def remove_validator(self, address):
        if address in self.validators:
            self.validators.remove(address)

    # Funcion para obtener el public key de una direccion
    def get_public_key(self, address):
        wallet = self.wallets.get(address)
        wallet.set_blockchain(self)
        if wallet:
            return wallet.public_key
        else:
            # Si la dirección no corresponde a ninguna billetera, levantar una excepción
            raise ValueError("Address not found in the blockchain.")
        
    # Funcion para escoger un validador
    def choose_validator(self):
        if not self.validators:
            return FIRST_VALIDATOR_ADDRESS

        # Obtiene la cantidad apostada para cada validador
        stakes = [self.wallets[address].staked_amount.value for address in self.validators]
        total_stake_value = sum(stakes)

        if total_stake_value == 0:
            return FIRST_VALIDATOR_ADDRESS

        pick = random.uniform(0, total_stake_value)
        current = 0
        for i, address in enumerate(self.validators):
            current += stakes[i]
            if current > pick:
                return address
            
        return FIRST_VALIDATOR_ADDRESS

    # Funciones para validar y crear un bloque
    def validate_and_create_block(self, validator_wallet):
        if len(self.pending_transactions) <= MIN_PENDING_TRANSACTIONS:
            #print("Not enough valid transactions to create a block.")
            self.logger.info("Not enough valid transactions to create a block.")
            return  # Salir de la función si no hay suficientes transacciones válidas

        if not validator_wallet.is_validator:
            raise ValueError("Must be a validator to validate transactions.")

        valid_transactions = []

        for transaction in self.pending_transactions:

           if self.is_transaction_valid(transaction, validator_wallet):
                
                if isinstance(transaction, dict):
                    transaction = Transaction.from_dict(transaction)
                
                self.execute_transaction(transaction)

                self.logger.info(f"Recipient address: {transaction.recipient}")
                self.logger.info(f"Sender address: {transaction.sender}")

                sender = self.wallets.get(transaction.sender)
                sender.set_blockchain(self)
                recipient = self.wallets.get(transaction.recipient)
                recipient.set_blockchain(self)

                self.logger.info(f"Objeto recipient: {recipient}")   
                self.logger.info(f"Objeto sender: {sender}")             

                sender.update_balance()
                recipient.update_balance()
                valid_transactions.append(transaction)
        else:
            self.invalid_transactions.append(transaction) # Se anade las transacciones que no son validas a la lista de transacciones invalidas

        self.validated_transactions.extend(valid_transactions) # Se anaden las transacciones validadas a la lista de transacciones validadas

        # Crear un nuevo bloque si hay transacciones válidas
        if valid_transactions:
            last_block = self.get_last_block()
            #print(f"Creating block, validator address: {validator_wallet.address}----------------------------------------------------- ")
            self.logger.info(f"Creating block, validator address: {validator_wallet.address}")
            timeStamp = time.time()
            new_block = Block(len(self.chain), last_block.hash, valid_transactions, timeStamp, validator_wallet.address)
            self.chain.append(new_block)

            # Limpiar transacciones pendientes
            self.pending_transactions = []

            if validator_wallet.address != FIRST_VALIDATOR_ADDRESS:
                # Dar la recompensa al validador tras realizar proceso de validacion
                reward_transaction = self.reward_function(validator_wallet.address, BLOCK_REWARD)
                return reward_transaction    
        
        return 0

    def is_transaction_valid(self, transaction, validator_wallet):
        # Verificar balances
        # Convertir transaction a una instancia de Transaction si es un diccionario
        if isinstance(transaction, dict):
            transaction = Transaction.from_dict(transaction)

        sender_balance = self.get_balance(transaction.sender)
            
        if sender_balance < transaction.amount:
            self.logger.info(f"Transaction {transaction} is invalid: insufficient balance.")
            # print(f"Transaction {transaction} is invalid: insufficient balance.")
            return False

        sender_wallet = self.wallets.get(transaction.sender)
        sender_wallet.set_blockchain(self)

        if validator_wallet.address != FIRST_VALIDATOR_ADDRESS:
            # Verificar sender
            if not sender_wallet:
                self.logger.info(f"Transaction {transaction} is invalid: sender not found.")
                #print(f"Transaction {transaction} is invalid: sender not found.")
                return False

            # Verificar recipient
            if transaction.type != "Initialize wallet":
                recipient_wallet = self.wallets.get(transaction.recipient)
                recipient_wallet.set_blockchain(self)
                if not recipient_wallet:
                    self.logger.info(f"Transaction {transaction} is invalid: recipient not found.")
                    #print(f"Transaction {transaction} is invalid: recipient not found.")
                    return False
                
                # Verificar firma
                if not sender_wallet.verify_signature(transaction, transaction.signature, sender_wallet.public_key):
                    self.logger.info(f"Transaction {transaction} is invalid: invalid signature.")
                    #print(f"Transaction {transaction}, is invalid: invalid signature.")
                    return False

        # Si llega hasta aquí, la transacción es válida
        self.logger.info(f"Transaction {transaction} is valid.")
        return True

    # Funciones para ejecutar una transaccion 
    def execute_transaction(self, transaction: Transaction):

        if isinstance(transaction, dict):
            transaction = Transaction.from_dict(transaction)

        # Actualizar el saldo del remitente en el diccionario self.balances
        sender_balance_entry = self.balances.get(transaction.sender, {"balance": 0, "last_block_index": 0})
        sender_balance_entry["balance"] -= transaction.amount.value
        sender_balance_entry["last_block_index"] = len(self.chain) + 1
        self.balances[transaction.sender] = sender_balance_entry

        # Actualizar el saldo del destinatario en el diccionario self.balances
        recipient_balance_entry = self.balances.get(transaction.recipient, {"balance": 0, "last_block_index": 0})
        recipient_balance_entry["balance"] += transaction.amount.value
        recipient_balance_entry["last_block_index"] = len(self.chain) + 1
        self.balances[transaction.recipient] = recipient_balance_entry

        if transaction.type == "Staking":
            aux_wallet = self.wallets.get(transaction.sender)
            aux_wallet.set_blockchain(self)
            aux_wallet.staked_amount += transaction.amount.value

            if aux_wallet.staked_amount.value == transaction.amount.value:
                aux_wallet.is_stakeholder = True
                self.add_stakeholder(aux_wallet.address)
            else:
                self.logger.info("Staking transaction failed.")
                # print("Staking transaction failed.")

        elif transaction.type == "Unstaking":
            aux_wallet = self.wallets.get(transaction.recipient)
            aux_wallet.set_blockchain(self)
            aux_wallet.staked_amount -= transaction.amount.value
        
            if aux_wallet.staked_amount.value == 0:  # Si el monto stakeado es 0, no es más un stakeholder
                aux_wallet.is_stakeholder = False
                self.remove_stakeholder(aux_wallet.address)
        
        elif transaction.type == "Become validator":
            aux_wallet = self.wallets.get(transaction.sender)
            aux_wallet.set_blockchain(self)
            if not aux_wallet.is_stakeholder or aux_wallet.staked_amount.value < MIN_STAKE_AMOUNT:
                raise ValueError(f"Must be a stakeholder with at least {MIN_STAKE_AMOUNT} DSC staked to become a validator.".format(MIN_STAKE_AMOUNT))
            aux_wallet.is_validator = True
            self.add_validator(aux_wallet.address)

        elif transaction.type == "Cease validator":
            aux_wallet = self.wallets.get(transaction.sender)
            aux_wallet.set_blockchain(self)
            if not aux_wallet.is_validator:
                raise ValueError("Not a validator.")
            aux_wallet.is_validator = False
            self.remove_validator(aux_wallet.address)

        elif transaction.type == "Initialize wallet": 
            #print("Initializing wallet...")
            new_wallet = Wallet.from_dict(transaction.new_Wallet, blockchain=self) 
            new_wallet.blockchain = self # Al parecer no se estaba asignando bien la blockchain al momento de crear la wallet en el metodo initialize_wallet

            self.logger.info(f"Diccionario Wallets Antes: ")
            self.logger.info(f"{self.print_wallets()}")

            self.wallets[new_wallet.address] = new_wallet
            self.logger.info(f"Nueva wallet: {new_wallet}")


            self.logger.info(f"Parametro de entrada para el diccionario Wallet: {transaction.new_Wallet}")
            self.logger.info(f"\nDiccionario New_Wallet: {new_wallet.to_dict()}")

            self.logger.info(f"\n\nDiccionario Wallets Despues: ")
            self.logger.info(f"\n{self.print_wallets()}\n")
        
        elif transaction.type == "upload-IPFS": # Si la transaccion es de subida de archivo, se calcula el fee y se distribuyen las recompensas            
            self.distribute_rewards_IPFS(total_fee=transaction.amount.value)#, file_size=transaction.file_size)


    # Funciones para imprimir la blockchain, las transacciones pendientes, las wallets y los balances

    def print_pending_transactions(self):
        for transaction in self.pending_transactions:
            print(transaction)

    def print_blockchain(self):
        for block in self.chain:
            print(f"\nBlock {block.index} : {block}")

    def print_wallets(self):
        for key, wallet in self.wallets.items():
            print("Clave:", key)
            print("Objeto Wallet:", wallet.to_dict())


    def print_balances(self):
        for address, balance in self.balances.items():
            print(f"{address}: {balance}")

    def print_validated_transactions(self):
        for transaction in self.validated_transactions:
            print(transaction)

    def print_invalid_transactions(self):  
        for transaction in self.invalid_transactions:
            print(transaction)

    # Funciones para realizar el stake y unstake

    def stake_function(self, staker_address, amount):
        staker_wallet = self.wallets.get(staker_address)
        staker_wallet.set_blockchain(self)
        return staker_wallet.send_transaction(STAKING_ADDRESS, amount, type="Staking")

    def unstake_function(self, staker_address, amount):
        staking_wallet = self.wallets.get(STAKING_ADDRESS)
        staking_wallet.set_blockchain(self)
        return staking_wallet.send_transaction(staker_address, amount, type="Unstaking")
    
    # Funciones para dar recomenpensas a los validadores y stakeholders
    def reward_function(self, validator_address, amount):
        genesis_wallet = self.wallets.get(GENESIS_ADDRESS)
        genesis_wallet.set_blockchain(self)
        return genesis_wallet.send_transaction(validator_address, DescentraCoin(amount), type="Reward")

    def distribute_stakeholders_rewards(self, amount): # VER DONDE SE IMPLEMENTA EL STAKE REWARD
        for address in self.stakeholders:
            self.reward_function(address, amount)

    def is_chain_valid(self, chain=[]):
        if not chain:
            chain = self.chain
        
        for i in range(1, len(chain)): # Comenzar desde 1 ya que no podemos comparar el bloque genesis con un bloque previo
            current_block = chain[i]
            previous_block = chain[i - 1]

             # Verificar si el hash almacenado es correcto
            if current_block.hash != current_block.calculate_hash():
                print(f"Hash incorrectos ---------------------------------------")
                print(current_block.hash)
                print(current_block.__dict__)
                print(current_block.calculate_hash())

                print(f"Hash incorrecto, bloque {current_block} corrupto, hash almacenado incorrecto")
                return False

            # Verificar si el bloque apunta al hash del bloque anterior
            if current_block.previous_hash != previous_block.hash:
                print(f"Hash incorrecto, bloque {current_block} corrupto, no apunta al hash del bloque anterior")
                return False
        
        # Si llegamos hasta aquí, la cadena es válida
        return True
    
    def update_chain(self, new_chain):
        if self.is_chain_valid(new_chain):
            self.chain = new_chain
            self.recalculate_balances()
            return True
        return False
    

    def get_wallet_addresses_transactions(self, transactions_list):
        wallet_address_list = []

        for transaction in transactions_list:
            if transaction.new_Wallet is not None:
                # Comprobar si new_Wallet es un objeto Wallet o un diccionario
                if isinstance(transaction.new_Wallet, Wallet):
                    wallet_address = transaction.new_Wallet.address
                else:  # asumir que es un diccionario
                    wallet_address = transaction.new_Wallet.get('address')
                wallet_address_list.append(wallet_address)
            else:
                wallet_address_list.append(None)

        return wallet_address_list


    # Funciones para dar recompensas de almacenamiento IPFS

    def distribute_rewards_IPFS(self, total_fee):#, file_size):
        # Porcentaje para la blockchain
        blockchain_percentage = 0.1  # 10%
        blockchain_fee = total_fee * blockchain_percentage

        # Monto a distribuir entre los nodos IPFS
        ipfs_reward_pool = total_fee - blockchain_fee

        # Calcular el espacio total aportado por los nodos IPFS
        total_node_space = sum(wallet.space if wallet.space is not None else 0 for address, wallet in self.wallets.items() if address not in [GENESIS_ADDRESS, STAKING_ADDRESS, FIRST_VALIDATOR_ADDRESS])


        # Calcular y distribuir recompensas para cada nodo
        for address, wallet in self.wallets.items():

            genesis_wallet = self.wallets.get(GENESIS_ADDRESS)
            genesis_wallet.set_blockchain(self)

            if address not in [GENESIS_ADDRESS, STAKING_ADDRESS, FIRST_VALIDATOR_ADDRESS]:
                reward = self.calculate_node_reward(ipfs_reward_pool, total_node_space, wallet.space)
                genesis_wallet.send_transaction(address, DescentraCoin(reward), type="reward-IPFS")



    def calculate_node_reward(self, reward_pool, total_node_space, node_space):
        # Verificar que el espacio total de los nodos no sea cero para evitar división por cero
        if total_node_space > 0:
            # Calcular la recompensa proporcional al espacio aportado
            reward = (node_space / total_node_space) * reward_pool
            return reward
        else:
            return 0  # Si no hay espacio total, no se puede calcular la recompensa


    # Serialize and deserialize blockchain

    def to_dict(self):
        return{
            "wallets": {address: wallet.to_dict() for address, wallet in self.wallets.items()},
            "stakeholders": self.stakeholders,
            "validators": self.validators,
            "balances": self.balances,
            "pending_addresses": self.get_wallet_addresses_transactions(self.pending_transactions),
            "validated_addresses": self.get_wallet_addresses_transactions(self.validated_transactions),
            "invalid_addresses": self.get_wallet_addresses_transactions(self.invalid_transactions),
            "pending_transactions": [tx.to_dict_with_signature() for tx in self.pending_transactions],
            "validated_transactions": [tx.to_dict_with_signature() for tx in self.validated_transactions],
            "invalid_transactions": [tx.to_dict_with_signature() for tx in self.invalid_transactions],
            "chain": [block.to_dict() for block in self.chain]
        }
    
    @staticmethod
    def from_dict(data):
        # Crear una instancia nueva de Blockchain
        blockchain = Blockchain(existing_chain=None)
   
        # Deserializar y reconstruir las wallets
        blockchain.wallets = {
        address: Wallet.from_dict(wallet_dict, blockchain) for address, wallet_dict in data["wallets"].items()
        }
        # Asignar stakeholders, validators y balances directamente
        blockchain.stakeholders = data["stakeholders"]
        blockchain.validators = data["validators"]
        blockchain.balances = data["balances"]

        #Obtener las direcciones de las wallets de las transacciones antes de obtener las transacciones
        pending_addresses = data["pending_addresses"]
        validated_addresses = data["validated_addresses"]
        invalid_addresses = data["invalid_addresses"]

        # Pending transactions
        # Verificar si las longitudes de las listas de direcciones y transacciones coinciden
        if len(pending_addresses) != len(data["pending_transactions"]):
            raise ValueError("Las listas de direcciones y transacciones pendientes no coinciden en longitud.")

        # Deserializar y reconstruir las transacciones pendientes
        blockchain.pending_transactions = []
        for i, tx_dict in enumerate(data["pending_transactions"]):
            address = pending_addresses[i]
            wallet = blockchain.wallets.get(address)
            transaction = Transaction.from_dict(tx_dict, wallet)
            blockchain.pending_transactions.append(transaction)

        # Validated transactions
        # Verificar si las longitudes de las listas de direcciones y transacciones coinciden
        if len(validated_addresses) != len(data["validated_transactions"]):
            raise ValueError("Las listas de direcciones y transacciones validadas no coinciden en longitud.")
        
        # Deserializar y reconstruir las transacciones validadas
        blockchain.validated_transactions = []
        for i, tx_dict in enumerate(data["validated_transactions"]):
            address = validated_addresses[i]
            wallet = blockchain.wallets.get(address)
            transaction = Transaction.from_dict(tx_dict, wallet)
            blockchain.validated_transactions.append(transaction)

        # Invalid transactions
        # Verificar si las longitudes de las listas de direcciones y transacciones coinciden
        if len(invalid_addresses) != len(data["invalid_transactions"]):
            raise ValueError("Las listas de direcciones y transacciones invalidadas no coinciden en longitud.")
        
        # Deserializar y reconstruir las transacciones invalidadas
        blockchain.invalid_transactions = []
        for i, tx_dict in enumerate(data["invalid_transactions"]):
            address = invalid_addresses[i]
            wallet = blockchain.wallets.get(address)
            transaction = Transaction.from_dict(tx_dict, wallet)
            blockchain.invalid_transactions.append(transaction)

        # Deserializar y reconstruir la cadena de bloques
        blockchain.chain = [
            Block.from_dict(block_dict) for block_dict in data["chain"]
        ]

        return blockchain
    

    def get_wallet_info(self, address):
        """
        Retorna una tupla con información detallada de una wallet específica.
        La tupla contiene: (is_validator, is_stakeholder, balance, staked_amount).
        """
        wallet = self.wallets.get(address)
        wallet.set_blockchain(self)

        if not wallet:
            raise ValueError("Wallet not found in the blockchain.")

        is_validator = wallet.is_validator
        is_stakeholder = wallet.is_stakeholder
        balance = wallet.balance.value  # o simplemente wallet.balance para obtener el objeto DescentraCoin
        staked_amount = wallet.staked_amount.value  # o simplemente wallet.staked_amount

        return (is_validator, is_stakeholder, balance, staked_amount)