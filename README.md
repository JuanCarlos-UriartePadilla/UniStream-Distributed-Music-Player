# UniStream-Distributed-Music-Player
Reproductor de música distribuido usando Python Flask, NFS y APIs de YouTube/Spotify

# Características
* **Backend:** Python Flask + Google Cloud APIs.
* **Frontend:** HTML + CSS + YouTube Player API.
* **Seguridad:** Encriptación de datos de usuario con Cryptography.
* **Almacenamiento:** Sistema de archivos distribuido (NFS).

# Instalación
1. Clona el repositorio.
2. Instala dependencias: `pip install flask flask_cors spotipy google-api-python-client cryptography`
4. Agrega tus API Keys en `api_server.py`.
5. Ejecuta: `python api_server.py`
