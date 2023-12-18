import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils # elliptic curve cryptography
from cryptography.exceptions import InvalidSignature
from descentracoin import DescentraCoin
from transaction import Transaction

MIN_STAKE_AMOUNT = 1000 # Stake minimo para ser validador
GENESIS_ADDRESS = "0" * 64  # Cadena de 64 ceros
STAKING_ADDRESS = "S" * 64  # Cadena de 64 caracteres 'S' para representar el staking
FIRST_VALIDATOR_ADDRESS = "V" * 64 # Cadena de 64 caracteres 'V' para representar el primer validador
BECOME_CEASE_VALIDATOR_COMISSION = 1 # Comision de transaccion para aplicar a validador y dejar de ser validador

INITIAL_REWARD = 0.1 # Recompensa inicial por crear una wallet
RATE_PER_MB = 0.1 # Tarifa por MB para subir archivos a IPFS


class Wallet:

    def __init__(self, blockchain=None, balance=INITIAL_REWARD, is_stakeholder=False, staked_amount=0, is_validator=False, is_genesis=False, is_staking=False, is_first_validator=False, empty=False, space=100, files_name_hash_list=[]): 
        
        # is_genesis, is_stacking, is_first_validator son billeteras especiales de la blockchain
        if empty == False:
            self.private_key = ec.generate_private_key(ec.SECP256R1())  
            self.public_key = self.private_key.public_key()  
            
            if is_genesis:
                self.address = GENESIS_ADDRESS
            elif is_staking:
                self.address = STAKING_ADDRESS
            elif is_first_validator:
                self.address = FIRST_VALIDATOR_ADDRESS
                is_validator = True

            else:
                self.address = self.generate_address(self.public_key)
            
            self.blockchain = blockchain
            self.balance = DescentraCoin(0) # Inicializa en 0, por que el balance se agrega tras realizar la funcion de inicializacion de la blockchain
            self.is_stakeholder = is_stakeholder
            self.staked_amount = DescentraCoin(0)
            self.is_validator = is_validator
            self.initialize_transaction_dict = None
            self.space = space # Space es el espacio de almacenamiento que tiene la wallet en megabytes -> IPFS
            self.files_name_hash_list = files_name_hash_list # Lista de hashes de los nombres de los archivos que tiene la wallet en IPFS

            # if blockchain and balance > 0 and not is_genesis:
            if not is_genesis and not is_staking and not is_first_validator:
                print(f"En el constructor, el balance es: {balance}")
                self.initialize_transaction_dict = self.blockchain.initialize_wallet(self.address, DescentraCoin(balance), self)

                if is_stakeholder:
                    self.stake(DescentraCoin(staked_amount))
                
                if is_validator:
                    self.become_validator()
            
            elif is_genesis or is_staking or is_first_validator:
                self.blockchain.wallets[self.address] = self
                
        elif empty: # Si tiene el atributo empty en True, se crea una wallet vacia sin llamar a ninguna funcion de la blockchain
            self.address = None
            self.blockchain = None
            self.balance = None
            self.is_stakeholder = None
            self.staked_amount = None
            self.is_validator = None
            self.initialize_transaction_dict = None
            self.space = None
            self.files_name_hash_list = None

   
    # Wallet methods--------------------------------------------------------------

    def add_file_name_hash(self, file_name, hash):
        self.files_name_hash_list.append((file_name, hash))

    # Serializa la clave pública a bytes, la funcion toma la clave publica, la codifica en un formato legible  
    # y transportable (PEM) y estructura la clave pública de acuerdo con el estándar SubjectPublicKeyInfo,
    def generate_address(self, public_key):
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM, # PEM y SubjectPublicKeyInfo son los formatos mas comunes
            format=serialization.PublicFormat.SubjectPublicKeyInfo 
        )
        # Calcula el hash SHA-256
        sha256_hash = hashlib.sha256(public_key_bytes).hexdigest()
        return sha256_hash

    def update_balance_blockchain(self):
        # Metodo para actualizar el saldo de la cartera basado en la blockchain
        self.balance = self.blockchain.get_balance_blockchain(self.address)

    def update_balance(self):
        # Metodo para actualizar el saldo de la cartera basado diccionario balances
        self.balance = self.blockchain.get_balance(self.address)

    
    def create_transaction(self, recipient, amount, type="regular", wallet=None, file_size=None):
        # Metodo para crear una nueva transacción
        transaction = Transaction(self.address, recipient, amount, type, wallet, file_size)
        return transaction
    
    # Metodo para firmar una transaccion
    def sign_transaction(self, transaction):
    
        transaction_bytes = str(transaction.to_dict()).encode('utf-8') # Serializa la transacción a una representación en bytes    
        # Calcula el hash SHA-256 de los datos de la transacción
        transaction_hash = hashlib.sha256(transaction_bytes).digest()
        
        # Firma el hash de la transacción con la clave privada
        signature = self.private_key.sign(
            transaction_hash,
            ec.ECDSA(hashes.SHA256())  # ECDSA (Elliptic Curve Digital Signature Algorithm) 
        )
        return signature
    
    # Método para enviar una transaccion, crea,firma y la agrega a las transacciones pendientes de blockchain
    def send_transaction(self, recipient_address, amount, type="regular", wallet=None, file_size=None):
        # Crear y firmar en un solo paso
        if wallet != None:
            wallet = wallet.to_dict() # En vez de almacenar el objeto, almacenamos el diccionario de la wallet

        transaction = self.create_transaction(recipient_address, amount, type, wallet)
        transaction.signature = self.sign_transaction(transaction)
        
        # Añadir a transacciones pendientes en la blockchain
        self.blockchain.add_transaction(transaction)
        return transaction.to_dict_with_signature()

    # Método para verificar la firma de una transacción
    def verify_signature(self, transaction, signature, public_key):
        # Comprobación de la validez de la clave pública
        if not self.is_valid_public_key(public_key):
            print("Clave pública inválida.")
            return False

        # Serializa la transacción a una representación en bytes,
        transaction_bytes = str(transaction.to_dict()).encode('utf-8')
        
        # Calcula el hash SHA-256 de los datos de la transacción
        transaction_hash = hashlib.sha256(transaction_bytes).digest()

        try:
            # Verifica la firma usando la clave pública
            public_key.verify(
                signature,  # La firma de la transacción
                transaction_hash,  # El hash de la transacción
                ec.ECDSA(hashes.SHA256())
            )
            #print("La firma es válida.")
            return True
        except InvalidSignature:
            #print("La firma es inválida.")
            return False
        
    def is_valid_public_key(self, public_key):
        # Comprueba si la clave pública es un objeto de tipo clave pública EC
        return isinstance(public_key, ec.EllipticCurvePublicKey)
        

    # IPFS methods---------------------------------------------------------------------

    def upload_file(self, file_size, recipient_address=GENESIS_ADDRESS):
        print(file_size)
        amount = self.calculate_transaction_fee_IPFS(file_size)
        #def send_transaction(self, recipient_address, amount, type="regular", wallet=None, file_size=None):
        return self.send_transaction(recipient_address, DescentraCoin(amount=amount), type="upload-IPFS", file_size=file_size)


    def download_file(self, recipient_address=GENESIS_ADDRESS):
        return self.send_transaction(recipient_address, DescentraCoin(amount=10), type="download-IPFS")


    def calculate_transaction_fee_IPFS(self, file_size):
        # Convertir bytes a megabytes
        size_in_mb = file_size / (1024 * 1024)
        amount = size_in_mb * RATE_PER_MB       # Calcular la tarifa total
        return amount

    # Stakeholder methods--------------------------------------------------------------

    def stake(self, amount: DescentraCoin):

        if amount.value <= 0:
            print("Invalid staking amount. It should be greater than zero.")
            return 
        return self.blockchain.stake_function(self.address, amount)
  
    def unstake(self, amount: DescentraCoin):
        if amount.value <= 0:
            print("Invalid unstaking amount. It should be greater than zero.")
            return
        return self.blockchain.unstake_function(self.address, amount)

    # Validator methods--------------------------------------------------------------

    def become_validator(self):
        return self.send_transaction(GENESIS_ADDRESS, DescentraCoin(BECOME_CEASE_VALIDATOR_COMISSION), "Become validator")

    def cease_validator(self):
        return self.send_transaction(GENESIS_ADDRESS, DescentraCoin(BECOME_CEASE_VALIDATOR_COMISSION), "Cease validator")

    def __str__(self):
        return f"\nWallet Address: \n{self.address}, Balance: {self.balance}"
    
    
    def to_dict(self):
        """
        Convierte la instancia de Wallet en un diccionario.
        """
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Asegúrate de que la clave privada esté presente antes de intentar serializarla
        private_key_bytes = None
        if self.private_key:
            private_key_bytes = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        
        return {
            "address": self.address,
            "balance": self.balance.to_dict(),
            "staked_amount": self.staked_amount.to_dict(),
            "is_stakeholder": self.is_stakeholder,
            "is_validator": self.is_validator,
            "private_key": private_key_bytes.decode('utf-8') if private_key_bytes else None,
            "public_key": public_key_bytes.decode('utf-8'),
            "space": self.space,
            "files_name_hash_list": self.files_name_hash_list
        }
    
    @staticmethod
    def from_dict(wallet_dict, blockchain):
        # Crear una instancia de Wallet sin inicializar balance y staked_amount
        wallet = Wallet(blockchain=blockchain, empty=True)

        # Asignar valores a partir del diccionario
        wallet.address = wallet_dict["address"]
        wallet.is_stakeholder = wallet_dict["is_stakeholder"]
        wallet.balance = DescentraCoin.from_dict(wallet_dict["balance"])
        wallet.staked_amount = DescentraCoin.from_dict(wallet_dict["staked_amount"])
        wallet.is_validator = wallet_dict["is_validator"]
        wallet.space = wallet_dict.get("space")  # Añadir asignación de space
        wallet.files_name_hash_list = wallet_dict.get("files_name_hash_list", [])  # Añadir asignación de files_name_hash_list con un valor predeterminado en caso de que no exista

        # Cargar la clave pública desde la representación string en formato PEM
        wallet.public_key = serialization.load_pem_public_key(
            wallet_dict["public_key"].encode('utf-8')
        )

        # Cargar la clave privada si está presente
        if wallet_dict.get("private_key"):
            wallet.private_key = serialization.load_pem_private_key(
                wallet_dict["private_key"].encode('utf-8'),
                password=None
            )

        return wallet
    
    def update_wallet_info(self, wallet_info):
        if isinstance(wallet_info, tuple):
            self.is_validator, self.is_stakeholder, balance_value, staked_amount_value = wallet_info
            self.balance = DescentraCoin(balance_value)
            self.staked_amount = DescentraCoin(staked_amount_value)
        elif isinstance(wallet_info, dict):
            self.is_validator = wallet_info.get("is_validator", self.is_validator)
            self.is_stakeholder = wallet_info.get("is_stakeholder", self.is_stakeholder)
            #self.files_name_hash_list = wallet_info.get("files_name_hash_list", [])  
            self.space = wallet_info.get("space", 100)  

            balance_value = wallet_info.get("balance", self.balance.value)
            staked_amount_value = wallet_info.get("staked_amount", self.staked_amount.value)
            self.balance = DescentraCoin(balance_value)
            self.staked_amount = DescentraCoin(staked_amount_value)
        else:
            raise ValueError("Invalid wallet info format. Expected a tuple or a dictionary.")

    def set_blockchain(self, blockchain):
        self.blockchain = blockchain