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

# Hugging Face Stability AI API setup
stability_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

def query_flux_image(prompt):
    response = requests.post("https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev", headers=hf_headers, json={"inputs": prompt})
    if response.status_code != 200:
        raise Exception(f"Failed to generate image: {response.status_code} - {response.text}")
    return response.content

def query_openai_image(prompt):
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
        if image_response.status_code == 200:
            return image_response.content
        else:
            raise Exception(f"Failed to download image: {image_response.status_code}")
    raise Exception("Failed to generate image from OpenAI")

def query_stability_image(prompt):
    response = requests.post(stability_api_url, headers=hf_headers, json={"inputs": prompt})
    if response.status_code != 200:
        raise Exception(f"Failed to generate image: {response.status_code} - {response.text}")
    return response.content

@app.route("/", methods=["GET"])
def index():
    if "conversation" not in session:
        session["conversation"] = []
    return render_template("index.html")

@app.route("/generate-image", methods=["POST"])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        generator = data.get('generator')

        # Generate image using the selected generator
        if generator == "flux":
            image_bytes = query_flux_image(prompt)
        elif generator == "openai":
            image_bytes = query_openai_image(prompt)
        elif generator == "stability":
            image_bytes = query_stability_image(prompt)
        else:
            return jsonify({"error": "Invalid generator selected"}), 400

        # Save the image as a file (use a unique name for each session)
        image_name = f"generated_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_path)

        # Store user prompt and image path in session
        session["conversation"].append({
            "prompt": prompt,
            "image_url": image_path
        })
        session.modified = True

        return jsonify({"image_url": image_path})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-history", methods=["GET"])
def conversation_history():
    return jsonify(session.get("conversation", []))

if __name__ == "__main__":
    app.run(debug=True)
