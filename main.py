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
    user_id = data.get('user_id')
    name_url = data.get('name_url')  # Nuevo campo

    # Verificación de campos obligatorios
    faltan_datos = []
    if not original_url:
        faltan_datos.append("original_url")
    if not user_id:
        faltan_datos.append("user_id")
    if not name_url:
        faltan_datos.append("name_url")

    if faltan_datos:
        return jsonify({
            "status": "error",
            "code": 400,
            "message": "Solicitud invalida. Verifique los datos ingresados.",
            "data": {
                "faltan_datos": faltan_datos
            }
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Obtener el límite de URLs y el número actual de URLs activas
        cursor.execute('''
            SELECT 
            cst.url_limit, 
            COUNT(ul.url_id) AS active_urls
            FROM goshort.pro.users u
            INNER JOIN goshort.pro.cat_subscription_type cst
                ON u.subscription_type_id = cst.subscription_type_id
            LEFT JOIN goshort.pro.url ul
                ON ul.user_id = u.user_id AND ul.active = TRUE
            WHERE u.user_id = %s
            GROUP BY cst.url_limit;
        ''', (user_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"message": "Usuario no encontrado"}), 404

        url_limit, active_urls = result

        if active_urls >= url_limit:
            return jsonify({
                "status": "error",
                "code": 403,
                "message": f"El usuario ha alcanzado el maximo de URLs generadas permitidas: {url_limit}",
                "data": None
            }), 403

        # Generar el enlace acortado y proceder con la inserción
        short_id = generate_short_link()
        cursor.execute('''
            INSERT INTO goshort.pro.url (name_url, base_url, short_url, user_id)
            VALUES (%s, %s, %s, %s) 
            RETURNING url_id, name_url, base_url, creation_date, short_url;
        ''', (name_url, original_url, f"{BASE_URL}{short_id}", user_id))

        new_url_id, new_name_url, new_base_url, new_creation_date, new_short_url = cursor.fetchone()

        # Contar las URLs del usuario después de la inserción
        cursor.execute('''
            SELECT COUNT(*) FROM goshort.pro.url WHERE user_id = %s;
        ''', (user_id,))
        user_count = cursor.fetchone()[0]

        # Actualizar el campo user_count en la tabla users
        cursor.execute('''
            UPDATE goshort.pro.users 
            SET user_count = %s 
            WHERE user_id = %s;
        ''', (user_count, user_id))

        connection.commit()

        return jsonify({
            "status": "success",
            "code": 201,
            "message": "URL acortada exitosamente",
            "data": {
                "url_id": new_url_id,
                "name_url": new_name_url,  # Retornar el nuevo campo
                "base_url": new_base_url,
                "creation_date": new_creation_date,
                "short_url": new_short_url,
                "user_count": user_count  # Retornar el conteo actualizado
            }
        }), 201

    except Exception as e:
        print(f"Error al acortar la URL: {e}")
        if connection:
            connection.rollback()  # Revierte en caso de error
        return jsonify({"message": "Error del servidor"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()




# Ejecuta la aplicación
#if __name__ == "__main__":
#    app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) # PRO
    #app.run(host="0.0.0.0", port=6000, debug=True)  # DEV
