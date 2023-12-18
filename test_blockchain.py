import base64
from blockchain import Blockchain
from block import Block
from transaction import Transaction
from wallet import Wallet
from descentracoin import DescentraCoin


def compare_wallets(wallet1, wallet2): # Funciona
    attributes_to_compare = ['address', 'balance', 'is_stakeholder', 'staked_amount', 'is_validator', 'public_key']
    for attr in attributes_to_compare:
        val1 = wallet1[attr] if isinstance(wallet1, dict) else getattr(wallet1, attr)
        val2 = wallet2[attr] if isinstance(wallet2, dict) else getattr(wallet2, attr)

        if attr in ['balance', 'staked_amount']:
            # Asumiendo que val1 y val2 son instancias de DescentraCoin o diccionarios
            if isinstance(val1, DescentraCoin):
                val1 = val1.value
            else:
                val1 = val1['value']

            if isinstance(val2, DescentraCoin):
                val2 = val2.value
            else:
                val2 = val2['value']

            if val1 != val2:
                return False
        else:
            if val1 != val2:
                return False
    return True


def compare_transactions(transaction1, transaction2):
    attributes_to_compare = ['sender', 'recipient', 'amount', 'type', 'timestamp', 'signature']

    for attr in attributes_to_compare:
        val1 = transaction1[attr] if isinstance(transaction1, dict) else getattr(transaction1, attr)
        val2 = transaction2[attr] if isinstance(transaction2, dict) else getattr(transaction2, attr)

        if attr == 'amount':
            if isinstance(val1, DescentraCoin):
                val1 = val1.value
            else:
                val1 = val1['value']

            if isinstance(val2, DescentraCoin):
                val2 = val2.value
            else:
                val2 = val2['value']

            if val1 != val2:
                return False
        elif attr == 'signature':
            if val1 and val2:
                val1 = base64.b64decode(val1) if len(val1) % 4 == 0 else val1
                val2 = base64.b64decode(val2) if len(val2) % 4 == 0 else val2
                if val1 != val2:
                    return False
        elif val1 != val2:
            return False

    # Comparar new_Wallet si existe
    if isinstance(transaction1, dict) and 'new_Wallet' in transaction1 and isinstance(transaction2, dict) and 'new_Wallet' in transaction2:
        if not compare_wallets(transaction1['new_Wallet'], transaction2['new_Wallet']):
            return False

    return True


def compare_blocks(block1, block2):
    """
    Compara dos instancias de Block para verificar si son iguales.
    """
    # Comparar atributos simples
    attributes_to_compare = ['index', 'previous_hash', 'timestamp', 'validator', 'hash']
    for attr in attributes_to_compare:
        if getattr(block1, attr) != getattr(block2, attr):
            print(f"Diferencia encontrada en {attr}: {getattr(block1, attr)} != {getattr(block2, attr)}")
            return False

    # Comparar las transacciones como strings JSON
    if len(block1.transactions) != len(block2.transactions):
        print("El número de transacciones es diferente.")
        return False

    for tx1_json, tx2_json in zip(block1.transactions, block2.transactions):
        if tx1_json != tx2_json:
            print("Las transacciones en los bloques son diferentes.")
            return False

    return True


def compare_blockchains(chain1, chain2):
    """
    Compara dos instancias de Blockchain para verificar si son iguales.
    """
    # Comparar las transacciones pendientes, validadas e invalidadas
    for tx_list_name in ['pending_transactions', 'validated_transactions', 'invalid_transactions']:
        tx_list1 = getattr(chain1, tx_list_name)
        tx_list2 = getattr(chain2, tx_list_name)

        if len(tx_list1) != len(tx_list2):
            print(f"Diferencia en el número de {tx_list_name}.")
            return False

        for tx1, tx2 in zip(tx_list1, tx_list2):
            # Asegúrate de que tx1 y tx2 sean diccionarios
            tx1_dict = tx1 if isinstance(tx1, dict) else tx1.to_dict_with_signature()
            tx2_dict = tx2 if isinstance(tx2, dict) else tx2.to_dict_with_signature()
            if not compare_transactions(tx1_dict, tx2_dict):
                print(f"Diferencia en {tx_list_name}.")
                return False

    # Comparar wallets
    if chain1.wallets.keys() != chain2.wallets.keys():
        print("Diferencia en las direcciones de las wallets.")
        return False

    for address in chain1.wallets:
        wallet1 = chain1.wallets[address]
        wallet2 = chain2.wallets[address]
        # Asegúrate de que wallet1 y wallet2 sean diccionarios
        wallet1_dict = wallet1 if isinstance(wallet1, dict) else wallet1.to_dict()
        wallet2_dict = wallet2 if isinstance(wallet2, dict) else wallet2.to_dict()
        if not compare_wallets(wallet1_dict, wallet2_dict):
            print(f"Diferencia en la wallet con dirección {address}.")
            return False

    # Comparar stakeholders, validators y balances
    for attr in ['stakeholders', 'validators', 'balances']:
        if getattr(chain1, attr) != getattr(chain2, attr):
            print(f"Diferencia en {attr}.")
            return False

    # Comparar la cadena de bloques
    if len(chain1.chain) != len(chain2.chain):
        print("Diferencia en la longitud de la cadena de bloques.")
        return False

    for block1, block2 in zip(chain1.chain, chain2.chain):
        if not compare_blocks(block1, block2):
            print("Diferencia en los bloques de la cadena.")
            return False

    return True




# 1. Crear una blockchain
print("1. Creando blockchain...")
DescentraChain = Blockchain()
DescentraChain.print_blockchain()
DescentraChain.print_wallets()

# 2. Crear wallets
print("\n\n2. Creando wallets...")
wallet1 = Wallet(DescentraChain, 100)
wallet2 = Wallet(DescentraChain, 200)
wallet3 = Wallet(DescentraChain, 10000)

