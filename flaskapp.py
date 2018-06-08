from __future__ import print_function
from apiclient.discovery import build
from apiclient import errors

from httplib2 import Http
from oauth2client import file, client, tools

from flask import Flask, render_template, redirect
# from utils import Service, encode_image
import base64
from flask import make_response, request, current_app
from flask import *
from flask import send_from_directory
import requests as rp
import json
import os, email, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from apiclient.http import MediaIoBaseDownload
from werkzeug import secure_filename
from flask_cors import CORS
import io
import time



path = os.path.dirname(__file__)
# modify this to change the Template Directory

app = Flask(__name__)
CORS(app)

def getfilenamebyId(service, file_id):
  try:
    file = service.files().get(fileId=file_id).execute()
    return file['name']
  except :
    pass
    return ""

def download(service, fileIds, prefix):
    fileNames = []
    for id in fileIds:
        name = prefix + "/" + getfilenamebyId(service , id)
        fileNames.append(name)
        req = service.files().get_media(fileId=id)
        fh = io.FileIO(name, 'w')
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        try:
            while done is False:
                status, done = downloader.next_chunk()
        except Exception as inst:
            return "Failed in downloading html file. please check fileId again"
    return fileNames

class EmailTemplate():
    def __init__(self, template_name='', values={}, html=True):
        self.template_name = template_name
        self.values = values
        self.html = html

    def render(self):
        content = open(self.template_name).read()

        for k, v in self.values.items():
            content = content.replace('[%s]' % k, v)
        return content

class MailMessage(object):
    html = False

    def __init__(self, from_email='', to_emails=[], cc_emails=[], subject='', body='', template=None, attachments=[]):
        self.from_email = from_email
        self.to_emails = to_emails
        self.cc_emails = cc_emails
        self.subject = subject
        self.template = template
        self.body = body
        self.file_attachments = attachments

    def attach_file(self, path):
        self.file_attachments.append(path)

    def get_message(self):
        if isinstance(self.to_emails, str):
            self.to_emails = [self.to_emails]

        if isinstance(self.cc_emails, str):
            self.cc_emails = [self.cc_emails]

        if len(self.to_emails) == 0 or self.from_email == '':
            raise ValueError('Invalid From or To email address(es)')

        msg = MIMEMultipart('alternative')
        msg['To'] = ', '.join(self.to_emails)
        msg['Cc'] = ', '.join(self.cc_emails)
        msg['From'] = self.from_email
        msg['Subject'] = self.subject
        if self.template:
            if self.template.html:
                msg.attach(MIMEText(self.body, 'plain'))
                msg.attach(MIMEText(self.template.render(), 'html'))
            else:
                msg.attach(MIMEText(self.template.render(), 'plain'))
        else:
            msg.attach(MIMEText(self.body, 'plain'))

        for attachment in self.file_attachments:
            with open(attachment, "rb") as f:
                filename = os.path.basename(attachment)
                part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = 'attachment; filename="' + str(filename) + '"'
                msg.attach(part)
        return msg

class MailServer(object):
    msg = None

    def __init__(self, server_name='smtp.gmail.com', username='<username>', password='<password>', port=587,
                 require_starttls=True):
        self.server_name = server_name
        self.username = username
        self.password = password
        self.port = port
        self.require_starttls = require_starttls

def send(mail_msg, mail_server=MailServer()):
    server = smtplib.SMTP(mail_server.server_name, mail_server.port)
    if mail_server.require_starttls:
        server.starttls()
    if mail_server.username:
        server.login(mail_server.username, mail_server.password)
    server.sendmail(mail_msg.from_email, (mail_msg.to_emails + mail_msg.cc_emails), mail_msg.get_message().as_string())
    server.close()


