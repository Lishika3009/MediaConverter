from flask import Flask, request, render_template, redirect, url_for, flash
from moviepy.editor import VideoFileClip
import os
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flashing messages

# Path for saving uploaded files
UPLOAD_FOLDER = 'uploads'
TRANSCRIPT_FOLDER = 'transcripts'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(TRANSCRIPT_FOLDER):
    os.makedirs(TRANSCRIPT_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSCRIPT_FOLDER'] = TRANSCRIPT_FOLDER


# create a speech recognition object
r = sr.Recognizer()

# Function to recognize speech in the audio file
def transcribe_audio(path):
    with sr.AudioFile(path) as source:
        audio_listened = r.record(source)
        text = r.recognize_google(audio_listened)
    return text

# Function that splits the audio file into chunks on silence and applies speech recognition
def get_large_audio_transcription_on_silence(path):
    sound = AudioSegment.from_file(path)
    chunks = split_on_silence(sound,
                              min_silence_len=500,
                              silence_thresh=sound.dBFS - 14,
                              keep_silence=500)
    folder_name = "audio-chunks"
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    whole_text = ""
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        try:
            text = transcribe_audio(chunk_filename)
        except sr.UnknownValueError as e:
            print("Error:", str(e))
        else:
            text = f"{text.capitalize()}. "
            print(chunk_filename, ":", text)
            whole_text += text
    return whole_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert/video-to-audio', methods=['POST'])
def video_to_audio():
    file = request.files['file']
    if file:
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(video_path)
        video = VideoFileClip(video_path)
        audio_path = os.path.splitext(video_path)[0] + ".mp3"
        video.audio.write_audiofile(audio_path)
        video.close()
        flash(f"Audio extracted successfully: {audio_path}", "success")
    else:
        flash("Failed to extract audio.", "error")
    return redirect(url_for('index'))

@app.route('/convert/audio-to-text', methods=['POST'])
def audio_to_text():
    file = request.files['file']
    if file:
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(audio_path)
        transcription = get_large_audio_transcription_on_silence(audio_path)
        transcript_file_path = os.path.join(app.config['TRANSCRIPT_FOLDER'], os.path.splitext(file.filename)[0] + ".txt")
        with open(transcript_file_path, 'w') as f:
            f.write(transcription)
        flash(f"Transcription saved successfully: {transcript_file_path}", "success")
    else:
        flash("Failed to transcribe audio.", "error")
    return redirect(url_for('index'))

@app.route('/convert/video-to-text', methods=['POST'])
def video_to_text():
    file = request.files['file']
    if file:
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(video_path)
        video = VideoFileClip(video_path)
        audio_path = os.path.splitext(video_path)[0] + "_temp.wav"
        video.audio.write_audiofile(audio_path)
        transcription = get_large_audio_transcription_on_silence(audio_path)
        os.remove(audio_path)  # Clean up the temporary audio file
        flash(transcription, "success")
    else:
        flash("Failed to transcribe video.", "error")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
