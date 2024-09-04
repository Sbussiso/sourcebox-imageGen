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
    
    Args:
    - prompt (str): The text prompt to guide the image generation.
    - api_url (str): The URL of the specific Hugging Face model's API.
    
    Returns:
    - The binary content of the generated image or None if an error occurred.
    """
    try:
        log_debug(f"Querying {api_url} with prompt: {prompt}")
        # Send the request with the prompt to the API
        response = requests.post(api_url, headers=hf_headers, json={"inputs": prompt})
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        log_debug(f"Received response with status code {response.status_code}")
        return response.content  # Return the image content as bytes
    except requests.exceptions.RequestException as e:
        log_debug(f"Error querying {api_url}: {e}")
        traceback.print_exc()
        return None

# Define specific functions for querying each model API on Hugging Face

def query_flux_image(prompt):
    return query_image(prompt, flux_api_url)

def query_boreal_image(prompt):
    return query_image(prompt, boreal_api_url)

def query_stability_image(prompt):
    return query_image(prompt, stability_api_url)

def query_phantasma_anime_image(prompt):
    return query_image(prompt, phantasma_anime_api_url)

def query_openai_image(prompt):
    """
    Query OpenAI's DALL-E 3 model to generate an image based on a given prompt.
    """
    try:
        log_debug(f"Querying OpenAI with prompt: {prompt}")
        # Send request to OpenAI's API to generate an image
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",  # Set desired image size
            quality="standard",  # Standard quality for the image
            n=1,  # Request only one image
        )
        
        # Check if the response contains valid data
        if response and response.data:
            image_url = response.data[0].url  # Extract the URL of the generated image
            log_debug(f"Received image URL: {image_url}")
            
            # Download the image from the provided URL
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            return image_response.content  # Return the binary content of the image
        else:
            log_debug("No data returned from OpenAI")
    except requests.exceptions.RequestException as e:
        log_debug(f"Error querying OpenAI: {e}")
        traceback.print_exc()
    return None

@app.route("/", methods=["GET"])
def index():
    """
    The home route for the Flask app, rendering the index.html template.
    Initializes a 'conversation' in the session if it doesn't already exist.
    """
    # Initialize conversation history in the session if it hasn't been created
    if "conversation" not in session:
        log_debug("Initializing conversation in session")
        session["conversation"] = []
    return render_template("index.html")  # Render the home page

@app.route("/clear-session", methods=["POST"])
def clear_session():
    """
    API route to clear the user's session data and delete any stored images.
    """
    try:
        log_debug("Clearing session and deleting images")
        # Retrieve the conversation history from the session
        conversation = session.get("conversation", [])

        # Iterate through each image in the conversation and delete the corresponding file from disk
        for entry in conversation:
            image_path = entry.get("image_url")
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)  # Delete the image file
                    log_debug(f"Deleted: {image_path}")
                except Exception as e:
                    log_debug(f"Error deleting {image_path}: {e}")
                    traceback.print_exc()

        # Clear the session to reset the conversation history
        session.clear()
        log_debug("Session cleared successfully")
        return jsonify({"message": "Session and files cleared successfully!"}), 200
    except Exception as e:
        log_debug(f"Error during session clearing: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/generate-image", methods=["POST"])
def generate_image():
    """
    API route for generating an image based on a prompt and a selected generator.
    Saves the generated image and stores the conversation in the user's session.
    """
    try:
        # Ensure that 'conversation' is initialized in the session
        if "conversation" not in session:
            log_debug("Initializing conversation in session")
            session["conversation"] = []

        # Extract JSON data from the POST request
        data = request.get_json()
        prompt = data.get('prompt')  # The prompt to generate the image
        generator = data.get('generator')  # The selected image generator (e.g., flux, openai)

        log_debug(f"Received request: prompt={prompt}, generator={generator}")

        # Validate that both a prompt and a generator were provided
        if not prompt or not generator:
            log_debug("Prompt or generator missing in request")
            return jsonify({"error": "Prompt and generator type are required."}), 400

        # Add a random signature to the prompt to ensure uniqueness even if the same prompt is used multiple times
        unique_prompt = f"{prompt} - {random_sig()}"

        # Generate the image using the specified generator
        if generator == "flux":
            image_bytes = query_flux_image(unique_prompt)
        elif generator == "openai":
            image_bytes = query_openai_image(unique_prompt)
        elif generator == "stability":
            image_bytes = query_stability_image(unique_prompt)
        elif generator == "boreal":
            image_bytes = query_boreal_image(unique_prompt)
        elif generator == "phantasma-anime":
            image_bytes = query_phantasma_anime_image(unique_prompt)
        else:
            log_debug(f"Invalid generator: {generator}")
            return jsonify({"error": "Invalid generator selected"}), 400

        # Ensure that image generation succeeded
        if not image_bytes:
            log_debug(f"Failed to generate image for generator: {generator}")
            return jsonify({"error": "Failed to generate image from the selected API."}), 500

        # Save the generated image as a PNG file with a unique name
        image_name = f"{generator}_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"  # Save in the static directory
        log_debug(f"Saving image as {image_path}")
        
        # Open the image content as a PIL image and save it to disk
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_path)

        # Append the prompt and image path to the conversation stored in the session
        log_debug("Storing image in session")
        session["conversation"].append({
            "prompt": unique_prompt,
            "generator": generator,
            "image_url": image_path
        })
        session.modified = True  # Mark the session as modified

        return jsonify({"image_url": image_path}), 200  # Return the image URL to the client

    except Exception as e:
        log_debug(f"Error in generate_image: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-history", methods=["GET"])
def conversation_history():
    """
    API route to fetch the conversation history from the session.
    """
    try:
        log_debug("Fetching conversation history")
        # Return the stored conversation history (or an empty list if not found)
        return jsonify(session.get("conversation", []))
    
    except Exception as e:
        log_debug(f"Error fetching conversation history: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route("/download-image/<filename>", methods=["GET"])
def download_image(filename):
    """
    Route to download the generated image file.
    """
    image_path = os.path.join("static", filename)
    if os.path.exists(image_path):
        return send_file(image_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404


@app.route("/regenerate-image", methods=["POST"])
def regenerate_image():
    """
    API route for regenerating an image based on the original prompt and generator.
    """
    try:
        # Extract JSON data from the POST request
        data = request.get_json()
        prompt = data.get('prompt')  # The original prompt
        generator = data.get('generator')  # The selected image generator (e.g., flux, openai)

        log_debug(f"Received regenerate request: prompt={prompt}, generator={generator}")

        # Validate that both a prompt and a generator were provided
        if not prompt or not generator:
            log_debug("Prompt or generator missing in regenerate request")
            return jsonify({"error": "Prompt and generator type are required."}), 400

        # Add a random signature to the prompt to ensure a new unique image is generated
        unique_prompt = f"{prompt} - {random_sig()}"

        # Generate the image using the specified generator
        if generator == "flux":
            image_bytes = query_flux_image(unique_prompt)
        elif generator == "openai":
            image_bytes = query_openai_image(unique_prompt)
        elif generator == "stability":
            image_bytes = query_stability_image(unique_prompt)
        elif generator == "boreal":
            image_bytes = query_boreal_image(unique_prompt)
        elif generator == "phantasma-anime":
            image_bytes = query_phantasma_anime_image(unique_prompt)
        else:
            log_debug(f"Invalid generator: {generator}")
            return jsonify({"error": "Invalid generator selected"}), 400

        # Ensure that image generation succeeded
        if not image_bytes:
            log_debug(f"Failed to regenerate image for generator: {generator}")
            return jsonify({"error": "Failed to regenerate image from the selected API."}), 500

        # Save the regenerated image as a PNG file with a unique name
        image_name = f"{generator}_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"  # Save in the static directory
        log_debug(f"Saving regenerated image as {image_path}")

        # Open the image content as a PIL image and save it to disk
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_path)

        # Return the image URL of the regenerated image
        return jsonify({"image_url": image_path}), 200

    except Exception as e:
        log_debug(f"Error in regenerate_image: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


#auth API
API_URL = os.getenv("API_URL")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logger.debug(f"Login attempt with email: {email}")

        try:
            response = requests.post(f"{API_URL}/login", json={'email': email, 'password': password})
            logger.debug(f"Login response status: {response.status_code}")

            if response.status_code == 200:
                access_token = response.json().get('access_token')
                session['access_token'] = access_token
                flash('Logged in successfully!', 'success')
                logger.debug("Login successful, redirecting to homepage...")
                return redirect(url_for('index'))
            else:
                message = response.json().get('message', 'Login failed')
                logger.error(f"Login failed: {message}")
                flash(message, 'danger')
        except requests.RequestException as e:
            logger.error(f"Error during login: {e}")
            flash('Error during login.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    logger.debug("Redirecting to external registration page...")
    return redirect('https://sourcebox-official-website-9f3f8ae82f0b.herokuapp.com/sign_up')




if __name__ == "__main__":
    # Start the Flask app in debug mode for local development
    log_debug("Starting Flask app")
    app.run(debug=True)
