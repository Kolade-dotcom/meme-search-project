from transformers import ViTFeatureExtractor as VFE, ViTForImageClassification as VIC
import requests
from flask import render_template, session, redirect
from functools import wraps

# set url that would be used for the image search
url = 'https://www.googleapis.com/customsearch/v1'

# render message as an apology to user
def error(message, code=400):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("error.html", top=code, bottom=escape(message))


# decorate routes to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# use ViT to predict the class name from image array
def generate_object_name(image_array):
    try:
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
    
    return class_name


# use api key to make the query on image search
def generate_related_memes(query, api_key):
    cx = "f6aac2aa50b5f4d75"
    try:
        params = {
            "q": query,
            "cx": cx,
            "searchType": "image",
            "key": api_key,
            "num": 10
        }

        response = requests.get(url, params=params)
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
        
    return image_urls