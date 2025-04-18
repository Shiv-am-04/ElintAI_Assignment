from utils import AuthenticatorandExtractor,ResumeParser,MailHandler
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from crewai import Agent,Task,Crew
import logging
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# logging configuration
logger = logging.getLogger('resume_feedback')
logger.setLevel('DEBUG')

console_handler = logging.StreamHandler()
console_handler.setLevel('DEBUG')

log_file_path = os.path.join(log_dir, 'resume_feedback.log')
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel('DEBUG')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

groq_api_key = os.getenv('GROQ_API_KEY')


auth_object = AuthenticatorandExtractor()

credentials = auth_object.fetch_resumes()

mail_object = MailHandler(creds=credentials)

llm = ChatGroq(model='groq/qwen-qwq-32b',api_key=groq_api_key,temperature=0.6)


def load_prompt(resume_content:str):
    prompt = f'''
            You are a highly skilled resume analyst with extensive experience in evaluating resumes for various industries.
            You have a keen eye for detail and a deep understanding of what makes a resume stand out, including the analysis
            of work experience, education, skills, years of experience, relevant keywords, formatting, and clarity.
            Your task is to analyze a resume and provide a comprehensive evaluation. Here is the {resume_content} to be analyzed
            Please rate the resume out of 100 and provide a detailed breakdown of the score components.
            Include any notable feedback, mentioning both strengths and weaknesses, to help improve the overall quality of the resume.
            '''
    return prompt

def create_agent(model):
    analyzer_agent = Agent(
        role="Resume Evaluation Expert",
        goal="Score resumes and provide feedback to improve them",
        backstory="You are a seasoned recruiter who provides fair and insightful resume reviews",
        llm=model,  # Groq, OpenAI, or Anthropic client
        )

    return analyzer_agent

def create_crew(agent,resume_content):
    analyze_task = Task(
        description=load_prompt(resume_content),
        agent=agent,
        expected_output='breakdown of the score components,include any notable feedback, mentioning both strengths and weaknesses, to help improve the overall quality of the resume.'
    )

    crew = Crew(
        agents=[agent],
        tasks=[analyze_task]
    )

    return crew

# Create agent once
analyzer_agent = create_agent(model=llm)


sender_mail = input('provide the mail of sender, make sure it should be same as authenticated earlier')
if sender_mail:
    logger.debug('input received')

# Process each resume with the same agent
def process_resume_and_send_mail(resume_path):
    try:
        analyzer = ResumeParser(resume_path)
        content = analyzer.resume_content_extractor()
        logger.debug('resume parsed successfully')
    except Exception as e:
        logger.error(f'{e} : failed to parse the resume')
    
    try:
        crew = create_crew(agent=analyzer_agent,resume_content=content)
        result = crew.kickoff()
        print(result)
    except Exception as e:
        logger.error(f'{e} : something occured while initializing agent or crew')
    
    mail = mail_object.extract_mail()

    if mail:
        mail_object.send_mail(sender_mail=sender_mail,
                          receiver_mail=mail,
                          subject='Resume Evaluation Feedback',
                          content=result)
        logger.debug(f'mail sent to {mail}')
    
    else:
        logger.error('mail not extracted !')
        
# put your own directory path
directory = r'C:\Users\SHIVAM GHUGE\Downloads\ElintAI Assignment\resumes'
resume_paths = [os.path.join(directory,file_name) for file_name in os.listdir('resumes')]

with ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(process_resume_and_send_mail,resume_paths)
