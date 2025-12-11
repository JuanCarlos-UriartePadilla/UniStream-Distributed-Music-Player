# UniStream-Distributed-Music-Player
Reproductor de música distribuido usando Python Flask, NFS y APIs de YouTube/Spotify

# Características
* **Backend:** Python Flask + Google Cloud APIs.
* **Frontend:** HTML5 + CSS3 + YouTube Player API.
* **Seguridad:** Encriptación de datos de usuario con Cryptography.
* **Almacenamiento:** Sistema de archivos distribuido (NFS).

# Instalación
1. Clona el repo.
2. Instala dependencias: `pip install flask flask_cors spotipy google-api-python-client cryptography`
3. Agrega tus API Keys en `api_server.py`.
4. Ejecuta: `python api_server.py`
