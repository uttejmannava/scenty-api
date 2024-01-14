import os, psycopg2, json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from scrape import *

load_dotenv()

app = Flask(__name__)

# connection to postgreSQL database
databaseURL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(databaseURL)

CREATE_PERFUMES_TABLE = (
    "CREATE TABLE IF NOT EXISTS perfumes (id SERIAL PRIMARY KEY, name TEXT, gender JSON, brand TEXT, accords JSON, brandImageURL TEXT, bottleImageURL TEXT, rating FLOAT, ratingCount INTEGER, description TEXT)"
    )

CREATE_REVIEWS_TABLE = (
    "CREATE TABLE IF NOT EXISTS reviews (perfume_id INTEGER, author TEXT, date DATE, body TEXT, FOREIGN KEY(perfume_id) REFERENCES perfumes(id) ON DELETE CASCADE)"
)

INSERT_PERFUME_RETURN_ID = (
    "INSERT INTO perfumes (name, gender, brand, accords, brandImageURL, bottleImageURL, rating, ratingCount, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
)

INSERT_REVIEWS = (
    "INSERT INTO reviews (perfume_id, author, date, body) VALUES (%s, %s, %s, %s)"
)

# search fragrantica database by URL for a specific perfume; return info
@app.route("/search", methods=["GET"])
def scrapeInfo():
    url = request.args.get('url')
    if url is None:
        return jsonify({"error": "URL to perfume is missing"}), 400

    info = scrape_all(url)
    return jsonify(info)

# retrieve a specific perfume from the table, by name
@app.route("/perfumes", methods=["GET"])
def get_perfume():

    perfume_name = request.args.get('name')
    if perfume_name is None:
        return jsonify({"error": "perfume name is missing"}), 400
    
    connection = get_connection()
    
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PERFUMES_TABLE)
            cursor.execute("SELECT * from perfumes WHERE name = %s", (perfume_name,))
            perfume_info = cursor.fetchone()
    
    cursor.close()
    connection.close()

    if perfume_info: # make this show what each field is
        return jsonify(perfume_info), 200
    else:
        return jsonify({"error": "perfume not found in table"}), 404


# adding perfumes to our table, along with its reviews
@app.route("/perfumes", methods=["POST"])
def add_perfume():
    url = request.args.get('url')
    if url is None:
        return jsonify({"error": "URL to perfume is missing"}), 400
    
    info = scrape_all(url)
    
    perfume_name = info["name"]
    
    connection = get_connection()

    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM perfumes WHERE name = %s", (perfume_name,))
            existing_perfume_id = cursor.fetchone()
    
    # check if the perfume with the same name already exists
    if existing_perfume_id:
        # perfume with the same name already exists, ignore
        
        cursor.close()
        connection.close()
        
        return {
            "id": existing_perfume_id,
            "message": f"{perfume_name} is already stored in the table"
        }, 200
    
    else:
        required_keys = ["name", "gender", "brand", "accords", "brandImageURL", "bottleImageURL", "rating", "ratingCount", "description"]

        # check if all required keys are present
        if not all(key in info for key in required_keys):
            return jsonify({"error": "missing required keys in the scraped data"})

        info_tuple = (
            info["name"], 
            json.dumps(info["gender"]), 
            info["brand"], 
            json.dumps(info["accords"]), 
            info["brandImageURL"], 
            info["bottleImageURL"], 
            info["rating"],
            info["ratingCount"],
            info["description"]
            )

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_PERFUMES_TABLE) # won't do anything after the first insert
                cursor.execute(CREATE_REVIEWS_TABLE)
                cursor.execute(INSERT_PERFUME_RETURN_ID, info_tuple)
                perfume_id = cursor.fetchone()[0]

                for review in info["reviews"]:
                    review_tuple = (
                        perfume_id,
                        review["author"],
                        review["date"],
                        review["body"]
                    )
                    cursor.execute(INSERT_REVIEWS, review_tuple)
        
        cursor.close()
        connection.close()

        return jsonify({
            "id": perfume_id,
            "message": f"{info['name']} added to table, corresponding reviews populated into reviews table"
        }), 201

