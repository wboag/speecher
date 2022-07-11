
import pyttsx3
from pydub import AudioSegment
import os
import re


# Initialize TTS engine
engine = pyttsx3.init()


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



def text_to_mp3(text, name='', rate=200, overwrite=False):
    text = preprocess_for_pyttsx3(text)

    # Load paramerers into the TTS engine
    engine.setProperty('rate', rate) # set playback speed

    # Where to store this file?
    if name == '':
        basename = f'{len(os.listdir(MP3_DIR))}'
    else:
        playback = rate / 200. # what speed? (eg 400 = 2x speed)
        basename = f'{name}-{playback:.1f}x'

    mp3_filename = os.path.join(MP3_DIR, f'{basename}.mp3')
    if (overwrite) or (not os.path.exists(mp3_filename)):
        # save to aiff (because thats what pyttsx3 does)
        aiff_filename = f'/tmp/{basename}.aiff'
        engine.save_to_file(text, aiff_filename)
        engine.runAndWait()
        print(f'saved tmp audio file {aiff_filename}')

        # convert from aiff to mp3
        aiff = AudioSegment.from_file(aiff_filename)
        aiff.export(mp3_filename, format='mp3')
        print(f'saved audio file {mp3_filename}')

        # Remove aiff file
        os.remove(aiff_filename)
        print(f'removed tmp audio file {aiff_filename}')

    else:
        print(f'audio file {mp3_filename} already exists')

    asset_filename = os.path.join(RELATIVE_MP3_PATH, f'{basename}.mp3')
    return asset_filename



if __name__ == '__main__':
    #text = 'The outlook wasnt brilliant for the Mudville Nine that day.'
    text = 'You are doing so good, friend! Keep it up!'
    mp3_filename = text_to_mp3(text, 'motivate', rate=200)

