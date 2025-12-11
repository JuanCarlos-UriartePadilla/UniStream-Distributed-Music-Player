from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import datetime
import json
import os

# Librerias de APIs externas
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from secure_storage import SecureStorage

app = Flask(__name__)
CORS(app)

# --------------------------------claves de api--------------------------------
SPOTIFY_CLIENT_ID = '6f892d7154054c2a819871f713d532df'
SPOTIFY_CLIENT_SECRET = '625be9de16194c829771e0ad4ffd49e1'
YOUTUBE_API_KEY = 'AIzaSyCmt2upKbYCJlmYZ_M0hcEFOPtLiteOkbU'
GOOGLE_CLIENT_ID = "118135224266-mfedhskg49toj900algmn1qlop3nf619.apps.googleusercontent.com"
# ------------------------------------------------------------------------------

# --- INICIALIZACION ---
db = SecureStorage()

# Iniciar Spotify
try:
    sp_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
    sp = spotipy.Spotify(client_credentials_manager=sp_manager)
    print("[INIT] Spotify conectado.")
except Exception as e:
    print(f"[ERROR] Fallo Spotify: {e}")

# Iniciar YouTube
try:
    yt = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    print("[INIT] YouTube conectado.")
except Exception as e:
    print(f"[ERROR] Fallo YouTube: {e}")

# --- HELPERS ---
def log_sistema(mensaje, nivel="INFO"):
    """Guarda logs tecnicos en logs_sistema.json"""
    entry = { "timestamp": str(datetime.datetime.now()), "nivel": nivel, "mensaje": mensaje }
    try:
        logs = db.read_table("logs_sistema")
        if not isinstance(logs, list): logs = []
        logs.append(entry)
        db.save_table("logs_sistema", logs)
    except: pass

def buscar_en_youtube(query):
    try:
        request = yt.search().list(q=query, part='id,snippet', maxResults=1, type='video')
        response = request.execute()
        if 'items' in response and len(response['items']) > 0:
            video = response['items'][0]
            return {
                "video_id": video['id']['videoId'],
                "video_title": video['snippet']['title'],
                "video_url": f"https://www.youtube.com/watch?v={video['id']['videoId']}",
                "thumbnail": video['snippet']['thumbnails']['default']['url']
            }
        return None
    except Exception as e:
        print(f"Error YouTube: {e}")
        return None

