import hashlib
import json
from transaction import Transaction

class Block:
    def __init__(self, index, previous_hash, transactions, timeStamp, validator):
        if index > 0 and not previous_hash:
            raise ValueError("Previous hash cannot be empty for blocks after genesis block.")

        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timeStamp
        self.transactions = [json.dumps(tx.to_dict_with_signature()) for tx in transactions]
        self.validator = validator
        self.hash = None  # Inicializa el hash como None antes de calcularlo
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        # Copia el bloque actual para no modificar el original
        block_data = self.__dict__.copy()
        # Elimina el hash actual para no incluirlo en el nuevo cálculo del hash
        block_data.pop('hash', None)  # Remueve el hash si existe, de lo contrario no hace nada
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def __str__(self):
        # Copia el bloque actual para no modificar el original
        block_data = self.__dict__.copy()
        # Elimina el hash para la representación en cadena del bloque
        block_data.pop('hash', None)
        return str(block_data)

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,  # Si son strings JSON, déjalos como están
            "validator": self.validator,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict):
        # Asegúrate de convertir los strings JSON en instancias de Transaction
        transactions = [Transaction.from_dict(json.loads(tx_json)) for tx_json in block_dict["transactions"]]
        return cls(
            index=block_dict["index"],
            previous_hash=block_dict["previous_hash"],
            transactions=transactions,
            timeStamp=block_dict["timestamp"],
            validator=block_dict["validator"]
        )

