# speecher

First attempt at the PDF-to-mp3 app.


# Setting up database

    $ export FLASK_APP=main

    $ flask shell

	>>> from main import db, ActivityLog

	>>> db.create_all()


# Notes

    - The current approach uses the espeak library to do text-to-speech because pyttsx3 wasnt working and gTTS throttled too much. Unfortunately, espeak is very robotic-y. Would love to improve in the future.

    - On AWS ec2, it was very hard to get the audio processing to run. Here is a way that worked for installing ffmpeg: https://www.maskaravivek.com/post/how-to-install-ffmpeg-on-ec2-running-amazon-linux/
