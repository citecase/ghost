import os
import datetime
import requests
import google.generativeai as genai

# --- CONFIGURATION ---
DOCUMENT_ID = os.environ.get("GDOC_ID", "1_NzJj5qisdbWigMdc53kt9ddjs7z4XwQdaG2UzCdQWs") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini with a strong System Instruction
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a highly skilled legal analyst specializing in Indian Supreme Court judgments. 
Your task is to take raw notes and transform them into a structured Q&A format.

For every judgment found in the text:
1. Create a clear heading for the Case Name.
2. Formulate 2-3 specific Questions about the legal principles or facts discussed.
3. Provide concise, accurate Answers based on the notes.
4. If the notes are brief, expand on the 'Ratio Decidendi' (the rule of law on which the decision is based).

FORMAT:
### [Case Name]
**Question:** [Specific legal question]
**Answer:** [Detailed explanation]
"""

def get_public_gdoc_content(doc_id):
    """Fetches text content from a PUBLIC Google Doc."""
    # Method 1: Export link
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        text = response.text.strip()
        if len(text) > 10:
            return text
    except Exception as e:
        print(f"Export method failed: {e}")
    
    return None

def generate_qa(text):
    """Uses Gemini to transform notes into Q&A."""
    # Using the latest 09-2025 preview model
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash-preview-09-2025',
        system_instruction=SYSTEM_PROMPT
    )
    
    try:
        # We send the text as the user prompt
        response = model.generate_content(f"Please process these notes into Q&A:\n\n{text}")
        return response.text
    except Exception as e:
        print(f"Error during AI generation: {e}")
        return None

def update_github_file(content):
    """Appends to the QA.md file."""
    if not content:
        return

    today = datetime.date.today().strftime("%B %d, %Y")
    entry = f"\n\n---\n## Updates for {today}\n\n{content}\n"
    
    try:
        with open("QA.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"Successfully updated local QA.md.")
    except Exception as e:
        print(f"File Error: {e}")

def main():
    print("--- SC Digest Processor Start ---")
    
    if not GEMINI_API_KEY:
        print("Error: Set the GEMINI_API_KEY environment variable.")
        return

    # 1. Fetching
    raw_text = get_public_gdoc_content(DOCUMENT_ID)
    if not raw_text:
        print("Error: Could not retrieve text. Is the Doc public (Anyone with link can view)?")
        return
    
    print(f"Fetched {len(raw_text)} characters from Google Doc.")
    
    # 2. Processing
    print("Sending to Gemini for Q&A generation...")
    qa_markdown = generate_qa(raw_text)
    
    if qa_markdown and len(qa_markdown.strip()) > 5:
        print("Generation successful.")
        # 3. Saving
        update_github_file(qa_markdown)
        print("Process Finished.")
    else:
        print("AI returned empty results. Check if the notes are too short or formatted oddly.")

if __name__ == "__main__":
    main()
