from flask import Flask, render_template
from flask import make_response, request, current_app
from werkzeug import secure_filename
import os
app = Flask(__name__)

UPLOAD_FOLDER = './tmp/flask-upload-test/'
uploadfilenames = []
@app.route("/")
def main():
    return render_template('index.html')
# "ec2-18-216-179-182.us-east-2.compute.amazonaws.com"
@app.route("/upload", methods=['GET','POST'])
def upload():
    if (request.method=='POST'):
        Reply_to = request.form['Reply_to']
        To = request.form['To']
        subject = request.form['subject']
        if 'file' not in request.files:
            print ('no file')
            return Reply_to
        uploaded_files = request.files.getlist("file")
        # print(uploaded_files)
        uploadfilenames = []

        for file in uploaded_files:
            filename = secure_filename(file.filename)
            uploadfilenames.append(filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
        return "here"

if __name__ == "__main__":
    app.run()