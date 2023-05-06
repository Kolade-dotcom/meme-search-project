from cs50 import SQL
from functools import wraps
from flask import Flask, redirect, request, render_template, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import requests, os, sys
from transformers import ViTFeatureExtractor as VFE, ViTForImageClassification as VIC
from PIL import Image as img

# Configure application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\PC\OneDrive\Documents'

# # Configure session to use filesystem (instead of signed cookies)
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# requests.Session(app)

# # Configure CS50 Library to use SQLite database
# db = SQL("sqlite:///meme_search.db")

# @app.after_request
# def after_request(response):
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     response.headers["Expires"] = 0
#     response.headers["Pragma"] = "no-cache"
#     return response

api_key = sys.argv[1]
urls = ['https://kgsearch.googleapis.com/v1/entities:search', 'https://www.googleapis.com/customsearch/v1']


def error(message, code=400):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("error.html", top=code, bottom=escape(message)), code


# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if session.get("user_id") is None:
#             return redirect("/login")
#         return f(*args, **kwargs)
#     return decorated_function


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'imageUpload' not in request.files:
            return error("No file uploaded.")
    
        file = request.files['imageUpload']
        if file.filename == '':
            return error("No file selected.")
        
        # save the file to a temporary location
        filename = secure_filename(file.filename)
        main_image_url = url_for('uploaded_file', filename=filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            image_array = img.open(file_path)

            model_id = 'google/vit-base-patch16-224'
            feature_extractor = VFE.from_pretrained(model_id)
            model = VIC.from_pretrained(model_id)

            inputs = feature_extractor(images=image_array, return_tensors='pt')
            outputs = model(**inputs)
            logits = outputs.logits

            predicted_class_id = logits.argmax(-1).item()
            class_name = model.config.id2label[predicted_class_id].split(",")
            class_name = class_name[0]
        
        except (OSError, ValueError) as e:
            print("An error occurred while processing the image:", e)
            return error("An error occurred while recognizing the image")
        
        q = class_name + " meme"
        cx = "f6aac2aa50b5f4d75"
        try:
            params = {
                "q": q,
                "cx": cx,
                "searchType": "image",
                "key": api_key,
                "num": 10
            }

            response = requests.get(urls[1], params=params)
            data = response.json()

            # Extract the image URLs from the response
            if 'items' in data:
                image_urls = [item['link'] for item in data['items']]
            else:
                raise KeyError("No 'items' found in the response.")
        
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)
            image_urls = []
            
        except KeyError as e:
            print("Could not extract image URLs:", e)
            image_urls = []
            
        if len(image_urls) == 0:
            return error("An error occurred while loading the memes")
        
        return render_template("info_meme.html", image_urls=image_urls, main_image_url=main_image_url, name=class_name)        
    
    return render_template("index.html")


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/camera")
def camera_capture():
    return render_template("camera_capture.html")


# @app.route("/login", methods=["GET", "POST"])
# def login():
#     # Forget any user_id
#     session.clear()

#     # User reached route via POST (as by submitting a form via POST)
#     if request.method == "POST":
#         # Ensure username was submitted
#         if not request.form.get("username"):
#             return error("must provide username", 403)

#         # Ensure password was submitted
#         elif not request.form.get("password"):
#             return error("must provide password", 403)

#         # Query database for username
#         rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

#         # Ensure username exists and password is correct
#         if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
#             return error("invalid username and/or password", 403)

#         # Remember which user has logged in
#         session["user_id"] = rows[0]["id"]

#         # Redirect user to home page
#         return redirect("/")

#     return render_template("login.html")


# @app.route("/logout")
# def logout():
#     # Forget any user_id
#     session.clear()

#     # Redirect user to login form
#     return redirect("/")


# @app.route("/signup", methods=["GET", "POST"])
# def signup():
#     if request.method == "POST":
#         # get the username password and the confirmation from the form
#         username, password, confirmation = request.form.get("username"), request.form.get("password"), request.form.get("confirmation")
#         # get username if it exist
#         row = db.execute("SELECT * FROM users WHERE username = ?", username)

#         # Ensures username was submitted and it does not already exist
#         if not username or len(row) != 0:
#             return error("Invalid Username")

#         # Ensure password and confirmation was submitted and are the same
#         elif not password  or not confirmation or password != confirmation:
#             return error ("Invalid password and/or ensure password and confirmation are the same")

#         # Insert the new user and the hashed password
#         db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))

#         return redirect("/")

#     return render_template("signup.html")


if __name__ == "__main__":
    app.run(debug=True)