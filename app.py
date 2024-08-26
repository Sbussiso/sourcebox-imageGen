from flask import Flask, render_template, request, jsonify, session
import requests
import io, os
from PIL import Image
from dotenv import load_dotenv
from flask_session import Session
import uuid
from openai import OpenAI

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

# Hugging Face Stability AI and Boreal API setup
stability_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
boreal_api_url = "https://api-inference.huggingface.co/models/kudzueye/Boreal"
flux_api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"

def query_image(prompt, api_url):
    """Generic function to query Hugging Face API."""
    try:
        response = requests.post(api_url, headers=hf_headers, json={"inputs": prompt})
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error querying {api_url}: {e}")
        return None

def query_flux_image(prompt):
    return query_image(prompt, flux_api_url)

def query_boreal_image(prompt):
    return query_image(prompt, boreal_api_url)

def query_stability_image(prompt):
    return query_image(prompt, stability_api_url)

def query_openai_image(prompt):
    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        if response and response.data:
            image_url = response.data[0].url
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            return image_response.content
    except requests.exceptions.RequestException as e:
        print(f"Error querying OpenAI: {e}")
    return None

@app.route("/", methods=["GET"])
def index():
    # Ensure that 'conversation' is initialized in the session
    if "conversation" not in session:
        session["conversation"] = []
    return render_template("index.html")

@app.route("/clear-session", methods=["POST"])
def clear_session():
    # Get the conversation history from the session
    conversation = session.get("conversation", [])

    # Iterate through each image in the conversation history and delete the file
    for entry in conversation:
        image_path = entry.get("image_url")
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"Deleted: {image_path}")
            except Exception as e:
                print(f"Error deleting {image_path}: {e}")

    # Clear the session
    session.clear()

    return jsonify({"message": "Session and files cleared successfully!"}), 200

@app.route("/generate-image", methods=["POST"])
def generate_image():
    try:
        # Ensure that 'conversation' is initialized in the session
        if "conversation" not in session:
            session["conversation"] = []

        data = request.get_json()
        prompt = data.get('prompt')
        generator = data.get('generator')

        if not prompt or not generator:
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
        else:
            return jsonify({"error": "Invalid generator selected"}), 400

        # Ensure that the image_bytes is not empty
        if not image_bytes:
            return jsonify({"error": "Failed to generate image from the selected API."}), 500

        # Save the image as a file (use a unique name including the generator name)
        image_name = f"{generator}_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_path)

        # Store user prompt and image path in session
        session["conversation"].append({
            "prompt": prompt,
            "generator": generator,
            "image_url": image_path
        })
        session.modified = True

        return jsonify({"image_url": image_path}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-history", methods=["GET"])
def conversation_history():
    return jsonify(session.get("conversation", []))

if __name__ == "__main__":
    app.run(debug=True)
