import os
import datetime
from google.generativeai import GenerativeModel
import google.generativeai as genai
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --- CONFIGURATION ---
# Your extracted Google Doc ID: 1_NzJj5qisdbWigMdc53kt9ddjs7z4XwQdaG2UzCdQWs
DOCUMENT_ID = os.environ.get("GDOC_ID", "1_NzJj5qisdbWigMdc53kt9ddjs7z4XwQdaG2UzCdQWs") 
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPO") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = GenerativeModel('gemini-2.5-flash-preview-09-2025')

def get_gdoc_content(doc_id):
    """
    Fetches text content from the specified Google Doc.
    Requires 'service_account.json' in the same directory.
    """
    try:
        creds = service_account.Credentials.from_service_account_file('service_account.json')
        service = build('docs', 'v1', credentials=creds)
        doc = service.documents().get(documentId=doc_id).execute()
        
        content = ""
        for element in doc.get('body').get('content'):
            if 'paragraph' in element:
                for run in element.get('paragraph').get('elements'):
                    content += run.get('textRun', {}).get('content', '')
        return content
    except Exception as e:
        print(f"Error accessing Google Doc: {e}")
        return None

def generate_qa(text):
    """
    Uses Gemini to transform raw judgment notes into a structured Q&A Markdown format.
    """
    prompt = f"""
    You are an expert legal researcher specializing in Indian Supreme Court (SC) judgments. 
    Below are my daily notes from a Google Doc. 
    Please transform them into a professional Question and Answer format.
    
    Requirements:
    1. Case Identification: Clearly state the 'Case Name' and 'Citation' (if available).
    2. Legal Issues: Formulate questions based on the core legal issues or the ratio decidendi.
    3. Comprehensive Answers: Provide detailed answers based on the notes provided.
    4. Markdown Structure: Use H3 headers (###) for cases and blockquotes or lists for Q&A.
    
    Notes to process:
    {text}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating Q&A: {e}")
        return None

def update_github_file(content):
    """
    Appends the daily digest to the QA.md file.
    Note: For GitHub Actions, ensure the git user is configured.
    """
    if not content:
        return

    today = datetime.date.today().strftime("%B %d, %Y")
    divider = "\n\n---\n\n"
    header = f"## Daily Digest - {today}\n\n"
    final_output = divider + header + content
    
    # Appends to the local QA.md which will be committed by the CI/CD workflow
    try:
        with open("QA.md", "a", encoding="utf-8") as f:
            f.write(final_output)
        print(f"Successfully updated QA.md for {today}.")
    except Exception as e:
        print(f"Error writing to file: {e}")

def main():
    print("🚀 Starting Daily SC Digest Processing...")
    
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    # 1. Fetch
    raw_text = get_gdoc_content(DOCUMENT_ID)
    if not raw_text or len(raw_text.strip()) == 0:
        print("⚠️ No content found in the Google Doc.")
        return
    print(f"✅ Fetched content from Doc ID: {DOCUMENT_ID}")
    
    # 2. Process
    qa_markdown = generate_qa(raw_text)
    if qa_markdown:
        print("✅ Q&A generated via Gemini.")
        
        # 3. Save
        update_github_file(qa_markdown)
        print("🎊 Process complete!")
    else:
        print("❌ Failed to generate Q&A.")

if __name__ == "__main__":
    main()
