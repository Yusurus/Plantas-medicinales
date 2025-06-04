from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import mysql.connector
import os
import requests
import cv2
import base64
import numpy as np
from PIL import Image
import io
from deepface import DeepFace

app = Flask(__name__)
CORS(app)


# --- Configuration for Plant App ---
"""def get_connection():
    return mysql.connector.connect(
        host='bdyuri.cpikeig8qwsl.us-east-1.rds.amazonaws.com',
        user='admin',
        password='23072208aaA',
        database='bdplantas'
    )"""
def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='12admin34',
        database='bdplantas'
    )

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
PLANTAS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'imgs', 'plantas')
IDENTIFY_UPLOAD_FOLDER = 'subidas'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PLANTAS_FOLDER, exist_ok=True)
os.makedirs(IDENTIFY_UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  
app.config['PLANTAS_FOLDER'] = PLANTAS_FOLDER  
app.config['IDENTIFY_UPLOAD_FOLDER'] = IDENTIFY_UPLOAD_FOLDER 

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

API_KEY = '2b10Q1pjh95QnKNGhW1eXZLO'
API_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={API_KEY}&lang=es&include-related-images=true"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Configuration for Face Recognition App ---
DIRECTORIO_ROSTROS = "rostros_conocidos"
USUARIOS_MOCK = {
    'admin': 'password123',
    'usuario': '12345',
    'test': 'test'
}

def verificar_base_datos_rostros():
    """Verifica que la base de datos de rostros existe"""
    if not os.path.isdir(DIRECTORIO_ROSTROS):
        print(f"Error: El directorio '{DIRECTORIO_ROSTROS}' no existe.")
        return False
    print(f"Base de datos de rostros lista: {DIRECTORIO_ROSTROS}")
    return True

def procesar_imagen_base64(imagen_base64):
    """Convierte imagen base64 a formato OpenCV"""
    try:
        # Remover el prefijo data:image/jpeg;base64,
        if ',' in imagen_base64:
            imagen_base64 = imagen_base64.split(',')[1]
        
        # Decodificar base64
        imagen_bytes = base64.b64decode(imagen_base64)
        imagen_pil = Image.open(io.BytesIO(imagen_bytes))
        
        # Convertir a array numpy para OpenCV
        imagen_np = np.array(imagen_pil)
        
        # Convertir RGB a BGR (OpenCV usa BGR)
        if len(imagen_np.shape) == 3:
            imagen_cv = cv2.cvtColor(imagen_np, cv2.COLOR_RGB2BGR)
        else:
            imagen_cv = imagen_np
            
        return imagen_cv
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        return None

# --- Routes from Face Recognition App (Primary Entry) ---
@app.route('/')
def index():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.idPlantas, 
                p.nombreCientifico, 
                p.linkimagen,
                GROUP_CONCAT(n.nombreComun SEPARATOR ', ') AS nombres_comunes
            FROM 
                plantas p
            LEFT JOIN 
                nombres_comunes n ON p.idPlantas = n.fk_Plantas
            GROUP BY 
                p.idPlantas, p.nombreCientifico, p.linkimagen
        """)
        rows = cursor.fetchall()
        resultado = []
        for r in rows:
            resultado.append({
                'idPlantas': r[0],
                'nombreCientifico': r[1],
                'linkimagen': r[2],
                'nombres_comunes': r[3] if r[3] else ''
            })
        return render_template('visualizar_plantas.html', plantas=resultado)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/login')
def login():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login_tradicional():
    """Endpoint para login tradicional"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username in USUARIOS_MOCK and USUARIOS_MOCK[username] == password:
            return jsonify({
                'success': True,
                'message': f'Bienvenido, {username}!',
                'user': username
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Usuario o contraseña incorrectos'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error del servidor: {str(e)}'
        })

@app.route('/api/verify-face', methods=['POST'])
def verificar_rostro():
    """Endpoint para verificación facial"""
    try:
        data = request.get_json()
        imagen_base64 = data.get('image')
        
        if not imagen_base64:
            return jsonify({
                'success': False,
                'message': 'No se recibió imagen'
            })
        
        # Procesar imagen
        imagen_cv = procesar_imagen_base64(imagen_base64)
        if imagen_cv is None:
            return jsonify({
                'success': False,
                'message': 'Error procesando la imagen'
            })
        
        # Detectar rostros primero
        detector_rostros = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        gray = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
        rostros_detectados = detector_rostros.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        if len(rostros_detectados) == 0:
            return jsonify({
                'success': False,
                'message': 'No se detectó ningún rostro en la imagen'
            })
        
        # Usar DeepFace para reconocimiento
        try:
            resultados_df = DeepFace.find(
                img_path=imagen_cv,
                db_path=DIRECTORIO_ROSTROS,
                model_name="VGG-Face",
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=True
            )
            
            if len(resultados_df) > 0 and not resultados_df[0].empty:
                # Rostro reconocido
                ruta_identidad = resultados_df[0].iloc[0]['identity']
                nombre_usuario = os.path.basename(os.path.dirname(ruta_identidad))
                distancia = resultados_df[0].iloc[0]['distance']
                
                return jsonify({
                    'success': True,
                    'message': f'¡Bienvenido, {nombre_usuario}!',
                    'user': nombre_usuario,
                    'confidence': round((1 - distancia) * 100, 2)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Rostro no reconocido'
                })
                
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': 'No se pudo procesar el rostro'
            })
        except Exception as e:
            print(f"Error con DeepFace: {e}")
            return jsonify({
                'success': False,
                'message': 'Error en el reconocimiento facial'
            })
            
    except Exception as e:
        print(f"Error general: {e}")
        return jsonify({
            'success': False,
            'message': f'Error del servidor: {str(e)}'
        })

