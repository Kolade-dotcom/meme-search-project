from cs50 import SQL
from flask import Flask, redirect, request, render_template, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import generate_related_memes, error, login_required, generate_object_name
from PIL import Image as img
import flask_session, os, sys
import base64, io

# Configure application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\PC\OneDrive\Documents'

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
flask_session.Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///meme_search.db")

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# get api key
api_key = sys.argv[1]

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # check if file was uploaded
        if 'imageUpload' not in request.files:
            return error("No file uploaded.")
    
        # get the image file
        file = request.files['imageUpload']
        if file.filename == '':
            return error("No file selected.")
        
        # save the file to a temporary location
        filename = secure_filename(file.filename)
        main_image_url = url_for('uploaded_file', filename=filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # open the image file
        image_array = img.open(file_path)
        # get the predicted object in the image array
        object_name = generate_object_name(image_array)

        # create query by appending meme to the name of the object generated
        query = object_name + " meme"
        # get related image urls on query
        image_urls = generate_related_memes(query, api_key)
            
        # check if the images where generated
        if len(image_urls) == 0:
            return error("An error occurred while loading the images")
        
        return render_template("info_meme.html", image_urls=image_urls, main_image_url=main_image_url, name=object_name)        
    
    return render_template("index.html")


@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    # send the uploaded image file from temporary directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route("/camera", methods=["POST", "GET"])
@login_required
def camera_capture():
    if request.method == "POST":
        # get data url from the server
        data_url = request.json['dataUrl']
        
        # get image data from url
        image_data = base64.b64decode(data_url.split(',')[1])
        # open the image file
        image_array = img.open(io.BytesIO(image_data))
        # get the predicted object in the image array
        object_name = generate_object_name(image_array)

        # create query by appending meme to the name of the object generated
        query = object_name + " meme"
        # get related image urls on query
        image_urls = generate_related_memes(query, api_key)
            
        # check if the images where generated
        if len(image_urls) == 0:
            return error("An error occurred while loading the images")
        
        return render_template("camera_meme.html", image_urls=image_urls, name=object_name)
        
    return render_template("camera_capture.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # get the username password and the confirmation from the form
        username, password, confirmation = request.form.get("username"), request.form.get("password"), request.form.get("confirmation")
        # get username if it exist
        row = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Ensures username was submitted and it does not already exist
        if not username or len(row) != 0:
            return error("Invalid Username")

        # Ensure password and confirmation was submitted and are the same
        elif not password  or not confirmation or password != confirmation:
            return error ("Invalid password and/or ensure password and confirmation are the same")

        # Insert the new user and the hashed password
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))

        return redirect("/")

    return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)