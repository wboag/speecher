
#import pyttsx3
#from gtts import gTTS
from pydub import AudioSegment
import random
import os
import re



# where to save mp3s
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELATIVE_MP3_PATH = os.path.join('static', 'mp3')
MP3_DIR = os.path.join(PROJECT_DIR, RELATIVE_MP3_PATH)


def preprocess_for_pyttsx3(text):
    # TODO: parse chapters/sections so that it has a 'end of chapter' x3 delimiter
    pass

    # pyttsx3 seems to only read one sentence, so make it one larger sentence
    text = re.sub('[^0-9a-zA-Z ]+', ' ', text)
    text = re.sub('\n+', ' ', text)
    return text



def preprocess_for_gtts(text):
    # TODO: parse chapters/sections so that it has a 'end of chapter' x3 delimiter
    pass

    return text



def preprocess_for_espeak(text):
    # TODO: parse chapters/sections so that it has a 'end of chapter' x3 delimiter
    pass

    return text



def text_to_mp3(text, name='', overwrite=False):
    text = preprocess_for_gtts(text)

    # Where to store this file?
    if name == '':
        basename = f'{len(os.listdir(MP3_DIR))}'
    else:
        basename = f'{name}'
    asset_filename = os.path.join(RELATIVE_MP3_PATH, f'{basename}.mp3')

    mp3_filename = os.path.join(MP3_DIR, f'{basename}.mp3')
    if (overwrite) or (not os.path.exists(mp3_filename)):
        # tmp file for espeak to read
        r = random.randint(0,100000)
        tmpfile = f'/tmp/{r}.txt'
        with open(tmpfile, 'w') as f:
            print(text, file=f)

        # Save to file
        wav_file = f'/tmp/{basename}.wav'
        cmd = f'espeak -f {tmpfile} -s 200 -w {wav_file}'
        os.system(cmd)
        os.remove(tmpfile)

        # Convert wav to mp3
        AudioSegment.from_wav(wav_file).export(asset_filename, format="mp3")
        os.remove(wav_file)

        output = f'saved audio file {mp3_filename}'

    else:
        output = f'audio file {mp3_filename} already exists'

    return asset_filename, output



if __name__ == '__main__':
    #text = 'The outlook wasnt brilliant for the Mudville Nine that day.'
    text = 'You are doing so good, friend! Keep it up!'
    mp3_filename = text_to_mp3(text, 'motivate')

