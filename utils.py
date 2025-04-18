import os
from langchain_community.document_loaders import PyPDFLoader,Docx2txtLoader
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64


class AuthenticatorandExtractor:
    def __init__(self):
        self.SCOPES = ["https://www.googleapis.com/auth/gmail.readonly","https://www.googleapis.com/auth/gmail.send"]

    def authenticate_gmail(self):
        creds = None

        if os.path.exists('gmail_token.pickle'):
            with open('gmail_token.pickle','rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    r'C:\Users\SHIVAM GHUGE\Downloads\ElintAI Assignment\credentials.json',
                    scopes=self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open('gmail_token.pikle','wb') as token:
                pickle.dump(creds,token)

        return creds
    
    def fetch_resumes(self):
        creds = self.authenticate_gmail()
        service = build('gmail','v1',credentials=creds)
        # Search for emails with attachments
        results = service.users().messages().list(userId='me', q="is:unread has:attachment").execute()
        messages = results.get('messages', [])

        # Create a directory to save resumes
        if not os.path.exists("resumes"):
            os.makedirs("resumes")

        print(f"Found {len(messages)} emails with attachments. Fetching resumes...")

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg['payload']
            # headers = payload.get('headers', [])
            # subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
            parts = payload.get('parts', [])

            for part in parts:
                if part['filename'] and part['filename'].endswith(('.pdf','.docx')):
                    attachment_id = part['body']['attachmentId']
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=message['id'], id=attachment_id
                    ).execute()
                    data = base64.urlsafe_b64decode(attachment['data'])
                    filepath = os.path.join("resumes", re.sub(r'[^\w\-_\. ]', '_', part['filename']))
                    with open(filepath, 'wb') as f:
                        f.write(data)
                    print(f"Saved: {filepath}")
    
        return creds
    

class ResumeParser:
    def __init__(self,file_path):
        self.file_path = file_path

    def resume_content_extractor(self):
        extension = os.path.splitext(self.file_path)[-1]

        if extension == '.pdf':
            loader = PyPDFLoader(file_path=self.file_path)
            content = loader.load()
            content = content[0].page_content
        elif extension == '.docx':
            loader = Docx2txtLoader(file_path=self.file_path)
            content = loader.load()
            content = content[0].page_content
        else:
            return 'unsupported'

        return content
    

class MailHandler:
    def __init__(self,creds):
        self.creds = creds

    def extract_mail(self):
        pattern = r"\S+@\S+"

        email_regex = re.compile(pattern)

        # Find all instances of the pattern in the text
        email = email_regex.findall(self.resume_content)

        if len(email) == 0:
            return 'no email found'

        return email[0]
    
    def send_mail(self,sender_mail,receiver_mail,subject,content):
        mail_service = build('gmail', 'v1', credentials=self.creds)

        msg = MIMEMultipart()

        msg['To'] = receiver_mail
        msg['From'] = sender_mail
        msg['Subject'] = subject

        body = msg.attach(MIMEText(content))

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        body = {'raw':raw_message}

        message = mail_service.users().messages().send(userId='me',body=body).execute()
        print(f"Email sent successfully! Message ID: {message['id']}")
