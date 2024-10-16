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
import replicate

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
        logger.debug("Received request to generate image")

        if "conversation" not in session:
            session["conversation"] = []

        data = request.get_json()
        prompt = data.get('prompt')
        generator = data.get('generator')

        logger.debug(f"Prompt: {prompt}, Generator: {generator}")

        if not prompt or not generator:
            logger.error("Prompt and generator type are required.")
            return jsonify({"error": "Prompt and generator type are required."}), 400

        unique_prompt = f"{prompt} - {random_sig()}"
        logger.debug(f"Unique prompt: {unique_prompt}")

        if not is_premium_user() and generator != "openai":
            logger.warning("Non-premium user trying to access non-OpenAI generator")
            return jsonify({"error": "Only OpenAI is available for non-premium users."}), 403

        image_bytes = None
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
            logger.error("Invalid generator selected")
            return jsonify({"error": "Invalid generator selected"}), 400

        if not image_bytes:
            logger.error("Failed to generate image from the selected API.")
            return jsonify({"error": "Failed to generate image from the selected API."}), 500

        image_name = f"{generator}_image_{uuid.uuid4().hex}.png"
        image_path = f"static/{image_name}"
        logger.debug(f"Saving image to: {image_path}")

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.save(image_path)
            logger.info(f"Image saved successfully: {image_name}")
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return jsonify({"error": "Error saving image"}), 500

        session["conversation"].append({
            "prompt": unique_prompt,
            "generator": generator,
            "image_url": image_name  # Store only the image name
        })
        session.modified = True

        return jsonify({"image_url": image_name}), 200

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-history", methods=["GET"])
def conversation_history():
    conversation = session.get("conversation", [])
    videos = session.get("videos", [])
    
    # Combine images and videos into a single list
    for video in videos:
        conversation.append({
            "prompt": "Generated Video",
            "generator": "video",
            "video_url": video
        })
    
    return jsonify(conversation)

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