@app.route("/perfumes", methods=["DELETE"])
def delete_perfume():
    perfume_name = request.args.get('name')
    if perfume_name is None:
        return jsonify({"error": "perfume name is missing"}), 400
    
    connection = get_connection()

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PERFUMES_TABLE)
            cursor.execute(CREATE_REVIEWS_TABLE)
            cursor.execute("SELECT id, name from perfumes WHERE name = %s", (perfume_name,))
            result = cursor.fetchone()

    if result:

        perfume_id, perfume_name = result

        with connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM perfumes WHERE name = %s", (perfume_name,))
                cursor.execute("DELETE FROM reviews WHERE perfume_id = %s", (perfume_id,))

        cursor.close()
        connection.close()

        return jsonify({
            "id": perfume_id,
            "message": f"{perfume_name} removed from table, corresponding reviews removed from reviews table"
        }), 201
    else:
        cursor.close()
        connection.close()
        return jsonify({"error": "perfume not found in table"}), 404

@app.route("/perfumes/all", methods=["GET", "DELETE"])
def handle_all_perfumes():
    connection = get_connection()
    
    if request.method == "GET":
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM perfumes")
                all_perfumes = cursor.fetchall()

        cursor.close()
        connection.close()

        if not all_perfumes:
            return jsonify({"message": "table is empty"})
        return jsonify(all_perfumes), 200

    elif request.method == "DELETE":
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM perfumes")
                cursor.execute("DELETE FROM reviews")
        
        cursor.close()
        connection.close()

        return jsonify({"message": "all perfumes and corresponding reviews deleted"})

@app.route("/perfumes/random", methods=["GET"])
def get_random_perfume():
    connection = get_connection()
    
    with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_PERFUMES_TABLE)
                cursor.execute("SELECT * from perfumes ORDER BY RANDOM() LIMIT 1")
                result = cursor.fetchone()
    
    cursor.close()
    connection.close()

    if result:
        return jsonify(result), 200
    
    else:
        return jsonify({"error": "table is empty"})
    
@app.route("/perfumes/top")
def get_top_perfumes():
    num = request.args.get('num')
    if num is None:
        return jsonify({"error": "number of top perfumes requested is missing"}), 400
    
    connection = get_connection()

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PERFUMES_TABLE)
            cursor.execute(CREATE_REVIEWS_TABLE)
            cursor.execute("SELECT * FROM perfumes ORDER BY rating DESC LIMIT %s", (num,))
            result = cursor.fetchall()
    
    cursor.close()
    connection.close()

    return jsonify(result), 200

@app.route("/perfumes/stats", methods=["GET"])
def perfume_stats():
    
    connection = get_connection()
    
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PERFUMES_TABLE)
            cursor.execute(CREATE_REVIEWS_TABLE)

            cursor.execute("SELECT COUNT(*) FROM perfumes")
            perfume_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(rating) FROM perfumes")
            average_rating = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(ratingCount) FROM perfumes")
            average_ratingCount = cursor.fetchone()[0]

            cursor.execute("SELECT id, name FROM perfumes ORDER BY rating DESC LIMIT 1")
            top_perfume = cursor.fetchone()

            cursor.execute("SELECT id, name FROM perfumes ORDER BY rating ASC LIMIT 1")
            bottom_perfume = cursor.fetchone()

            cursor.execute("SELECT brand, COUNT(*) as value_count FROM perfumes GROUP BY brand ORDER BY value_count DESC;")
            brand_dist = cursor.fetchall()

    cursor.close()
    connection.close()

    if perfume_count:
        return jsonify({
            "perfume_count": perfume_count,
            "average_perfume_rating": round(average_rating, 2),
            "average_perfume_rating_count": round(average_ratingCount, 2),
            "top_rated_perfume": top_perfume,
            "bottom_rated_perfume": bottom_perfume,
            "brand_distribution": brand_dist
        }), 200
    else:
        return jsonify({"error": "table is empty"}), 404

@app.route("/reviews", methods=["GET"])
def get_reviews():
    perfume_id = request.args.get('perfume_id')
    if perfume_id is None:
        return jsonify({"error": "perfume id is missing"}), 400

    connection = get_connection()

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PERFUMES_TABLE)
            cursor.execute(CREATE_REVIEWS_TABLE)
            cursor.execute("SELECT * from reviews WHERE perfume_id = %s", (perfume_id,))
            result = cursor.fetchall()
    
    cursor.close()
    connection.close()

    if result:
        return jsonify(result), 200
    
    else:
        return jsonify({"error": "reviews for given perfume id not found in table"}), 404

if __name__ == "__main__":
    app.run(debug=True)