from flask import Flask, request, jsonify
from PIL import Image  # Import the Image class from PIL
import os

from pathlib import Path
from hair_swap import HairFast, get_parser

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import torchvision.transforms as T
import torch
from torchvision.utils import save_image

import cloudinary
import cloudinary.uploader
import cloudinary.api
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Save the final image
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

cloudinary.config( 
  cloud_name = "dsjuckdxu", 
  api_key = "973371356842627", 
  api_secret = "zJ5bMJgfkw3XBdyBocwO8Kgs1us",
  secure = True
)

model_args = get_parser().parse_args([])
hair_fast = HairFast(model_args)

@app.route('/upload-images', methods=['POST'])
def upload_images():
    if 'selfImg' not in request.files or 'shapeImg' not in request.files or 'colorImg' not in request.files:
        return jsonify({"error": "All three image files (selfImg, shapeImg, corlorImg) are required."}), 400

     # Retrieve files from the request
    self_img = request.files['selfImg']
    shape_img = request.files['shapeImg']
    color_img = request.files['colorImg']

    # Check if any file is missing
    if not self_img.filename or not shape_img.filename or not color_img.filename:
        return jsonify({"error": "One or more files are missing."}), 400

    try:


        self_img_path = os.path.join(UPLOAD_FOLDER, self_img.filename)
        self_img.save(self_img_path)

        shape_img_path = os.path.join(UPLOAD_FOLDER, shape_img.filename)
        shape_img.save(shape_img_path)

        color_img_path = os.path.join(UPLOAD_FOLDER, color_img.filename)
        color_img.save(color_img_path)

        final_image,face_align, shape_align, color_align = hair_fast.swap(self_img_path, shape_img_path, color_img_path, align=True)

        
        output_image_path = output_dir / 'final_image_result.png'
        save_image(final_image, output_image_path)

        resp=cloudinary.uploader.upload(output_image_path)

        print(resp['secure_url'])

        response_message = f"Final image saved to {resp['secure_url']}"
        return jsonify({"message": response_message}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
