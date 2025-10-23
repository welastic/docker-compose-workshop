from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
import os
import time

app = Flask(__name__)
CORS(app)

db_url = os.environ.get('DATABASE_URL')
engine = None
for attempt in range(10):
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        break
    except Exception as e:
        print(f"DB not ready ({attempt}) - retrying: {e}")
        time.sleep(1)

@app.route('/')
def hello():
    return jsonify({"message": "Hello from backend"})

@app.route('/test')
def test():
    return "Backend is working! This is a simple text response."

@app.route('/items', methods=['GET', 'POST'])
def items():
    try:
        if request.method == 'POST':
            data = request.json or {}
            name = data.get('name', 'unnamed')
            with engine.begin() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS items (id serial primary key, name text);"))
                conn.execute(text("INSERT INTO items (name) VALUES (:name)"), {"name": name})
            return jsonify({"status": "created", "name": name}), 201

        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS items (id serial primary key, name text);"))
            result = conn.execute(text("SELECT id, name FROM items ORDER BY id"))
            rows = [{'id': row[0], 'name': row[1]} for row in result]
        return jsonify(rows)
    except Exception as e:
        print(f"Error in /items: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/items/<int:item_id>', methods=['PUT', 'DELETE'])
def item_operations(item_id):
    try:
        if request.method == 'PUT':
            data = request.json or {}
            name = data.get('name')
            if not name:
                return jsonify({"error": "Name is required"}), 400
            
            with engine.begin() as conn:
                result = conn.execute(text("UPDATE items SET name = :name WHERE id = :id"), {"name": name, "id": item_id})
                if result.rowcount == 0:
                    return jsonify({"error": "Item not found"}), 404
            return jsonify({"status": "updated", "id": item_id, "name": name})
        
        elif request.method == 'DELETE':
            with engine.begin() as conn:
                result = conn.execute(text("DELETE FROM items WHERE id = :id"), {"id": item_id})
                if result.rowcount == 0:
                    return jsonify({"error": "Item not found"}), 404
            return jsonify({"status": "deleted", "id": item_id})
    except Exception as e:
        print(f"Error in /items/{item_id}: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host=os.environ.get('FLASK_RUN_HOST', '0.0.0.0'), port=int(os.environ.get('FLASK_RUN_PORT', 5000)))
