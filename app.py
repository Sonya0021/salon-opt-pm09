import hashlib
import pymysql
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_caching import Cache
from flask_compress import Compress

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
Compress(app)  # HTTP gzip сжатие

cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})
cache.init_app(app)

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'korochki_pm09',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# --- AUTH ---
@app.post('/api/register')
def register():
    d = request.json or {}
    login = d.get('login', '').strip()
    pw = d.get('password', '')
    full_name = d.get('full_name', '').strip()
    if len(login) < 5 or len(pw) < 6 or not full_name:
        return jsonify({'error': 'Логин от 5 симв., пароль от 6 симв., ФИО обязательно'}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM users WHERE login=%s', (login,))
            if cur.fetchone():
                return jsonify({'error': 'Логин уже занят'}), 409
            cur.execute('INSERT INTO users (login, password_hash, full_name, role_id) VALUES (%s,%s,%s,3)',
                        (login, hash_pw(pw), full_name))
        conn.commit()
    return jsonify({'message': 'Регистрация выполнена'}), 201

@app.post('/api/login')
def login():
    d = request.json or {}
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.login, u.full_name, r.name AS role
                FROM users u JOIN roles r ON u.role_id = r.id
                WHERE u.login=%s AND u.password_hash=%s
            """, (d.get('login', '').strip(), hash_pw(d.get('password', ''))))
            user = cur.fetchone()
            if not user:
                return jsonify({'error': 'Неверный логин или пароль'}), 401
            return jsonify({'user': user})

# --- КАТАЛОГ УСЛУГ С КЭШИРОВАНИЕМ, ФИЛЬТРОМ, ПОИСКОМ И ПАГИНАЦИЕЙ ---
@app.get('/api/catalog')
@cache.cached(timeout=300, query_string=True)
def get_catalog():
    q = request.args.get('q', '').strip()
    cat = request.args.get('category', '').strip()
    page = max(int(request.args.get('page', 1)), 1)
    per_page = min(int(request.args.get('per_page', 6)), 50)
    offset = (page - 1) * per_page

    where = ['1=1']
    params = []
    if q:
        where.append('name LIKE %s')
        params.append(f'%{q}%')
    if cat:
        where.append('category = %s')
        params.append(cat)
    where_sql = ' AND '.join(where)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) AS cnt FROM services WHERE {where_sql}', params)
            total = cur.fetchone()['cnt']
            cur.execute(f"""
                SELECT id, name, category, price, duration_min, img_color
                FROM services WHERE {where_sql}
                ORDER BY price ASC LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            items = cur.fetchall()
            for it in items:
                it['price'] = float(it['price'])
    return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page})

@app.get('/api/stylists')
@cache.cached(timeout=600)
def get_stylists():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, full_name, specialization FROM stylists')
            return jsonify(cur.fetchall())

# --- ЗАЯВКИ (CRUD + SUM ПО ЧЕКУ) ---
@app.get('/api/applications/my')
def my_applications():
    user_id = request.args.get('user_id', type=int)
    role = request.args.get('role', 'user')
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 10
    offset = (page - 1) * per_page

    with get_db() as conn:
        with conn.cursor() as cur:
            if role in ('admin', 'operator'):
                cur.execute("""
                    SELECT a.id, u.full_name AS client, s.name AS service_name, s.price,
                           st.full_name AS stylist, a.status_id, ast.name AS status,
                           DATE_FORMAT(a.start_date, '%%d.%%m.%%Y %%H:%%i') AS start_date
                    FROM applications a
                    JOIN users u ON a.user_id = u.id
                    JOIN services s ON a.service_id = s.id
                    JOIN stylists st ON a.stylist_id = st.id
                    JOIN application_statuses ast ON a.status_id = ast.id
                    ORDER BY a.created_at DESC LIMIT %s OFFSET %s
                """, (per_page, offset))
                items = cur.fetchall()
                cur.execute('SELECT COALESCE(SUM(s.price),0) AS total_sum FROM applications a JOIN services s ON a.service_id=s.id')
            else:
                cur.execute("""
                    SELECT a.id, u.full_name AS client, s.name AS service_name, s.price,
                           st.full_name AS stylist, a.status_id, ast.name AS status,
                           DATE_FORMAT(a.start_date, '%%d.%%m.%%Y %%H:%%i') AS start_date
                    FROM applications a
                    JOIN users u ON a.user_id = u.id
                    JOIN services s ON a.service_id = s.id
                    JOIN stylists st ON a.stylist_id = st.id
                    JOIN application_statuses ast ON a.status_id = ast.id
                    WHERE a.user_id = %s
                    ORDER BY a.created_at DESC LIMIT %s OFFSET %s
                """, (user_id, per_page, offset))
                items = cur.fetchall()
                cur.execute('SELECT COALESCE(SUM(s.price),0) AS total_sum FROM applications a JOIN services s ON a.service_id=s.id WHERE a.user_id=%s', (user_id,))
            total_sum = float(cur.fetchone()['total_sum'])
            for it in items:
                it['price'] = float(it['price'])
    return jsonify({'items': items, 'total_sum': total_sum})

@app.post('/api/applications')
def create_application():
    d = request.json or {}
    if not all([d.get('user_id'), d.get('service_id'), d.get('stylist_id'), d.get('start_date')]):
        return jsonify({'error': 'Заполните все поля заявки'}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO applications (user_id, service_id, stylist_id, status_id, start_date)
                VALUES (%s, %s, %s, 1, %s)
            """, (d['user_id'], d['service_id'], d['stylist_id'], d['start_date']))
        conn.commit()
    return jsonify({'message': 'Запись создана'}), 201

@app.patch('/api/applications/<int:app_id>/status')
def update_status(app_id):
    d = request.json or {}
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE applications SET status_id=%s WHERE id=%s', (d.get('status_id'), app_id))
        conn.commit()
    return jsonify({'message': 'Статус обновлен'})

@app.delete('/api/applications/<int:app_id>')
def delete_application(app_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM applications WHERE id=%s', (app_id,))
        conn.commit()
    return jsonify({'message': 'Запись удалена'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)