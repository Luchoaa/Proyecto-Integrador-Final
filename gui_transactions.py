import os
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Diccionario de node ID - node wallet address
users = {}
# Lista de acciones posibles en la wallet
wallet_actions = ['stake', 'unstake', 'become_validator', 'cease_validator', 'validate_block']

def check_nodes_connection():
    for user_id, (address, port) in users.items():
        try:
            # Asegúrate de que la URL esté correctamente formada, incluyendo http:// o https:// según sea necesario.
            url = f'http://localhost:{port}'
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Conexión con la API/nodo {user_id} exitosa.")
            else:
                print(f"No se pudo conectar con la API/nodo {user_id}. Estado: {response.status_code}")
        except Exception as e:
            print(f"Error al conectar con la API/nodo {user_id}: ", str(e))


# Función para actualizar el diccionario users, se obtiene direcciones nodos registrados en el Consul
def update_users():

    print("Actualizando nodos...")

    try:
        consul_url = 'http://localhost:8500/v1/agent/services'
        response = requests.get(consul_url)
        if response.status_code == 200:
            services = response.json()
            print("Nodos descubiertos:")
            for svc_id, svc in services.items():
                node_id = svc['ID']
                node_address = svc['Address']
                node_port = svc['Port']
                users[node_id] = (node_address, node_port)  # Actualizar el diccionario
                print(f"ID: {node_id}, Address: {node_address}, Port: {node_port}")
            # Actualizar los valores del combobox
            user_entry['values'] = list(users.keys())
        else:
            print("Error al obtener nodos: ", response.status_code)
    except Exception as e:
        print("Error al conectar con Consul: ", str(e))


def update_wallet_address():
    selected_user = user_entry.get()
    tuple = users.get(selected_user, ("", ""))
    node_wallet_address = tuple[0]
    wallet_var.set(node_wallet_address)

def handle_wallet_action():
    selected_action = wallet_action_entry.get()
    selected_user = user_entry.get()
    _, node_port = users.get(selected_user, ("", ""))

    if selected_action == 'validate_block':
        action_url = f'http://localhost:{node_port}/validate-block'
        try:
            response = requests.get(action_url)
            if response.status_code == 200:
                messagebox.showinfo("Éxito", "Bloque validado y creado si fue necesario.")
            else:
                messagebox.showerror("Error", f"Error al validar el bloque: {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Error en la solicitud: {str(e)}")
    else:
        action_url = f'http://localhost:{node_port}/wallet-action'
        data = {'action': selected_action}
        if selected_action in ['stake', 'unstake']:
            try:
                amount = float(amount_entry.get())
                data['amount'] = amount
            except ValueError:
                messagebox.showerror("Error", "Por favor, ingrese un monto válido.")
                return
        
        print(f"Realizando acción {selected_action} en el nodo {selected_user}...")
        print(f"URL: {action_url}")
        print(f"Data: {data}")

        try:
            response = requests.post(action_url, json=data)
            if response.status_code == 200:
                messagebox.showinfo("Éxito", "Acción realizada correctamente.")
            else:
                messagebox.showerror("Error", f"Error al realizar la acción: {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Error en la solicitud: {str(e)}")

def on_wallet_action_change(event=None):
    selected_action = wallet_action_entry.get()
    if selected_action == 'validate_block':
        amount_entry.config(state='disabled')
    else:
        amount_entry.config(state='normal')

# --- CONFIGURACION GUI -----------------------------------------------------------------------------

root = tk.Tk()
root.title("Wallet Manager")
root.resizable(width=False, height=False)

style = ttk.Style()
style.theme_use("clam")

# Combobox para seleccionar el usuario
user_label = ttk.Label(root, text="User:")
user_label.pack()
user_entry = ttk.Combobox(root, values=list(users.keys()), state="readonly")
user_entry.pack()
user_entry.bind("<<ComboboxSelected>>", lambda event: update_users())
user_entry.bind("<<ComboboxSelected>>", lambda event: update_wallet_address())


# Entry para mostrar la dirección de cartera
wallet_label = ttk.Label(root, text="Wallet Address:")
wallet_label.pack()
wallet_var = tk.StringVar()
wallet_entry = ttk.Entry(root, textvariable=wallet_var, state="readonly", width=70)
wallet_entry.pack()

# Combobox para seleccionar la acción de wallet
wallet_action_label = ttk.Label(root, text="Wallet Action:")
wallet_action_label.pack()
wallet_action_entry = ttk.Combobox(root, values=wallet_actions, state="readonly")
wallet_action_entry.pack()

wallet_action_entry.bind("<<ComboboxSelected>>", on_wallet_action_change)

# Entry para ingresar el monto
amount_label = ttk.Label(root, text="Amount (for stake/unstake):")
amount_label.pack()
amount_entry = ttk.Entry(root)
amount_entry.pack()

# Botón para ejecutar la acción de wallet
wallet_action_button = ttk.Button(root, text="Execute Wallet Action", command=handle_wallet_action)
wallet_action_button.pack()

check_nodes_connection()  # Verificar la conexión con los nodos
update_users()  # Actualizar el diccionario de usuarios

# Iniciar el loop principal de la aplicación
root.mainloop()