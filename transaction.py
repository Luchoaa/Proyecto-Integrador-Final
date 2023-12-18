from descentracoin import DescentraCoin
import time
import base64

# GLOBAL_FEE = 1 # Tarifa global por transaccion

class Transaction:
    def __init__(self, sender, recipient, amount, type, new_wallet=None, timestamp=None, signature=None, file_size=None): #, fee=GLOBAL_FEE):
        if amount.value <= 0:
            raise ValueError("Invalid transaction amount. It should be greater than zero.")
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        # self.fee = DescentraCoin(fee)
        self.signature = signature
        self.type = type
        
        if timestamp is not None:
            self.timestamp = timestamp
        else:
            self.timestamp =  time.time()

        self.new_Wallet = new_wallet # Para el caso de creacion de wallets, necesitamos enviar la wallet para anadirla al registro de wallets de la blockchain
                                    # Es el diccionario de la wallet

        self.file_size = file_size # Para el caso de subida de archivos, necesitamos enviar el tamano del archivo para calcular el fee y las recompensas de los demas nodos

    def sign(self, signature):
            self.signature = signature

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount.to_dict(),
            "type": self.type,
            "timestamp": self.timestamp
        }
    
    def to_dict_with_signature(self):
        transaction_dict = self.to_dict()
        # Codificar la firma en Base64 para convertirla en una cadena
        if self.signature:
            transaction_dict["signature"] = base64.b64encode(self.signature).decode('utf-8')
        else:
            transaction_dict["signature"] = None

        if self.new_Wallet is not None and type(self.new_Wallet) is not dict:
            transaction_dict["new_wallet"] = self.new_Wallet.to_dict()
            
        elif self.new_Wallet is not None and type(self.new_Wallet) is dict:
            transaction_dict["new_wallet"] = self.new_Wallet 
        else:
            transaction_dict["new_wallet"] = None

        if self.file_size is not None:
            transaction_dict["file_size"] = self.file_size
        else:
            transaction_dict["file_size"] = None

        return transaction_dict

    @classmethod
    def from_dict(cls, transaction_dict, wallet=None):

         # Decodificar la firma de Base64 si está presente
        signature = transaction_dict.get("signature")
        if signature:
            signature = base64.b64decode(signature)

        if wallet is None:
            wallet = transaction_dict["new_wallet"]

        # Inicializar la transacción con los campos requeridos
        transaction = cls(
            sender=transaction_dict["sender"],
            recipient=transaction_dict["recipient"],
            amount=DescentraCoin.from_dict(transaction_dict["amount"]),
            type=transaction_dict["type"],
            timestamp=transaction_dict["timestamp"],
            signature=signature,
            new_wallet=wallet,
            file_size=transaction_dict["file_size"]
        )

        return transaction
    
    def __str__(self):
        return f"From: {self.sender}, To: {self.recipient}, Amount: {self.amount.value},\nSignature: {self.signature}, Type: {self.type}" 






