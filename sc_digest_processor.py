import os
import datetime
import requests
import google.generativeai as genai

# --- CONFIGURATION ---
DOCUMENT_ID = os.environ.get("GDOC_ID", "1_NzJj5qisdbWigMdc53kt9ddjs7z4XwQdaG2UzCdQWs") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini with a specific System Instruction for Question-only output
genai.configure(api_key=GEMINI_API_KEY)

# Refined prompt to meet the "Questions only, Answer is Case Name + original link" requirement
SYSTEM_PROMPT = """
You are a highly skilled legal analyst specializing in Indian Supreme Court judgments. 
Your task is to take raw notes and transform them into a specific Q&A format.

The input text contains case notes where case names are often associated with external URLs (e.g., LiveLaw, Bar and Bench, or SC website links).

For every judgment found in the text:
1. Identify the specific legal questions or issues addressed in the judgment.
2. Provide the "Answer" as ONLY the original Judgment/Case Name.
3. Hyperlink that Case Name using the specific URL associated with that case in the provided notes. If no specific URL is found for a case, do not hyperlink it.

FORMAT:
**Question:** [The legal question]
**Answer:** [[Case Name]](https://apps.apple.com/us/app/notes/id1110145109)
"""

def get_public_gdoc_content(doc_id):
    """Fetches text content from a PUBLIC Google Doc."""
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        # Note: Exporting as .txt from Google Docs sometimes loses hyperlink targets 
        # but keeps the text. For advanced link extraction, the Google Docs API is preferred.
        # However, for public docs where links are written out or accessible, this works.
        response = requests.get(url)
        response.raise_for_status()
        text = response.text.strip()
        if len(text) > 10:
            return text
    except Exception as e:
        print(f"Export method failed: {e}")
    
    return None

def generate_qa(text):
    """Uses Gemini to transform notes into the requested format."""
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash-preview-09-2025',
        system_instruction=SYSTEM_PROMPT
    )
    
    try:
        response = model.generate_content(f"Please process these notes into the specific Q&A format, ensuring you use the links found in the text for the case names:\n\n{text}")
        return response.text
    except Exception as e:
        print(f"Error during AI generation: {e}")
        return None

def update_github_file(content):
    """Appends to the QA.md file."""
    if not content:
        return

    today = datetime.date.today().strftime("%B %d, %Y")
    entry = f"\n\n---\n## Daily Questions - {today}\n\n{content}\n"
    
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
        print("Error: Could not retrieve text. Ensure the Doc is public.")
        return
    
    print(f"Fetched {len(raw_text)} characters from Google Doc.")
    
    # 2. Processing
    print("Generating Questions with original hyperlinks...")
    qa_markdown = generate_qa(raw_text)
    
    if qa_markdown and len(qa_markdown.strip()) > 5:
        print("Generation successful.")
        # 3. Saving
        update_github_file(qa_markdown)
        print("Process Finished.")
    else:
        print("AI returned empty results.")

if __name__ == "__main__":
    main()
