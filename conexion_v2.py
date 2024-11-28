from flask import Flask, request, jsonify
import uuid
import psycopg2
from datetime import datetime

app = Flask(__name__)

# Dominio base del acortador
BASE_URL = "http://goshort.ly/"

# Configuración de conexión a la base de datos
def get_db_connection():
    #database_url = "postgresql://postgres:IgtzJLbHpqJPoimAEYCVTqkDtQFFPqEz@autorack.proxy.rlwy.net:39767/railway"
    database_url = "postgresql://postgres:IgtzJLbHpqJPoimAEYCVTqkDtQFFPqEz@autorack.proxy.rlwy.net:39767/goshort"
    connection = psycopg2.connect(database_url)
    return connection

# Generar un identificador único para la URL
def generate_short_link():
    return uuid.uuid4().hex[:6]

@app.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    original_url = data.get('original_url')
    user_id = data.get('user_id')  # ID del usuario

    if not original_url or not user_id:
        return jsonify({"message": "Faltan datos obligatorios (original_url, user_id)"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Verificar si ya existe una URL acortada para este usuario
        cursor.execute('''
            SELECT url_id FROM goshort.pro.URL WHERE base_url = %s AND user_id = %s;
        ''', (original_url, user_id))
        existing_url = cursor.fetchone()

        if existing_url:
            return jsonify({"url_short": f"{BASE_URL}{existing_url[0]}"}), 200

        # Generar un nuevo identificador único
        short_id = BASE_URL + str(generate_short_link())
        # Insertar la nueva URL en la base de datos
        creation_date = datetime.utcnow()
        cursor.execute('''
            INSERT INTO goshort.pro.URL (base_url, short_url, user_id)
            VALUES (%s, %s, %s);
        ''', (original_url, short_id, user_id))
        connection.commit()

        return jsonify({"url_short": f"{BASE_URL}{short_id}"}), 201

    except Exception as e:
        print(f"Error al acortar la URL: {e}")
        connection.rollback()
        return jsonify({"message": "Error del servidor"}), 500

    finally:
        cursor.close()
        connection.close()

# Ejecuta la aplicación
if __name__ == "__main__":
    app.run(debug=True)