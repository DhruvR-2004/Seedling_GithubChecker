import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file
import json
import requests
import uvicorn
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- CONFIGURATION ---
# --- CONFIGURATION ---
# Load API Key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file") 
GITHUB_TOKEN = None

genai.configure(api_key=GEMINI_API_KEY)

# --- HELPER FUNCTIONS ---

def fetch_github_data(repo_url: str, issue_number: int, page: int = 1):
    """
    Fetches the specific issue AND a paginated list of recent issues.
    """
    try:
        parts = repo_url.rstrip("/").split("/")
        owner, repo = parts[-2], parts[-1]
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        # 1. Fetch Specific Issue (The one being analyzed)
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        issue_res = requests.get(issue_url, headers=headers)
        
        # 2. Fetch Comments
        comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
        comments_res = requests.get(comments_url, headers=headers)

        # 3. PAGINATION: Fetch Recent Issues with page parameter
        # We fetch 30 issues per page
        issues_list_url = f"https://api.github.com/repos/{owner}/{repo}/issues?per_page=30&state=all&sort=updated&page={page}"
        issues_list_res = requests.get(issues_list_url, headers=headers)

        if issue_res.status_code != 200:
            return None, f"Error fetching issue: {issue_res.status_code}"

        issue_data = issue_res.json()
        comments_data = comments_res.json() if comments_res.status_code == 200 else []
        issues_list_data = issues_list_res.json() if issues_list_res.status_code == 200 else []

        # Combine text for the AI
        full_text = f"Title: {issue_data.get('title')}\n\nBody:\n{issue_data.get('body')}\n\n"
        for comment in comments_data:
            full_text += f"Comment: {comment.get('body')}\n"

        return {
            "owner": owner,
            "repo": repo,
            "issue_title": issue_data.get("title"),
            "full_text": full_text,
            "issues_list": issues_list_data,
            "current_page": page  # Pass the page number back to the UI
        }, None

    except Exception as e:
        return None, str(e)

def analyze_with_gemini(issue_text):
    target_model_name = 'gemini-2.5-flash'
    fallback_model_name = 'gemini-2.0-flash'
    
    prompt = f"""
    You are an expert Engineering Manager. Analyze the following GitHub issue and return ONLY a JSON object.
    
    Format requirements:
    {{
        "summary": "One sentence summary",
        "type": "bug" | "feature_request" | "documentation" | "question" | "other",
        "priority_score": 1-5 (int),
        "suggested_labels": ["label1", "label2"],
        "potential_impact": "Short sentence on user impact"
    }}

    Issue Data:
    {issue_text}
    """
    
    try:
        model = genai.GenerativeModel(target_model_name)
        response = model.generate_content(prompt)
    except Exception as e:
        print(f"Error using {target_model_name}: {e}")
        # Try fallback
        try:
            print(f"Retrying with fallback model: {fallback_model_name}")
            model = genai.GenerativeModel(fallback_model_name)
            response = model.generate_content(prompt)
        except Exception as fallback_e:
             # If both fail, list models for debug
             available_models = []
             try:
                 for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
             except:
                pass
             return json.dumps({
                 "error": f"Model {target_model_name} failed. Fallback {fallback_model_name} also failed. Available models: {available_models}. Error: {str(fallback_e)}"
             })

    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return clean_text
    except Exception as e:
         return json.dumps({"error": f"AI Parsing failed: {str(e)}"})

# --- SHARED LOGIC ---

async def render_dashboard(request: Request, repo_url: str, issue_number: int, page: int):
    # 1. Fetch Data with Page
    data, error = fetch_github_data(repo_url, issue_number, page)
    
    if error:
        return templates.TemplateResponse("index.html", {"request": request, "error": f"Could not find issue: {error}"})

    # 2. AI Analysis
    ai_response_json = analyze_with_gemini(data["full_text"])
    
    safe_analysis = {
        "summary": "AI could not analyze this issue.",
        "type": "other",
        "priority_score": 0,
        "suggested_labels": ["error"],
        "potential_impact": "Unknown"
    }

    try:
        parsed_data = json.loads(ai_response_json)
        if "error" in parsed_data:
            safe_analysis["summary"] = f"AI Error: {parsed_data['error']}"
        else:
            safe_analysis.update(parsed_data)
    except Exception as e:
        safe_analysis["summary"] = f"Error parsing AI response: {str(e)}"

    # 3. Render Dashboard
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "repo_url": repo_url, 
        "repo_name": f"{data['owner']}/{data['repo']}",
        "issue_number": issue_number,
        "issue_title": data['issue_title'],
        "issues_list": data['issues_list'],
        "analysis": safe_analysis,
        "page": page # Sending page number to template
    })

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_post(request: Request, repo_url: str = Form(...), issue_number: int = Form(...)):
    # Default to page 1 on new form submission
    return await render_dashboard(request, repo_url, issue_number, page=1)

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_get(request: Request, repo_url: str = Query(...), issue_number: int = Query(...), page: int = Query(1)):
    # Accept page param from link clicks
    return await render_dashboard(request, repo_url, issue_number, page)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)