# --- ENDPOINTS ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search_song():
    try:
        query = request.args.get('q')
        log_sistema(f"Busqueda: {query}", "AUDITORIA")
        if not query: return jsonify({"error": "Falta q"}), 400

        print(f"\n[BUSQUEDA] {query}")
        
        # Spotify
        sp_results = sp.search(q=query, limit=1, type='track')
        items = sp_results['tracks']['items']
        
        if len(items) > 0:
            track = items[0]
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            
            resultado = {
                "source": "Spotify+YouTube",
                "id": track['id'],
                "name": track_name,
                "artist": artist_name,
                "album": track['album']['name'],
                "image": track['album']['images'][0]['url'],
                "preview_url": track['preview_url']
            }
            
            # YouTube
            yt_data = buscar_en_youtube(f"{track_name} {artist_name} Official Video")
            if yt_data: resultado["youtube"] = yt_data
            
            # Historial
            log = {"accion": "BUSQUEDA", "termino": query, "encontrado": track_name, "timestamp": str(datetime.datetime.now())}
            hist = db.read_table("historial_busquedas")
            if not isinstance(hist, list): hist = []
            hist.append(log)
            db.save_table("historial_busquedas", hist)
            
            return jsonify(resultado), 200
        else:
            return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        print(f"ERROR SERVER: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def google_login():
    token = request.json.get('token')
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        user_data = {
            "google_id": idinfo['sub'], "nombre": idinfo['name'], 
            "email": idinfo['email'], "foto": idinfo['picture'], 
            "ultimo_acceso": str(datetime.datetime.now())
        }
        
        usuarios = db.read_table("usuarios")
        if not isinstance(usuarios, list): usuarios = []
        
        existe = False
        for u in usuarios:
            if u['google_id'] == user_data['google_id']:
                u.update(user_data)
                existe = True
                break
        if not existe: usuarios.append(user_data)
        
        db.save_table("usuarios", usuarios)
        return jsonify({"status": "success", "user": user_data}), 200
    except Exception as e:
        print(f"ERROR LOGIN: {e}")
        return jsonify({"error": str(e)}), 500

# --- PLAYLISTS (Crear, Leer, Borrar) ---
@app.route('/api/playlists', methods=['POST', 'GET', 'DELETE'])
def manejar_playlists():
    try:
        playlists = db.read_table("playlists")
        if not isinstance(playlists, list): playlists = []

        # GET
        if request.method == 'GET':
            email = request.args.get('usuario')
            modo = request.args.get('modo')
            if modo == 'comunidad':
                otras = [p for p in playlists if p.get('usuario') != email]
                return jsonify(otras), 200
            else:
                mias = [p for p in playlists if p.get('usuario') == email]
                return jsonify(mias), 200

        # POST
        if request.method == 'POST':
            data = request.json
            data['creada_en'] = str(datetime.datetime.now())
            for p in playlists:
                if p.get('nombre') == data['nombre'] and p.get('usuario') == data['usuario']:
                    return jsonify({"status": "error", "msg": "Ya existe esa lista"}), 200
            playlists.append(data)
            db.save_table("playlists", playlists)
            return jsonify({"status": "success", "msg": "Playlist creada"}), 200

        # DELETE
        if request.method == 'DELETE':
            nombre = request.args.get('nombre')
            usuario = request.args.get('usuario')
            # Borrar lista
            playlists = [p for p in playlists if not (p.get('nombre') == nombre and p.get('usuario') == usuario)]
            db.save_table("playlists", playlists)
            # Limpiar canciones huerfanas
            items = db.read_table("playlist_items")
            if isinstance(items, list):
                items = [i for i in items if not (i.get('playlist_nombre') == nombre and i.get('usuario') == usuario)]
                db.save_table("playlist_items", items)
            return jsonify({"status": "success", "msg": "Playlist eliminada"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ITEMS PLAYLIST (Agregar, Leer, Borrar Cancion) ---
@app.route('/api/playlist/items', methods=['POST', 'GET', 'DELETE'])
def manejar_items_playlist():
    try:
        tabla = "playlist_items" 
        items = db.read_table(tabla)
        if not isinstance(items, list): items = []

        # POST
        if request.method == 'POST':
            data = request.json
            for i in items:
                if i.get('cancion_id') == data['cancion_id'] and i.get('playlist_nombre') == data['playlist_nombre'] and i.get('usuario') == data['usuario']:
                    return jsonify({"status": "warn", "msg": "Ya está en la lista"}), 200
            items.append(data)
            db.save_table(tabla, items)
            return jsonify({"status": "success", "msg": "Agregada"}), 200

        # GET
        if request.method == 'GET':
            nombre_lista = request.args.get('nombre_lista')
            usuario = request.args.get('usuario')
            resultado = [i for i in items if i.get('playlist_nombre') == nombre_lista and i.get('usuario') == usuario]
            return jsonify(resultado), 200
            
        # DELETE
        if request.method == 'DELETE':
            cancion_id = request.args.get('cancion_id')
            nombre_lista = request.args.get('nombre_lista')
            usuario = request.args.get('usuario')
            items = [i for i in items if not (i.get('cancion_id') == cancion_id and i.get('playlist_nombre') == nombre_lista and i.get('usuario') == usuario)]
            db.save_table(tabla, items)
            return jsonify({"status": "success", "msg": "Eliminada de lista"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- FAVORITOS ---
@app.route('/api/favoritos', methods=['POST', 'GET', 'DELETE'])
def manejar_favoritos():
    try:
        usuario = request.args.get('usuario') or request.json.get('usuario')
        favs = db.read_table("favoritos")
        if not isinstance(favs, list): favs = []

        if request.method == 'GET':
            mis_favs = [f for f in favs if f.get('usuario') == usuario]
            return jsonify(mis_favs), 200

        if request.method == 'POST':
            data = request.json
            for f in favs:
                if f.get('cancion_id') == data['cancion_id'] and f.get('usuario') == data['usuario']:
                    return jsonify({"status": "warn", "msg": "Ya existe"}), 200
            favs.append(data)
            db.save_table("favoritos", favs)
            return jsonify({"status": "success", "msg": "Guardado"}), 200

        if request.method == 'DELETE':
            cancion_id = request.args.get('cancion_id')
            favs = [f for f in favs if not (f.get('cancion_id') == cancion_id and f.get('usuario') == usuario)]
            db.save_table("favoritos", favs)
            return jsonify({"status": "success", "msg": "Eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
def guardar_config():
    try:
        data = request.json
        configs = db.read_table("configuracion")
        if not isinstance(configs, list): configs = []
        configs.append(data)
        db.save_table("configuracion", configs)
        return jsonify({"status": "success", "msg": "Guardado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
