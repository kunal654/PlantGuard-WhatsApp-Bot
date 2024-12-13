import datetime
import logging
from flask import Flask,request
import requests
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import json
from dotenv import load_dotenv

import requests
url = "https://web-production-0cb7.up.railway.app/predict/"

def detect(file):
    file = {"file": open(file,'rb')}
    response = requests.post(url, files=file)
    result = json.loads(response.text)['class_name']
    return result

load_dotenv()

app = Flask(__name__)

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

UPLOAD_FOLDER = 'uploads' 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # this is for twilio to save the image from whatsapp message in static folder (uploads)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

session = {}

def save_image_from_url(media_url, from_number):
    static_dir = app.config['UPLOAD_FOLDER']
    image_name = f"whatsapp_{from_number.replace(':', '')}{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}.pdf"
    image_path = os.path.join(static_dir, image_name)

    try:
        message_sid = media_url.split('/')[-3]
        media_sid = media_url.split('/')[-1].split('.')[0]

        media = client.messages(message_sid).media(media_sid).fetch()
        media_url = f"https://api.twilio.com{media.uri.replace('.json', '')}"

        response = requests.get(media_url, auth=(account_sid, auth_token))
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"Image saved successfully: {image_path}")
        return image_path
    except Exception as e:
        logging.error(f"Error downloading image: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def chatbot():
    media_url = request.form.get('MediaUrl0')
    user_message = request.form.get('Body').lower()
    
    bot_message = MessagingResponse()
    
    if "state" not in session:
        session["state"] = "initial"
    
    if user_message in ['hi', 'hello'] and session["state"] == "initial":
        bot_message.message('👋 Hello! Send me a clear image of your plant’s leaf, and I’ll help identify any issues.')
        session["state"] = "processing"

    elif media_url and session["state"] == "processing":
        bot_message.message('🌿 Analyzing image... Please wait...')
        
        image_path = save_image_from_url(media_url, request.form.get('From'))
        if image_path:
            dis = detect(image_path)
            if dis == 'Unknown':
                bot_message.message('🚫 Couldn’t identify the issue. Please ensure the image shows the plant’s leaf.')
            else:
                bot_message.message(f'🔍 Detected: {dis}. 🍂')
        else:
            bot_message.message('🚫 Couldn’t download the image. Try again later.')

        bot_message.message('📷 Want to send another image? Reply Y for yes, N for no.')
    
    elif user_message == 'y':
        bot_message.message('🌿 Send another image for analysis.')
        session["state"] = "processing"
    
    elif user_message == 'n':
        bot_message.message('😊 Thanks for using the bot! Say "hi" anytime for help.')
        session["state"] = "initial"
        session.clear()

    else:
        bot_message.message('🤔 I didn’t understand. Reply "hi" to start over.')
        session["state"] = "initial"

    return str(bot_message)

