import os
import shutil
from flask import Flask, render_template, request

from source.tts import text_to_mp3

app = Flask(__name__)
app.config['UPLOAD_DIR'] = 'uploads'

ASSETS_DIR = 'static/photos'


@app.route('/')
def uploader():
  return render_template('upload.html')



@app.route('/result',methods = ['POST', 'GET'])
def result():
  if request.method == 'POST':
    result = request.form

    # Ensure the form asked for a file
    if 'Image' not in request.files:
      return 'No file in form'

    image = request.files['Image']

    # Check if file uploaded
    if not image.filename:
      # TODO: send alert and reload the form
      return 'No file uploaded'

    # Save file to server
    asset_path = os.path.join(ASSETS_DIR, image.filename)
    print(f'saving image to {asset_path}')
    image.save(asset_path)

    # Read the description
    desc = result['Description']
    mp3_filename = text_to_mp3(desc, name='demo', rate=200, overwrite=True)

    return render_template('result.html', filename=asset_path, description=desc, mp3=mp3_filename)



if __name__ == '__main__':
  app.run(debug = True)