# --- Routes from Plant App ---
@app.route('/admin') # Renamed from '/' to avoid conflict
def home():
    return render_template('registro_planta.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    data = request.get_json()
    nombre = data.get('nombre')
    correo = data.get('correo')

    if not nombre or not correo:
        return jsonify({'error': 'Nombre y correo son requeridos'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nombre, correo) VALUES (%s, %s)", (nombre, correo))
        conn.commit()
        return jsonify({'mensaje': 'Usuario registrado'})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/usuarios')
def usuarios():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, correo FROM usuarios")
        rows = cursor.fetchall()
        return jsonify([{'nombre': r[0], 'correo': r[1]} for r in rows])
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

'''
@app.route('/plantas', methods=['GET'])
def plantas():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.idPlantas, 
                p.nombreCientifico, 
                p.linkimagen,
                GROUP_CONCAT(n.nombreComun SEPARATOR ', ') AS nombres_comunes
            FROM 
                plantas p
            LEFT JOIN 
                nombres_comunes n ON p.idPlantas = n.fk_Plantas
            GROUP BY 
                p.idPlantas, p.nombreCientifico, p.linkimagen
        """)
        rows = cursor.fetchall()
        resultado = []
        for r in rows:
            resultado.append({
                'idPlantas': r[0],
                'nombreCientifico': r[1],
                'linkimagen': r[2],
                'nombres_comunes': r[3] if r[3] else ''
            })
        return render_template('visualizar_plantas.html', plantas=resultado)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()
'''
@app.route('/registrar_planta', methods=['GET', 'POST'])
def registrar_planta():
    familias = []
    mensaje = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nomFamilia FROM familiasplantas")
        familias = [row['nomFamilia'] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()
    
    if request.method == 'POST':
        nombreCientifico = request.form['nombreCientifico']
        nomFamilia = request.form['nomFamilia']
        nombresComunes = request.form['nombresComunes']
        imagen = request.files['imagen']

        if imagen and imagen.filename.endswith('.jpg'):
            nombre_cientifico_sanitized = secure_filename(nombreCientifico).lower()
            nombre_archivo = nombre_cientifico_sanitized + ".jpg"
            ruta = os.path.join(app.config['PLANTAS_FOLDER'], nombre_archivo)
            imagen.save(ruta)

            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.callproc('gestionar_plantas', [1, None, nombreCientifico, nombre_archivo, nomFamilia, nombresComunes])
                for result in cursor.stored_results():
                    mensaje = result.fetchall()[0]['respuesta']
                conn.commit()
            except Exception as e:
                mensaje = f'Error en el servidor: {str(e)}'
            finally:
                cursor.close()
                conn.close()

    return render_template('registro_plantas.html', mensaje=mensaje, familias=familias)

@app.route('/iden')
def iden_home():
    return render_template('iden.html')

@app.route('/identify', methods=['POST'])
def identify():
    if 'image' not in request.files:
        return jsonify({'error': 'No se proporcionó imagen'}), 400
    file = request.files['image']

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Archivo no válido'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['IDENTIFY_UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, 'rb') as img:
        files = {'images': img}
        data = {'organs': request.form.get('organ', 'leaf')}

        try:
            response = requests.post(API_URL, files=files, data=data)
            response.raise_for_status()
            result = response.json()

            if not result["results"]:
                return jsonify({'message': 'No se encontraron coincidencias'})

            top = result["results"][0]
            species = top["species"]
            images = top.get("images", [])

            image_urls = []
            for i, img_data in enumerate(images[:1]):
                url = img_data.get("url")
                if url:
                    specific_url = url.get("m") 
                    if specific_url:
                        image_urls.append(specific_url)

            return jsonify({
                'identifiedOrgan': images[0].get("organ") if images else 'Desconocido',
                'scientificName': species.get("scientificNameWithoutAuthor", "Desconocido"),
                'authorship': species.get("scientificNameAuthorship", ""),
                'commonNames': species.get("commonNames", []),
                'genus': species.get("genus", {}).get("scientificNameWithoutAuthor", ""),
                'family': species.get("family", {}).get("scientificNameWithoutAuthor", ""),
                'score': round(top.get("score", 0) * 100, 2),
                'imageUrls': image_urls
            })

        except requests.RequestException as e:
            return jsonify({'message': f'Error al comunicarse con la API de PlantNet: {str(e)}'}), 500

if __name__ == '__main__':
    if verificar_base_datos_rostros():
        print("Iniciando servidor Flask...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("No se puede iniciar el servidor sin la base de datos de rostros.")