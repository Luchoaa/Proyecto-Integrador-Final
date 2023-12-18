import os
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Diccionario de node ID - node wallet address
users = {}

# --- DEFINICION DE FUNCIONES ---------------------------------------------------------------------

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


# Funcion para actualizar la tabla de archivos subidos
def update_uploaded_files_treeview(files_info):
    print("Actualizando archivos subidos...")
    treeview.delete(*treeview.get_children())
    for file in files_info:
        treeview.insert('', tk.END, values=(file["filename"], file["hash"], file["sender_address"]))


# Funcion para actualizar el campo de la dirección de la cartera
def update_wallet_address():

    print("Actualizando dirección de cartera...")

    selected_user = user_entry.get()
    tuple = users.get(selected_user, ("", ""))
    node_wallet_address = tuple[0]
    node_port = tuple[1]
    wallet_var.set(node_wallet_address)

    try:
        response = requests.get(f'http://localhost:{node_port}/files')
        if response.status_code == 200:
            files_info = response.json()
            print("Respuesta de la API: ", files_info)
            # Transformar la respuesta a una lista de diccionarios
            files_info_list = []
            for file_info in files_info:
                # Aquí asumimos que la estructura de cada elemento en la lista es ['hash', 'filename', 'sender_address']
                file_dict = {
                    "sender_address": file_info[0],
                    "filename": file_info[1],
                    "hash": file_info[2]
                }
                files_info_list.append(file_dict)

            print("Archivos obtenidos exitosamente: ", files_info_list)
            update_uploaded_files_treeview(files_info_list)
        else:
            print("Error al obtener archivos: ", response.text)
    except Exception as e:
        print("Error en la solicitud: ", str(e))


# Funcion para subir un archivo, se comunica con la API del nodo seleccionado
def upload_file():
    print("Subiendo archivo...")
    file_path = filedialog.askopenfilename()
    if file_path:
        # Obtener el nombre del archivo
        filename = file_path.split("/")[-1]

        # Verificar si el archivo ya ha sido subido
        for uploaded_file in uploaded_files:
            if uploaded_file['filename'] == filename:
                messagebox.showinfo("Archivo ya subido", "Este archivo ya ha sido subido anteriormente.")
                return
            
        # Obtener el tamaño del archivo en MB
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        with open(file_path, 'rb') as file:
            files = {'file': file}
            sender_address = wallet_var.get()

            # Obtener la dirección y el puerto del nodo seleccionado
            selected_user = user_entry.get()
            _, node_port = users.get(selected_user, ("", "")) # Devuelve una tupla, (address, port)
            
            # Construir la URL de la API usando la dirección y el puerto
            api_url = f'http://localhost:{node_port}/upload'
            print(api_url)

            response = requests.post(api_url, files=files, data={'sender_address': sender_address, 'file_size_mb': file_size_mb})
            if response.status_code == 200:
                response_json = response.json()
                uploaded_files.append(response_json)
                print("Archivo cargado exitosamente: ", response_json)
                print(f"Archivos subidos: {uploaded_files}")
                update_uploaded_files_treeview(uploaded_files)
                messagebox.showinfo("Éxito", "Archivo cargado exitosamente.")
            else:
                messagebox.showerror("Error", f"Error al subir archivo: {response.text}")
                print("Error al subir archivo: ", response.text)

# Funcion para recuperar un archivo, se comunica con la API del nodo seleccionado
def retrieve_file():
    selected = treeview.focus()  # Obtiene el elemento seleccionado en la tabla
    if not selected:
        messagebox.showinfo("Seleccionar archivo", "Por favor, selecciona un archivo de la lista.")
        return
    print(f"Recuperando archivo... {selected}")

    # Obtener información del archivo seleccionado
    selected_file_info = treeview.item(selected, 'values')
    filename = selected_file_info[0]
    hash_cid = selected_file_info[1]

    print(f"Archivo seleccionado: {filename}, CID: {hash_cid}")

    # Obtener el puerto del nodo seleccionado
    selected_user = user_entry.get()
    _, node_port = users.get(selected_user, ("", ""))
    if not node_port:
        messagebox.showerror("Error", "No se encontró el puerto del nodo seleccionado.")
        return

    # URL del nodo para la solicitud de recuperación
    node_url = f"http://localhost:{node_port}/retrieve/{hash_cid}/{filename}"
    print(node_url)

    try:
        # Realizar la solicitud al nodo
        response = requests.get(node_url, stream=True)

        if response.status_code == 200:
            save_path = filedialog.asksaveasfilename(defaultextension=".*", initialfile=filename)
            if save_path:
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)

                messagebox.showinfo("Éxito", f"Archivo {filename} descargado con éxito.")
            else:
                messagebox.showinfo("Cancelado", "Descarga cancelada por el usuario.")
        else:
            messagebox.showerror("Error", f"Error al descargar el archivo: {response.text}")

    except Exception as e:
        messagebox.showerror("Error", f"Se produjo un error: {str(e)}")


# --- CONFIGURACION GUI-----------------------------------------------------------------------------
# Configuración de la ventana principal
root = tk.Tk()
root.title("IPFS File Manager")
root.resizable(width=False, height=False)


style = ttk.Style()
style.theme_use("clam")

# Crear campo para seleccionar el usuario
user_label = ttk.Label(root, text="User:")
user_label.pack()
user_entry = ttk.Combobox(root, values=list(users.keys()), state="readonly")
user_entry.pack()

# Vincular el evento de selección del combobox con la función de actualización
user_entry.bind("<<ComboboxSelected>>", lambda event: update_users())
user_entry.bind("<<ComboboxSelected>>", lambda event: update_wallet_address())

# Campo de entrada para mostrar la dirección de cartera
wallet_label = ttk.Label(root, text="Wallet Address:")
wallet_label.pack()
wallet_var = tk.StringVar()
wallet_entry = ttk.Entry(root, textvariable=wallet_var, state="readonly", width=70) 
wallet_entry.pack()


# Botones y contenedor
frame = ttk.Frame(root)
frame.pack(padx=10, pady=10)

upload_button = ttk.Button(frame, text="Upload File", command=upload_file)
upload_button.pack(side=tk.LEFT, padx=5, pady=5)

retrieve_button = ttk.Button(frame, text="Retrieve File", command=retrieve_file)
retrieve_button.pack(side=tk.RIGHT, padx=5, pady=5)

# Tabla para mostrar archivos subidos

uploaded_files = [] # Lista de archivos subidos

# Tabla para mostrar archivos subidos
columns = ("Filename", "Hash", "User")
treeview = ttk.Treeview(root, columns=columns, show="headings")
treeview.heading("Filename", text="Filename")
treeview.heading("Hash", text="Hash") 
treeview.heading("User", text="User") 
treeview.column("Filename", minwidth=100, width=200, stretch=tk.NO)
treeview.column("Hash", minwidth=100, width=250, stretch=tk.NO)
treeview.column("User", minwidth=100, width=100, stretch=tk.NO) 
treeview.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)



check_nodes_connection()  # Verificar la conexión con los nodos
update_users()  # Actualizar el diccionario de usuarios

# Iniciar el loop principal de la aplicación
root.mainloop()