@app.route('/generate-video', methods=['POST'])
def generate_video():
    try:
        logger.info("Starting video generation process")
        
        # Load environment variables
        load_dotenv()
        api_token = os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            logger.error("API Token not found. Please check your .env file.")
            return jsonify({"error": "API Token not found"}), 500

        # Get the model and version
        logger.debug("Fetching model and version")
        try:
            model = replicate.models.get("sunfjun/stable-video-diffusion")
            version = model.versions.get("d68b6e09eedbac7a49e3d8644999d93579c386a083768235cabca88796d70d82")
        except Exception as e:
            logger.error(f"Error fetching model or version: {e}")
            return jsonify({"error": "Error fetching model or version"}), 500

        # Extract input image path from request
        data = request.get_json()
        image_path = data.get('image_url')  # This is actually a path in the static folder
        if not image_path:
            logger.error("No image path provided")
            return jsonify({"error": "Image path is required"}), 400

        # Construct the full path to the image
        full_image_path = os.path.join('static', image_path)
        logger.debug(f"Full image path: {full_image_path}")

        # Open the image file
        with open(full_image_path, 'rb') as image_file:
            logger.info(f"Creating prediction for image file: {full_image_path}")
            try:
                # Create a prediction
                prediction = replicate.predictions.create(
                    version=version,
                    input={
                        "input_image": image_file,
                        "cond_aug": 0.05,
                        "decoding_t": 14,
                        "video_length": "14_frames_with_svd",
                        "sizing_strategy": "maintain_aspect_ratio",
                        "motion_bucket_id": 127,
                        "frames_per_second": 6
                    }
                )
            except Exception as e:
                logger.error(f"Error creating prediction: {e}")
                return jsonify({"error": "Error creating prediction"}), 500

            # Wait for the prediction to complete
            logger.info("Waiting for prediction to complete")
            prediction.wait()

            # Check the status and get the output
            if prediction.status == 'succeeded':
                output_url = prediction.output
                logger.info(f"Prediction succeeded, video URL: {output_url}")

                # Download the video
                video_response = requests.get(output_url)
                video_response.raise_for_status()

                # Save the video to the static directory
                video_name = f"video_{uuid.uuid4().hex}.mp4"
                video_path = os.path.join('static', video_name)
                with open(video_path, 'wb') as video_file:
                    video_file.write(video_response.content)

                logger.info(f"Video saved successfully at {video_path}")

                # Save the video URL in the session
                if "videos" not in session:
                    session["videos"] = []
                session["videos"].append(video_name)
                session.modified = True

                return jsonify({"video_url": video_name}), 200
            else:
                logger.error(f"Prediction failed with status: {prediction.status}, detail: {prediction.error}")
                return jsonify({"error": f"Prediction failed with status: {prediction.status}"}), 500

    except replicate.exceptions.ReplicateError as e:
        logger.error(f"Replicate API error during video generation: {e}")
        return jsonify({"error": "An error occurred with the Replicate API"}), 500
    except Exception as e:
        logger.error(f"Unexpected error during video generation: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/get-videos', methods=['GET'])
def get_videos():
    videos = session.get("videos", [])
    return jsonify({"videos": videos})

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
api_token = os.getenv("REPLICATE_API_TOKEN")
if not api_token:
    logger.error("API Token not found. Please check your .env file.")
    exit(1)

# Initialize the model and version
try:
    model = replicate.models.get("batouresearch/magic-image-refiner")
    version = model.versions.get("507ddf6f977a7e30e46c0daefd30de7d563c72322f9e4cf7cbac52ef0f667b13")
except Exception as e:
    logger.error(f"Error fetching model or version: {e}")
    exit(1)

@app.route('/upscale-image', methods=['POST'])
def upscale_image():
    logger.debug("Received request to upscale image")
    data = request.get_json()
    image_path = data.get('image_path')

    if not image_path:
        logger.error("Image path not provided in the request")
        return jsonify({"error": "Image path is required"}), 400

    try:
        # Construct the full path to the image
        full_image_path = os.path.join('static', image_path)
        logger.debug(f"Full image path: {full_image_path}")

        # Open the image file
        with open(full_image_path, 'rb') as image_file:
            logger.info("Creating prediction for image upscaling")
            prediction = replicate.predictions.create(
                version=version,
                input={
                    "hdr": 0,
                    "image": image_file,
                    "steps": 20,
                    "prompt": "UHD 4k",
                    "scheduler": "DDIM",
                    "creativity": 0.25,
                    "guess_mode": False,
                    "resolution": "original",
                    "resemblance": 0.75,
                    "guidance_scale": 7,
                    "negative_prompt": "teeth, tooth, open mouth, longbody, lowres, bad anatomy, bad hands, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, mutant"
                }
            )
            logger.debug("Waiting for prediction to complete")
            prediction.wait()

            if prediction.status == 'succeeded' and isinstance(prediction.output, list) and len(prediction.output) > 0:
                output_url = prediction.output[0]
                logger.info(f"Prediction succeeded, output URL: {output_url}")

                # Download the upscaled image
                upscaled_image_response = requests.get(output_url)
                upscaled_image_response.raise_for_status()

                # Save the upscaled image to the static directory
                upscaled_image_name = f"upscaled_image_{uuid.uuid4().hex}.png"
                upscaled_image_path = os.path.join('static', upscaled_image_name)
                with open(upscaled_image_path, 'wb') as upscaled_image_file:
                    upscaled_image_file.write(upscaled_image_response.content)

                logger.info(f"Upscaled image saved successfully at {upscaled_image_path}")

                # Add the upscaled image to the session's conversation
                if "conversation" not in session:
                    session["conversation"] = []

                session["conversation"].append({
                    "prompt": "Upscaled Image",
                    "generator": "upscale",
                    "image_url": upscaled_image_name
                })
                session.modified = True

                # Return the path of the saved upscaled image
                return jsonify({"output_url": upscaled_image_name}), 200
            else:
                logger.error(f"Prediction failed with status: {prediction.status}, detail: {prediction.error}")
                return jsonify({"error": f"Prediction failed with status: {prediction.status}"}), 500

    except FileNotFoundError:
        logger.error(f"Image file not found at path: {full_image_path}")
        return jsonify({"error": "Image file not found"}), 404
    except replicate.exceptions.ReplicateError as e:
        logger.error(f"Replicate API error during prediction: {e}")
        return jsonify({"error": "An error occurred with the Replicate API"}), 500
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error: {e}")
        return jsonify({"error": "An error occurred while making an HTTP request"}), 500
    except Exception as e:
        logger.error(f"Unexpected error during prediction: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)