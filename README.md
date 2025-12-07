IssuePilot AI

I built IssuePilot because I wanted a faster way to understand what is happening in GitHub issue threads without reading every single comment. It is basically an AI assistant that acts like a product manager for your code repositories.

You can try the live demo here: https://seedling-githubchecker.onrender.com/


The home screen looks like this:
![image alt](https://github.com/DhruvR-2004/Seedling_GithubChecker/blob/7411e5edf597b5ed9259fb2d4fa854dec942181d/demo.png)   


What it actually does

The main goal of this tool is to save time on triage.

* It reads the issue title, body, and all the comments.
* It uses Google Gemini (2.5 Flash)(Fallback Model: 2.0 Flash) to figure out what is actually wrong and writes a one-sentence summary.
* It guesses the priority (1 to 5) and the type of issue (bug, feature, etc.) so you know what to focus on.
* It suggests labels to help organize the repo.
* I spent some extra time on the UI to make it look like a Dark Mode version of GitHub, including a sidebar that lets you browse other issues in the repo without leaving the page.

Tech Stack

* Backend: Python with FastAPI. I chose this because it is fast and easy to set up.
* AI Model: Google Gemini 2.5 Flash. It handles long context windows well, which is important for long issue threads.
* Frontend: Standard HTML and CSS with Jinja2 templates. No heavy frameworks like React, just simple server-side rendering.
* Deployment: Hosted on Render.

How to run it locally

If you want to run the code yourself instead of using the website:

1. Clone the repository
   git clone https://github.com/YOUR_USERNAME/issue-pilot-ai.git
   cd issue-pilot-ai

2. Set up a virtual environment
   python -m venv venv
   
   # For Windows:
   venv\Scripts\activate
   
   # For Mac/Linux:
   source venv/bin/activate

3. Install the libraries
   pip install -r requirements.txt

4. Set up your API Key
   You will need a Google Gemini API key. You can set it in a .env file or just export it in your terminal:
   
   export GEMINI_API_KEY="your_key_here"

5. Start the server
   uvicorn main:app --reload

Then just open http://127.0.0.1:8000 in your browser.

How it works under the hood

When you paste a link and click Analyze:

1. The app uses the GitHub API to fetch the issue text and comments.
2. It sends that text to Gemini with a specific prompt. I used a technique called Few-Shot Prompting (giving the AI examples of good answers) to make sure it always returns clean JSON data.
3. The backend parses that JSON and renders the dashboard.
4. At the same time, it fetches a list of other recent issues so you can navigate through the repo in the sidebar.

License

MIT License.
