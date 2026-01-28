import os
import datetime
import requests
import re
import google.generativeai as genai

# --- CONFIGURATION ---
DOCUMENT_ID = os.environ.get("GDOC_ID", "1_NzJj5qisdbWigMdc53kt9ddjs7z4XwQdaG2UzCdQWs") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a highly skilled legal analyst specializing in Indian Supreme Court judgments. 
Your task is to take raw notes and transform them into a specific Q&A format.

The input text provided to you contains case names followed by their original source URLs in brackets, like this: "Case Name [URL]".

For every judgment found in the text:
1. Identify the specific legal questions or issues addressed.
2. Provide the "Answer" as ONLY the original Judgment/Case Name.
3. CRITICAL: Hyperlink that Case Name using the EXACT URL provided in the brackets next to it in the input.

FORMAT:
**Question:** [The legal question]
**Answer:** [[Case Name]]([Exact URL from notes])
"""

def get_public_gdoc_with_links(doc_id):
    """
    Fetches a PUBLIC Google Doc as HTML to preserve hyperlinks.
    Converts HTML links into a format Gemini can understand: 'Text [URL]'
    """
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text

        # Regex to find <a href="URL">Text</a> and convert to "Text [URL]"
        # This allows Gemini to see the links that were previously hidden in the text export.
        processed_text = re.sub(
            r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', 
            r'\2 [\1]', 
            html_content
        )
        
        # Strip remaining HTML tags to leave clean text + bracketed links
        clean_text = re.sub(r'<[^>]+>', ' ', processed_text)
        # Clean up whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    except Exception as e:
        print(f"Error fetching HTML from Google Doc: {e}")
        return None

def generate_qa(text_with_links):
    """Uses Gemini to transform notes into the hyperlinked Q&A format."""
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash-preview-09-2025',
        system_instruction=SYSTEM_PROMPT
    )
    
    try:
        # We explicitly tell the model to look at the bracketed URLs
        prompt = (
            "Below are my judgment notes. Links are provided in brackets [URL] immediately after the text they belong to. "
            "Please generate the Q&A using these links for the answers:\n\n" + text_with_links
        )
        response = model.generate_content(prompt)
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
        print(f"Successfully updated local QA.md with hyperlinked cases.")
    except Exception as e:
        print(f"File Error: {e}")

def main():
    print("--- SC Digest Processor Start (Link-Aware Edition) ---")
    
    if not GEMINI_API_KEY:
        print("Error: Set the GEMINI_API_KEY environment variable.")
        return

    # 1. Fetching (Using HTML export to keep links)
    raw_text = get_public_gdoc_with_links(DOCUMENT_ID)
    if not raw_text or len(raw_text) < 50:
        print("Error: Could not retrieve sufficient text. Check if Doc is public.")
        return
    
    print(f"Successfully extracted text and links from Google Doc.")
    
    # 2. Processing
    print("Generating Questions and extracting original hyperlinks...")
    qa_markdown = generate_qa(raw_text)
    
    if qa_markdown and len(qa_markdown.strip()) > 5:
        print("Generation successful.")
        # 3. Saving
        update_github_file(qa_markdown)
        print("Process Finished.")
    else:
        print("AI failed to generate content or find links.")

if __name__ == "__main__":
    main()
