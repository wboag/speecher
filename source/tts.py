
#import pyttsx3
from gtts import gTTS
from pydub import AudioSegment
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



def text_to_mp3(text, name='', overwrite=False):
    text = preprocess_for_gtts(text)

    # Where to store this file?
    if name == '':
        basename = f'{len(os.listdir(MP3_DIR))}'
    else:
        basename = f'{name}'

    mp3_filename = os.path.join(MP3_DIR, f'{basename}.mp3')
    if (overwrite) or (not os.path.exists(mp3_filename)):
        # save to mp3
        myobj = gTTS(text=text, lang='en', slow=False)
        myobj.save(mp3_filename)
        print(f'saved audio file {mp3_filename}')

    else:
        print(f'audio file {mp3_filename} already exists')

    asset_filename = os.path.join(RELATIVE_MP3_PATH, f'{basename}.mp3')
    return asset_filename



if __name__ == '__main__':
    #text = 'The outlook wasnt brilliant for the Mudville Nine that day.'
    text = 'You are doing so good, friend! Keep it up!'
    mp3_filename = text_to_mp3(text, 'motivate')

