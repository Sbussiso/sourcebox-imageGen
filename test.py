import requests, os
from dotenv import load_dotenv
import io
from PIL import Image

# Load environment variables from .env file
load_dotenv()

api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/alvdansen/phantasma-anime"
headers = {"Authorization": f"Bearer {api_token}"}

def query(payload):
	response = requests.post(API_URL, headers=headers, json=payload)
	return response.content
image_bytes = query({
	"inputs": "a wizard and a knight in an epic duel",
})

# You can access the image with PIL.Image for example
image = Image.open(io.BytesIO(image_bytes))
image.save("phantasma_anime_ai_image.png")
image.show()