def getConnection():
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage(path + '/credentials.json')
    creds = store.get()

    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(path + '/client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)

    service = build('drive', 'v3', http=creds.authorize(Http()))
    return service

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/sendEmail', methods=['POST'])
def sendEmail():
    if request.method == 'POST':

        ##############  Get params from request ###############
        ##   reply_to   :  destination email
        ##   file_id    :  email file id of google drive  %% You can get file id using this end point "ec2-18-216-179-182.us-east-2.compute.amazonaws.com/fileList"
        ##   subject    :  Subject of Email
        ##   attachment :  attach file params
        ##   address    :  Address information
        ##   price      :  Price param
        ##   name       :  Name param
        #######################################################

        if 'msg[Reply_to]' in request.form:
            Reply_to = request.form['msg[Reply_to]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[Reply_to]'"})

        if 'msg[To]' in request.form:
            To = request.form['msg[To]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[To]'"})

        if 'googleattachment' in request.form:
            googleattachment = request.form['googleattachment']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'googleattachment'"})

        if 'address' in request.form:
            address = request.form['address']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'address'"})

        if 'price' in request.form:
            price = request.form['price']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'price'"})

        if 'name' in request.form:
            name = request.form['name']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'name'"})

        if 'templateID' in request.form:
            templateID = request.form['templateID']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'templateID'"})

        if 'subject' in request.form:
            subject = request.form['subject']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'subject'"})

        prefix = path + "/uploads/" + str(int(round(time.time() * 1000)))
        if not os.path.exists(prefix):
            os.makedirs(prefix)

        templateFileName = prefix + "/email.html"

        ## get instance of connection for google drive
        service = getConnection()
        ## download file which id is file_id and save as "email.html"
        req = service.files().get_media(fileId=templateID)
        fh = io.FileIO(templateFileName, 'w')
        downloader = MediaIoBaseDownload(fh, req)

        done = False
        try:
            while done is False:
                status, done = downloader.next_chunk()
        except Exception as inst:
            return json.dumps({"error": "Failed in downloading html file. please check fileId again"})
        fh.close()
        ### download attached files
        fileIds = googleattachment.replace(" ", "")
        fileIds = fileIds.split(",")
        attachFileNames = download(service, fileIds, prefix)

        ## Define values which are needed to exchange with email text.
        values = {}
        # values['username'] = 'mail@gmail.com'
        # values['from'] = 'mail@gmail.com'
        # values['url'] = ''

        ## Sending email to reply_to
        temp = EmailTemplate(template_name= templateFileName, values=values)
        server = MailServer(server_name='smtp.office365.com', username='nina@la-retrofit.com',
                            password='Test123456789@',
                            port=587, require_starttls=True)
        msg = MailMessage(from_email='nina@la-retrofit.com', to_emails=[Reply_to],
                          subject=subject, template=temp, attachments=attachFileNames)
        send(mail_msg=msg, mail_server=server)

        ## delete downloaded files
        os.remove(templateFileName)
        for name in attachFileNames:
            if (os.path.exists(name)):
                os.remove(name)
        os.rmdir(prefix)
        return json.dumps({"success": "sent email to " + Reply_to})

## Get file list of google drive
@app.route('/fileList')
def fileList():
    # Setup the Drive v3 API
    service = getConnection()
    # Call the Drive v3 API
    results = service.files().list(
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        return "File Not Found"
    else:
        return json.dumps({'lists': items})

@app.route('/restApi', methods=['POST'])
def uploads():
    if request.method=='POST':
        if 'msg[Reply_to]' in request.form:
            Reply_to = request.form['msg[Reply_to]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[Reply_to]'"})

        if 'msg[To]' in request.form:
            To = request.form['msg[To]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[To]'"})

        if 'subject' in request.form:
            subject = request.form['subject']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'subject'"})

        if 'address' in request.form:
            address = request.form['address']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'address'"})

        if 'price' in request.form:
            price = request.form['price']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'price'"})

        if 'name' in request.form:
            name = request.form['name']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'name'"})

        prefix = path + "/uploads/" + str(int(round(time.time() * 1000)))
        if not os.path.exists(prefix):
            os.makedirs(prefix)

        if 'template' not in request.files:
            return json.dumps({"error": "No template found!"})
        else:
            uploadfile = request.files.getlist("template")
            for file in uploadfile:
                templateName = os.path.join(prefix + "/",secure_filename(file.filename))
                file.save(templateName)

        uploadFileNames = []
        if 'attachFiles' not in request.files:
            print('no file')
        else:
            uploadsFiles = request.files.getlist("attachFiles")
            for file in uploadsFiles:
                fileName = os.path.join(prefix + "/",secure_filename(file.filename))
                uploadFileNames.append(fileName)
                file.save(fileName)
        values = {}
        temp = EmailTemplate(template_name= templateName, values=values)
        server = MailServer(server_name='smtp.office365.com', username='nina@la-retrofit.com',
                            password='Test123456789@',
                            port=587, require_starttls=True)
        msg = MailMessage(from_email='nina@la-retrofit.com', to_emails=[Reply_to],
                          subject=subject, template=temp, attachments=uploadFileNames)
        send(mail_msg=msg, mail_server=server)

        ## delete downloaded files
        os.remove(templateName)
        for name in uploadFileNames:
            if (os.path.exists(name)):
                os.remove(name)
        os.rmdir(prefix)
        return json.dumps({"success": "sent email to " + Reply_to})

@app.route('/main', methods=['POST'])
def main():
    if request.method == 'POST':
        image_path = request.form['image_path']
        access_token = 'AIzaSyBOgXvKISPeCZMgBWbneBsslFZ1jv9h-T8'
        base64_image = base64.b64encode(rp.get(image_path).content)
        service = Service('vision', 'v1', access_token=access_token)
        body = {
            'requests': [{
                'image': {
                    'content': base64_image,
                },
                'features': [{
                    'type': 'TEXT_DETECTION',
                    'maxResults': 1,
                }]
            }]
        }
        response = service.execute(body=body)
        res = response['responses'][0]['textAnnotations']
        json_data = json.dumps({'res': res[0]})
        return json_data
    return None

if __name__ == '__main__':
    app.run()


