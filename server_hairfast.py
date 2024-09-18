import os
import re
import requests
from confluent_kafka import Consumer, Producer, KafkaError

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
import json

cloudinary.config( 
  cloud_name = "dsjuckdxu", 
  api_key = "973371356842627", 
  api_secret = "zJ5bMJgfkw3XBdyBocwO8Kgs1us",
  secure = True
)

output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

model_args = get_parser().parse_args([])
hair_fast = HairFast(model_args)
print("============Model loaded=============")

# Kafka Consumer configuration
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',  # Replace with your Kafka broker(s)
    'group.id': 'my_consumer_group',  # Consumer group id
    'auto.offset.reset': 'earliest'  # Start consuming from the earliest message
}

# Kafka Producer configuration
producer_conf = {
    'bootstrap.servers': 'localhost:9092',  # Replace with your Kafka broker(s)
}

# Create Kafka Consumer and Producer instances
consumer = Consumer(consumer_conf)
producer = Producer(producer_conf)

# Subscribe to the source topic
source_topic = 'hairfast'
consumer.subscribe([source_topic])

# Target topic to which processed data will be sent
target_topic = 'result_hairfast'

# Folder to save downloaded images
download_folder = './downloaded_images'
os.makedirs(download_folder, exist_ok=True)

# Function to download image from URL and save it
def download_image(url, filename):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the download was successful
        image_path = os.path.join(download_folder, filename)
        with open(image_path, 'wb') as f:
            f.write(response.content)
        print(f"Image saved at {image_path}")
        return image_path
    except Exception as e:
        print(f"Failed to download image from {url}: {str(e)}")
        return None

# Function to parse the received message
def parse_message(message):
    # Extract the fields from the message
    pattern = r'\{"url":"(.*?)","created_at":(\d+),"account_id":(\d+),"self_img":"(.*?)","shape_img":"(.*?)","color_img":"(.*?)"\}'
    match = re.search(pattern, message)
    
    if match:
        parsed_data = {
            'url': match.group(1),
            'created_at': match.group(2),
            'account_id': match.group(3),
            'self_img': match.group(4),
            'shape_img': match.group(5),
            'color_img': match.group(6)
        }
        return parsed_data
    else:
        print("Failed to parse message")
        return None

# Function to process the message and download images
def process_message(value):
    print(f"Processing message: {value}")
    parsed_data = parse_message(value)

    if parsed_data:
        print(f"Parsed data: {parsed_data}")
        
        # Download images
        self_img_path = download_image(parsed_data['self_img'], "self_image.jpg")
        shape_img_path = download_image(parsed_data['shape_img'], "shape_img.jpg")
        color_img_path = download_image(parsed_data['color_img'], "color_image_.jpg")
        
        return {
            'SelfImgPath': self_img_path,
            'ShapeImgPath': shape_img_path,
            'ColorImgPath': color_img_path,
            'SelfImgCloud': parsed_data['self_img'],
            'ShapeImgCloud': parsed_data['shape_img'],
            'ColorImgCloud': parsed_data['color_img']
        }
    return None

# Delivery report callback for the producer
def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

# Main loop to consume, process, and produce messages
try:
    while True:
        # Poll for new messages
        msg = consumer.poll(1.0)  # Timeout set to 1 second

        if msg is None:
            # No message received in poll
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event
                print(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
            else:
                # Other error
                print(f"Error occurred: {msg.error()}")
            continue

        # Get the message key and value
        key = msg.key().decode('utf-8') if msg.key() else None
        value = msg.value().decode('utf-8') if msg.value() else None
        print(f"Received message from 'hairfast': Key={key}, Value={value}")

        # Process the received message
        processed_data = process_message(value)

        if processed_data:
            # Prepare a response with paths to downloaded images
            
            self_img_path = processed_data['SelfImgPath']
            shape_img_path = processed_data['ShapeImgPath']
            color_img_path = processed_data['ColorImgPath']

            final_image,face_align, shape_align, color_align = hair_fast.swap(self_img_path, shape_img_path, color_img_path, align=True)
            output_image_path = output_dir / 'final_image_result.png'
            save_image(final_image, output_image_path)

            resp=cloudinary.uploader.upload(output_image_path)

            print(resp['secure_url'])
            
            result_message = {
                "self_img_cloud": processed_data['SelfImgCloud'],
                "shape_img_cloud": processed_data['ShapeImgCloud'],
                "color_img_cloud": processed_data['ColorImgCloud'],
                "generated_img_cloud": resp['secure_url']
            }
            
            result_message_json = json.dumps(result_message)

            
            # Send the processed result to "result_hairfast"
            producer.produce(
                topic=target_topic,
                key=key,
                value=result_message_json,
                callback=delivery_report
            )
            producer.flush()  # Ensure the message is sent
finally:
    # Close the consumer when done
    consumer.close()