# Imprimir transacciones pendientes
print("\n\nTransacciones pendientes:")
for i in DescentraChain.pending_transactions:
    print(i.to_dict_with_signature())

# 3. Elegir un validador y validar transacciones
print("\n\n3. Elegir un validador y validar transacciones...")
validator_address = DescentraChain.choose_validator()
validator_wallet = DescentraChain.wallets.get(validator_address)
print("\nValidador elegido: ")
print(validator_wallet)

DescentraChain.validate_and_create_block(validator_wallet)


# 5. Crear nuevas transacciones
wallet3.stake(DescentraCoin(8000))
wallet3.become_validator()

'''
# Pruebas to_dict, from_dict para wallet
print("\nProbando to_dict y from_dict en Wallet...")

# Convertir wallet1 a un diccionario y luego volver a crear una wallet a partir de ese diccionario
wallet_dict = wallet1.to_dict()
recreated_wallet = Wallet.from_dict(wallet_dict, DescentraChain)

# Comparar wallet1 y recreated_wallet
print("Original Wallet:", wallet1)
print("Recreada desde diccionario:", recreated_wallet)


# Comparar wallet1 y recreated_wallet
print("Comparando wallets original y recreada...")
if compare_wallets(wallet1, recreated_wallet):
    print("Las wallets son iguales.")
else:
    print("Las wallets no son iguales.")
'''

# Crear transacciones
print("\nCreando transacciones...")
wallet1.send_transaction(wallet2.address, DescentraCoin(50))

# Imprimir transacciones pendientes
# print("\nTransacciones pendientes:")
# DescentraChain.print_pending_transactions()

'''
# Prueba dict transactions
test_transaction = DescentraChain.pending_transactions[2]
print("Transacción de prueba:", test_transaction)

dict_tran = test_transaction.to_dict_with_signature()
test_transaction2 = Transaction.from_dict(dict_tran)

# Comparando transacciones
print("Comparando transacciones...")
if compare_transactions(test_transaction, test_transaction2):
    print("Las transacciones son iguales.")
else:
    print("Las transacciones no son iguales.")

'''

# # 3. Imprimir la blockchain
# print("\n3. Blockchain después de crear wallets")
# DescentraChain.print_blockchain()

# # Imprimir transacciones pendientes
# print("\nTransacciones pendientes:")
# DescentraChain.print_pending_transactions()

# 4. Elegir un validador y validar transacciones
print("\n4. Elegir un validador y validar transacciones...")
validator_address = DescentraChain.choose_validator()
validator_wallet = DescentraChain.wallets.get(validator_address)
print("\nValidador elegido: ")
print(validator_wallet)

DescentraChain.validate_and_create_block(validator_wallet)

# Pruebas dict block
print("\nProbando to_dict y from_dict en Block...")

test_block = DescentraChain.chain[-1]
print("\nBloque de prueba:", test_block)

test_block_dict = test_block.to_dict()
test_block2 = Block.from_dict(test_block_dict)

print("\nComparando bloques...")
if compare_blocks(test_block, test_block2):
    print("Los bloques son iguales.")
else:
    print("Los bloques no son iguales.")

# 5. Imprimir la blockchain actualizada
print("\n5. Blockchain después de validar transacciones")
DescentraChain.print_blockchain()

# # 6. Wallet3 deja de ser staker y validador
# print("\n6. Wallet3 deja de ser staker y validador...")
# wallet3.unstake(DescentraCoin(8000))
# wallet3.cease_validator()

# 7. Imprimir la blockchain actualizada
print("\n7. Blockchain después de cambios en Wallet3")
DescentraChain.print_blockchain()

# 8. Elegir un validador y validar nuevas transacciones
print("\n8. Elegir un validador y validar nuevas transacciones...")
validator_address = DescentraChain.choose_validator()
validator_wallet = DescentraChain.wallets.get(validator_address)
print("\nValidador elegido: ")
print(validator_wallet)

DescentraChain.validate_and_create_block(validator_wallet)

# 9. Imprimir la blockchain actualizada
print("\n9. Blockchain después de validar nuevas transacciones")
DescentraChain.print_blockchain()

# Imprimir balances de wallets
print("\nBalances de wallets:")
DescentraChain.print_balances()

# 10. Comprobar la validez de la cadena
if DescentraChain.is_chain_valid():
    print("\n10. La blockchain es válida.")
else:
    print("\n10. La blockchain no es válida.")


print("\n11. Prueba de to_dict y from_dict en Blockchain...")
blockchain_dict = DescentraChain.to_dict()
new_blockchain = Blockchain.from_dict(blockchain_dict)

new_blockchain_dict = new_blockchain.to_dict()

print("\nComparando blockchains...")

print("\nComparando blockchains...")
if compare_blockchains(DescentraChain, new_blockchain):
    print("Las blockchains son iguales.")
else:
    print("Las blockchains no son iguales.")

# Probando get_wallet_info y update_wallet_info
print("\nProbando get_wallet_info y update_wallet_info...")

# Obtener información actual de la wallet1
original_info = DescentraChain.get_wallet_info(wallet1.address)
print(f"Información original de wallet1: {original_info}")

# Simular una actualización (puedes cambiar estos valores según lo que desees probar)
updated_info = (not original_info[0], not original_info[1], original_info[2] + 100, original_info[3] + 50)
wallet1.update_wallet_info(updated_info)

# Obtener información después de la actualización
new_info = DescentraChain.get_wallet_info(wallet1.address)
print(f"Información actualizada de wallet1: {new_info}")

# Verificar si la actualización fue exitosa
if original_info != new_info:
    print("La actualización fue exitosa.")
else:
    print("La actualización falló.")
