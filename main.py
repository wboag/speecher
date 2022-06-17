import os
import shutil
from flask import Flask, render_template, request
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

ASSETS_FOLDER = 'static/photos'


@app.route('/')
def uploader():
  return render_template('upload.html')


'''
@app.route('/uploads')
def view_assets():
  print('AAAAA')
  print(request)
  print('BBBBB')
  return '<p>unsure</p>'
'''


@app.route('/result',methods = ['POST', 'GET'])
def result():
  if request.method == 'POST':
    result = request.form

    # Ensure the form asked for a file
    if 'Video' not in request.files:
      return 'No file in form'

    video = request.files['Video']

    # Check if file uploaded
    if not video.filename:
      # TODO: send alert and reload the form
      return 'No file uploaded'

    # Save file to server
    asset_path = os.path.join(ASSETS_FOLDER, video.filename)
    print(f'saving video to {asset_path}')
    video.save(asset_path)

    name = result['Name']
    return render_template("result.html", filename=asset_path, name=name)

if __name__ == '__main__':
  app.run(debug = True)
