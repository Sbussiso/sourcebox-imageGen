from flask import Flask, render_template, request, jsonify, session, send_file, flash, redirect, url_for
import requests
import io, os
from PIL import Image
from dotenv import load_dotenv
from flask_session import Session
import uuid
from openai import OpenAI
import traceback
import random
import string
import logging

# Load environment variables from the .env file to make sensitive information (like API keys) accessible
load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__)

# Configure the Flask session to store session data on the filesystem
app.config["SESSION_TYPE"] = "filesystem"
# Set a secret key for session encryption, defaulting to 'supersecretkey' if not found in the environment variables
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
# Initialize the Flask session
Session(app)

API_URL = os.getenv("API_URL")

# Setup API tokens for Hugging Face and OpenAI, retrieved from environment variables
api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
openai_key = os.getenv("OPENAI_API_KEY")

# Prepare headers for API requests to Hugging Face, including the authorization token
hf_headers = {"Authorization": f"Bearer {api_token}"}

# Initialize the OpenAI client with the retrieved API key
openai_client = OpenAI(api_key=openai_key)

# URLs for various Hugging Face models (Stability AI, Boreal, Flux, and Phantasma Anime)
stability_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
boreal_api_url = "https://api-inference.huggingface.co/models/kudzueye/Boreal"
flux_api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
phantasma_anime_api_url = "https://api-inference.huggingface.co/models/alvdansen/phantasma-anime"

# Utility functions
def check_authentication():
    logger.debug("Checking authentication status...")
    access_token = session.get('access_token')
    if access_token:
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_URL}/user_history", headers=headers)
            logger.debug(f"Authentication check response status: {response.status_code}")
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                logger.error("Access token is invalid or expired.")
                session.pop('access_token', None)
                flash('Session expired, please login again', 'danger')
                return False
            else:
                logger.error(f"Authentication check failed: {response.text}")
                session.pop('access_token', None)
                flash('Authentication check failed, please login again.', 'danger')
                return False
        except requests.RequestException as e:
            logger.error(f"Error during authentication check: {e}")
            flash('Error during authentication check. Please login again.', 'danger')
            session.pop('access_token', None)
            return False
    else:
        logger.debug("No access token found. User not authenticated.")
        flash('You need to login first.', 'danger')
        return False

# Before requests are made
@app.before_request
def before_request():
    logger.debug(f"Before request: {request.endpoint}")
    if request.endpoint not in ('login', 'register', 'static'):
        if not check_authentication():
            return redirect(url_for('login'))

def random_sig():
    """Generates a 3-character random signature, which can be a combination of letters or digits."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(3))

def log_debug(message):
    """Helper function to print debug messages to the console."""
    print(f"[DEBUG]: {message}")

def query_image(prompt, api_url):
    """
    Generic function to query a Hugging Face API for generating images based on a prompt.
    The function sends a POST request to the specified API URL with the prompt data.
    Returns the binary content of the generated image or None if an error occurred.
    """
    try:
        log_debug(f"Querying {api_url} with prompt: {prompt}")
        response = requests.post(api_url, headers=hf_headers, json={"inputs": prompt})
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        log_debug(f"Received response with status code {response.status_code}")
        return response.content  # Return the image content as bytes
    except requests.exceptions.RequestException as e:
        log_debug(f"Error querying {api_url}: {e}")
        traceback.print_exc()
        return None

def query_openai_image(prompt):
    """
    Query OpenAI's DALL-E 3 model to generate an image based on a given prompt.
    """
    try:
        log_debug(f"Querying OpenAI with prompt: {prompt}")
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        if response and response.data:
            image_url = response.data[0].url
            log_debug(f"Received image URL: {image_url}")
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            return image_response.content
    except requests.exceptions.RequestException as e:
        log_debug(f"Error querying OpenAI: {e}")
        traceback.print_exc()
    return None

def query_flux_image(prompt):
    return query_image(prompt, flux_api_url)

def query_boreal_image(prompt):
    return query_image(prompt, boreal_api_url)

def query_stability_image(prompt):
    return query_image(prompt, stability_api_url)

def query_phantasma_anime_image(prompt):
    return query_image(prompt, phantasma_anime_api_url)

def is_premium_user():
    token = session.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    user_id_url = f"{API_URL}/user/id"
    user_id_response = requests.get(user_id_url, headers=headers)
    if user_id_response.status_code == 200:
        user_id = user_id_response.json().get('user_id')
        premium_status_url = f"{API_URL}/user/{user_id}/premium/status"
        response = requests.get(premium_status_url, headers=headers)
        if response.status_code == 200:
            return response.json().get('premium_status', False)
    return False

# Routes
@app.route("/", methods=["GET"])
def index():
    if "conversation" not in session:
        session["conversation"] = []
    return render_template("index.html")

@app.route("/generate-image", methods=["POST"])
def generate_image():
    try:
        if "conversation" not in session:
            session["conversation"] = []

        data = request.get_json()
        prompt = data.get('prompt')
        generator = data.get('generator')

        if not prompt or not generator:
            return jsonify({"error": "Prompt and generator type are required."}), 400

        unique_prompt = f"{prompt} - {random_sig()}"

        if not is_premium_user() and generator != "openai":
            return jsonify({"error": "Only OpenAI is available for non-premium users."}), 403

        if generator == "openai":
            image_bytes = query_openai_image(unique_prompt)
        elif generator == "flux":
            image_bytes = query_flux_image(unique_prompt)
        elif generator == "stability":
            image_bytes = query_stability_image(unique_prompt)
        elif generator == "boreal":
            image_bytes = query_boreal_image(unique_prompt)
        elif generator == "phantasma-anime":
            image_bytes = query_phantasma_anime_image(unique_prompt)
        else:
            return jsonify({"error": "Invalid generator selected"}), 400

        if not image_bytes:
            return jsonify({"error": "Failed to generate image from the selected API."}), 500

        image_name = f"{generator}_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_path)

        session["conversation"].append({
            "prompt": unique_prompt,
            "generator": generator,
            "image_url": image_path
        })
        session.modified = True

        return jsonify({"image_url": image_path}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-history", methods=["GET"])
def conversation_history():
    return jsonify(session.get("conversation", []))

@app.route("/download-image/<filename>", methods=["GET"])
def download_image(filename):
    image_path = os.path.join("static", filename)
    if os.path.exists(image_path):
        return send_file(image_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

@app.route("/clear-session", methods=["POST"])
def clear_session():
    try:
        conversation = session.get("conversation", [])
        for entry in conversation:
            image_path = entry.get("image_url")
            if image_path and os.path.exists(image_path):
                os.remove(image_path)

        session.clear()
        return jsonify({"message": "Session and files cleared successfully!"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            response = requests.post(f"{API_URL}/login", json={'email': email, 'password': password})
            if response.status_code == 200:
                access_token = response.json().get('access_token')
                session['access_token'] = access_token
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
            else:
                message = response.json().get('message', 'Login failed')
                flash(message, 'danger')
        except requests.RequestException as e:
            flash('Error during login.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return redirect('https://sourcebox-official-website-9f3f8ae82f0b.herokuapp.com/sign_up')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
