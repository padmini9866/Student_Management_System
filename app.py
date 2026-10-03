import os
import mysql.connector
from mysql.connector import Error
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# ------------------------------------------------------------
# DATABASE CONFIG (override with environment variables if needed)
# ------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "student@123"),
    "database": os.getenv("DB_NAME", "student_management"),
}


def connect_database():
    return mysql.connector.connect(**DB_CONFIG)


def create_table():
    connection = connect_database()
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            age INT NOT NULL,
            gender VARCHAR(20),
            course VARCHAR(100),
            phone VARCHAR(20),
            email VARCHAR(100)
        )
        """
    )
    connection.commit()
    cursor.close()
    connection.close()


def validate(data):
    name = (data.get("name") or "").strip()
    if not name:
        return None, "Student name cannot be empty."
    try:
        age = int(data.get("age"))
        if age <= 0 or age > 120:
            raise ValueError
    except (TypeError, ValueError):
        return None, "Age must be a valid number."
    clean = {
        "name": name,
        "age": age,
        "gender": (data.get("gender") or "").strip(),
        "course": (data.get("course") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "email": (data.get("email") or "").strip(),
    }
    return clean, None


def run(query, params=(), fetch=None, commit=False):
    """Run one query; fetch can be 'all', 'one' or None."""
    connection = connect_database()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        result = None
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        if commit:
            connection.commit()
        return result, cursor.lastrowid, cursor.rowcount
    finally:
        cursor.close()
        connection.close()


# ------------------------------------------------------------
# PAGES
# ------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ------------------------------------------------------------
# API
# ------------------------------------------------------------
@app.route("/api/students", methods=["GET"])
def list_students():
    q = (request.args.get("q") or "").strip()
    try:
        if q:
            like = f"%{q}%"
            rows, _, _ = run(
                "SELECT * FROM students WHERE name LIKE %s OR course LIKE %s "
                "OR email LIKE %s OR CAST(id AS CHAR) = %s ORDER BY id",
                (like, like, like, q),
                fetch="all",
            )
        else:
            rows, _, _ = run("SELECT * FROM students ORDER BY id", fetch="all")
        return jsonify(rows)
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/students", methods=["POST"])
def add_student():
    data, err = validate(request.get_json(silent=True) or {})
    if err:
        return jsonify({"error": err}), 400
    try:
        _, new_id, _ = run(
            "INSERT INTO students (name, age, gender, course, phone, email) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (data["name"], data["age"], data["gender"], data["course"],
             data["phone"], data["email"]),
            commit=True,
        )
        return jsonify({"message": "Student added successfully!", "id": new_id}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    data, err = validate(request.get_json(silent=True) or {})
    if err:
        return jsonify({"error": err}), 400
    try:
        existing, _, _ = run("SELECT id FROM students WHERE id = %s",
                             (student_id,), fetch="one")
        if not existing:
            return jsonify({"error": "Student not found."}), 404
        run(
            "UPDATE students SET name=%s, age=%s, gender=%s, course=%s, "
            "phone=%s, email=%s WHERE id=%s",
            (data["name"], data["age"], data["gender"], data["course"],
             data["phone"], data["email"], student_id),
            commit=True,
        )
        return jsonify({"message": "Student updated successfully!"})
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    try:
        _, _, count = run("DELETE FROM students WHERE id = %s",
                          (student_id,), commit=True)
        if count == 0:
            return jsonify({"error": "Student not found."}), 404
        return jsonify({"message": "Student deleted successfully!"})
    except Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    try:
        create_table()
    except Error as e:
        print("Database connection error:", e)
        raise SystemExit(1)
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True)
