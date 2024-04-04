import os
import tempfile
import urllib.parse
import uuid
import requests
import subprocess

# Set environment variables directly
key = os.getenv("TRANSLATOR_KEY")
endpoint = os.getenv("TRANSLATOR_ENDPOINT")
path = os.getenv("TRANSLATOR_PATH")
# Hugging Face API credentials
HF_API_URL = os.getenv("HF_API_URL")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")


# Function to download video from URL
def download_video(video_url, temp_video_path):
    response = requests.get(video_url)
    with open(temp_video_path, 'wb') as f:
        f.write(response.content)


# Function to extract audio from video using ffmpeg
def extract_audio(temp_video_path, temp_audio_path):
    subprocess.run(
        ['ffmpeg', '-y', '-i', temp_video_path, '-vn', '-acodec', 'flac', '-ar', '44100', '-ac', '2', temp_audio_path],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# Function to transcribe audio using Hugging Face API
def transcribe_audio_huggingface(audio_path):
    try:
        with open(audio_path, "rb") as f:
            data = f.read()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "audio/flac"
        }
        response = requests.post(HF_API_URL, headers=headers, data=data)
        response.raise_for_status()
        transcription = response.json()["text"]
        return transcription
    except Exception as e:
        print("Error transcribing audio using Hugging Face API:", e)
        return None


# Function to translate text using Azure Translator
def translate_text(transcription):
    try:
        constructed_url = endpoint + path
        params = {
            'api-version': '3.0',
            'to': ['en']
        }
        headers = {
            'Ocp-Apim-Subscription-Key': key,
            'Content-type': 'application/json',
            'Ocp-Apim-Subscription-Region': 'centralindia',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        body = [{'text': transcription}]
        request = requests.post(constructed_url, params=params, headers=headers, json=body)
        response = request.json()
        translated_text = response[0]['translations'][0]['text']
        return translated_text
    except Exception as e:
        print("Error translating text:", e)
        return None


# Function to transcribe and translate audio
def transcribe_and_translate_api(video_url):
    try:
        # Encode the video URL to ensure it doesn't contain control characters
        encoded_url = urllib.parse.quote(video_url, safe=':/')
        # Download video and extract audio
        temp_video_path = os.path.join(tempfile.mkdtemp(), 'temp_video.mp4')
        temp_audio_path = os.path.join(tempfile.mkdtemp(), 'temp_audio.flac')
        download_video(encoded_url, temp_video_path)
        extract_audio(temp_video_path, temp_audio_path)
        # Transcribe audio using Hugging Face API
        transcription = transcribe_audio_huggingface_with_retry(temp_audio_path)
        if transcription:
            # Translate the transcription
            translated_text = translate_text(transcription)
            # Clean up temporary files
            os.remove(temp_video_path)
            os.remove(temp_audio_path)
            return {"translated_text": translated_text, "translated_hindi_text": transcription}
        else:
            return {"translated_text": None, "translated_hindi_text": None}
    except Exception as e:
        return {"translated_text": None, "translated_hindi_text": None}


# Function to transcribe audio using Hugging Face API with retry logic
def transcribe_audio_huggingface_with_retry(audio_path, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            with open(audio_path, "rb") as f:
                data = f.read()
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {HF_API_TOKEN}",
                "Content-Type": "audio/flac"
            }
            response = requests.post(HF_API_URL, headers=headers, data=data)
            response.raise_for_status()
            transcription = response.json()["text"]
            return transcription
        except requests.exceptions.HTTPError as e:
            if response.status_code == 503 and retries < max_retries - 1:
                print("503 Error: Hugging Face API service is currently unavailable. Retrying...")
                # time.sleep(retry_delay)
                retries += 1
            else:
                print(f"Error transcribing audio using Hugging Face API: {e}")
                return None
        except Exception as e:
            print(f"Error transcribing audio using Hugging Face API: {e}")
            return None
    print("Maximum number of retries reached. Unable to transcribe audio.")
    return None
