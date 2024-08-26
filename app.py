from flask import Flask, render_template, request, jsonify, session
import requests
import io, os
from PIL import Image
from dotenv import load_dotenv
from flask_session import Session
import uuid
from openai import OpenAI
import traceback

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configure session storage
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
Session(app)

# Hugging Face and OpenAI API setup
api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
openai_key = os.getenv("OPENAI_API_KEY")
hf_headers = {"Authorization": f"Bearer {api_token}"}
openai_client = OpenAI(api_key=openai_key)

# Hugging Face Stability AI, Boreal, Flux, and Phantasma Anime API setup
stability_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
boreal_api_url = "https://api-inference.huggingface.co/models/kudzueye/Boreal"
flux_api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
phantasma_anime_api_url = "https://api-inference.huggingface.co/models/alvdansen/phantasma-anime"


def log_debug(message):
    print(f"[DEBUG]: {message}")

def query_image(prompt, api_url):
    """Generic function to query Hugging Face API."""
    try:
        log_debug(f"Querying {api_url} with prompt: {prompt}")
        response = requests.post(api_url, headers=hf_headers, json={"inputs": prompt})
        response.raise_for_status()
        log_debug(f"Received response with status code {response.status_code}")
        return response.content
    except requests.exceptions.RequestException as e:
        log_debug(f"Error querying {api_url}: {e}")
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

def query_openai_image(prompt):
    try:
        log_debug(f"Querying OpenAI with prompt: {prompt}")
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        if response and response.data:
            image_url = response.data[0].url
            log_debug(f"Received image URL: {image_url}")
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            return image_response.content
        else:
            log_debug("No data returned from OpenAI")
    except requests.exceptions.RequestException as e:
        log_debug(f"Error querying OpenAI: {e}")
        traceback.print_exc()
    return None

@app.route("/", methods=["GET"])
def index():
    # Ensure that 'conversation' is initialized in the session
    if "conversation" not in session:
        log_debug("Initializing conversation in session")
        session["conversation"] = []
    return render_template("index.html")

@app.route("/clear-session", methods=["POST"])
def clear_session():
    try:
        log_debug("Clearing session and deleting images")
        # Get the conversation history from the session
        conversation = session.get("conversation", [])

        # Iterate through each image in the conversation history and delete the file
        for entry in conversation:
            image_path = entry.get("image_url")
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    log_debug(f"Deleted: {image_path}")
                except Exception as e:
                    log_debug(f"Error deleting {image_path}: {e}")
                    traceback.print_exc()

        # Clear the session
        session.clear()
        log_debug("Session cleared successfully")
        return jsonify({"message": "Session and files cleared successfully!"}), 200
    except Exception as e:
        log_debug(f"Error during session clearing: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/generate-image", methods=["POST"])
def generate_image():
    try:
        # Ensure that 'conversation' is initialized in the session
        if "conversation" not in session:
            log_debug("Initializing conversation in session")
            session["conversation"] = []

        data = request.get_json()
        prompt = data.get('prompt')
        generator = data.get('generator')

        log_debug(f"Received request: prompt={prompt}, generator={generator}")

        if not prompt or not generator:
            log_debug("Prompt or generator missing in request")
            return jsonify({"error": "Prompt and generator type are required."}), 400

        # Generate image using the selected generator
        if generator == "flux":
            image_bytes = query_flux_image(prompt)
        elif generator == "openai":
            image_bytes = query_openai_image(prompt)
        elif generator == "stability":
            image_bytes = query_stability_image(prompt)
        elif generator == "boreal":
            image_bytes = query_boreal_image(prompt)
        elif generator == "phantasma-anime":
            image_bytes = query_phantasma_anime_image(prompt)
        else:
            log_debug(f"Invalid generator: {generator}")
            return jsonify({"error": "Invalid generator selected"}), 400

        # Ensure the image_bytes is not empty
        if not image_bytes:
            log_debug(f"Failed to generate image for generator: {generator}")
            return jsonify({"error": "Failed to generate image from the selected API."}), 500

        # Save the image as a file (use a unique name including the generator name)
        image_name = f"{generator}_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"
        log_debug(f"Saving image as {image_path}")
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_path)

        # Store user prompt and image path in session
        log_debug("Storing image in session")
        session["conversation"].append({
            "prompt": prompt,
            "generator": generator,
            "image_url": image_path
        })
        session.modified = True

        return jsonify({"image_url": image_path}), 200

    except Exception as e:
        log_debug(f"Error in generate_image: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-history", methods=["GET"])
def conversation_history():
    try:
        log_debug("Fetching conversation history")
        return jsonify(session.get("conversation", []))
    except Exception as e:
        log_debug(f"Error fetching conversation history: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    log_debug("Starting Flask app")
    app.run(debug=True)
