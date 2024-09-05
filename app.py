from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup
from uuid import uuid4
import html
import requests
import json
from dotenv import load_dotenv
import os
import markdown2

load_dotenv()  # Add this near the top of your file

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chats.db'
db = SQLAlchemy(app)

# Add these lines to get your API keys
GPT4_API_KEY = os.getenv('GPT4_API_KEY')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

class Chat(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    query = db.Column(db.Text)
    gpt4_response = db.Column(db.Text)
    claude_response = db.Column(db.Text)
    google_response = db.Column(db.Text)
    gpt4_optimised = db.Column(db.Text)
    claude_optimised = db.Column(db.Text)
    google_optimised = db.Column(db.Text)
    final_response = db.Column(db.Text)
    gpt4_votes = db.Column(db.Integer)
    claude_votes = db.Column(db.Integer)
    google_votes = db.Column(db.Integer)
    gpt4_comparison = db.Column(db.Text)
    claude_comparison = db.Column(db.Text)
    google_comparison = db.Column(db.Text)

@app.route('/')
def home():
    chat_id = str(uuid4())
    return redirect(url_for('chat', chat_id=chat_id))

@app.route('/basic/')
def home_basic():
    chat_id = str(uuid4())
    return redirect(url_for('chat', chat_id=chat_id))

@app.route('/optimise/')
def home_optimise():
    chat_id = str(uuid4())
    return redirect(url_for('optimise_chat', chat_id=chat_id))

@app.route('/basic/<chat_id>', methods=['GET', 'POST'])
def chat(chat_id):
    chat = db.session.get(Chat, chat_id)

    if request.method == 'POST' and not chat:
        query = html.escape(request.form['query'])
        chat = Chat(id=chat_id, query=query)
        db.session.add(chat)
        
        # Call LLM APIs and store responses
        chat.gpt4_response = call_gpt4_api(query)
        chat.claude_response = call_claude_api(query)
        chat.google_response = call_google_api(query)

        # Create comparison prompt
        comparison_prompt = f"""
        Original query: {query}
        
        Potential answers:
        1: {chat.gpt4_response}
        2: {chat.claude_response}
        3: {chat.google_response}
        
        Please pick which answer you believe is best and most accurate, and also choose a second best.
        """

        # Get comparisons from LLMs and store them
        chat.gpt4_comparison = call_gpt4_api(comparison_prompt, is_comparison=True)
        chat.claude_comparison = call_claude_api(comparison_prompt, is_comparison=True)
        chat.google_comparison = call_google_api(comparison_prompt, is_comparison=True)

        # Determine final response
        chat.final_response = determine_final_response(chat, chat.gpt4_response, chat.claude_response, chat.google_response, chat.gpt4_comparison, chat.claude_comparison, chat.google_comparison)

        db.session.commit()

    if chat and chat.final_response:
        return render_template('chat.html', chat_id=chat_id, query=chat.query, 
                               response=convert_markdown_to_html(chat.final_response),
                               gpt4_response=convert_markdown_to_html(chat.gpt4_response),
                               claude_response=convert_markdown_to_html(chat.claude_response),
                               google_response=convert_markdown_to_html(chat.google_response),
                               gpt4_votes=chat.gpt4_votes,
                               claude_votes=chat.claude_votes,
                               google_votes=chat.google_votes,
                               gpt4_comparison=chat.gpt4_comparison,
                               claude_comparison=chat.claude_comparison,
                               google_comparison=chat.google_comparison)

    return render_template('chat.html', chat_id=chat_id)

@app.route('/optimise/<chat_id>', methods=['GET', 'POST'])
def optimise_chat(chat_id):
    chat = db.session.get(Chat, chat_id)

    if request.method == 'POST' and not chat:
        query = html.escape(request.form['query'])
        chat = Chat(id=chat_id, query=query)
        db.session.add(chat)
        
        # Call LLM APIs and store initial responses
        chat.gpt4_response = call_gpt4_api(query)
        chat.claude_response = call_claude_api(query)
        chat.google_response = call_google_api(query)

        # Create optimisation prompt
        optimisation_prompt = f"""
        Original query: {query}

        Here are three AI-generated responses to this query:

        1:
        {chat.gpt4_response}

        2:
        {chat.claude_response}

        3:
        {chat.google_response}

        Please review these responses to this question, correct any errors you find, and provide an optimised output based ONLY on the information from all three responses. Ensure your response is comprehensive, accurate, and well-structured and that it does not mention that it is an optimised response; it should just appear to be the best answer to the question.
        """

        # Get optimised responses from LLMs
        chat.gpt4_optimised = call_gpt4_api(optimisation_prompt)
        chat.claude_optimised = call_claude_api(optimisation_prompt)
        chat.google_optimised = call_google_api(optimisation_prompt)

        # Create comparison prompt for optimised responses
        comparison_prompt = f"""
        Original query: {query}
        
        Optimised answers:
        1: {chat.gpt4_optimised}
        2: {chat.claude_optimised}
        3: {chat.google_optimised}
        
        Please pick which answer you believe is best and most accurate, and also choose a second best.
        """

        # Get comparisons from LLMs and store them
        chat.gpt4_comparison = call_gpt4_api(comparison_prompt, is_comparison=True)
        chat.claude_comparison = call_claude_api(comparison_prompt, is_comparison=True)
        chat.google_comparison = call_google_api(comparison_prompt, is_comparison=True)

        # Determine final response
        chat.final_response = determine_final_response(chat, chat.gpt4_optimised, chat.claude_optimised, chat.google_optimised, chat.gpt4_comparison, chat.claude_comparison, chat.google_comparison)

        db.session.commit()

    if chat and chat.final_response:
        return render_template('optimise_chat.html', chat_id=chat_id, query=chat.query, 
                               response=convert_markdown_to_html(chat.final_response),
                               gpt4_response=convert_markdown_to_html(chat.gpt4_optimised),
                               claude_response=convert_markdown_to_html(chat.claude_optimised),
                               google_response=convert_markdown_to_html(chat.google_optimised),
                               gpt4_original_response=convert_markdown_to_html(chat.gpt4_response),
                               claude_original_response=convert_markdown_to_html(chat.claude_response),
                               google_original_response=convert_markdown_to_html(chat.google_response),
                               gpt4_votes=chat.gpt4_votes,
                               claude_votes=chat.claude_votes,
                               google_votes=chat.google_votes,
                               gpt4_comparison=chat.gpt4_comparison,
                               claude_comparison=chat.claude_comparison,
                               google_comparison=chat.google_comparison)

    return render_template('optimise_chat.html', chat_id=chat_id)

def call_gpt4_api(prompt, is_comparison=False):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GPT4_API_KEY}"
    }
    messages = [{"role": "user", "content": prompt}]
    if is_comparison:
        messages.insert(0, {"role": "system", "content": "You must only respond with JSON (with no markup) in the format { \"primary_vote\": 1, \"secondary_vote\": 2 }"})
    data = {
        "model": "gpt-4o",
        "messages": messages
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

def call_claude_api(prompt, is_comparison=False):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    messages = [{"role": "user", "content": prompt}]
    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1024,
        "messages": messages
    }
    if is_comparison:
        data["system"] = "You must only respond with JSON (with no markup) in the format { \"primary_vote\": 1, \"secondary_vote\": 2 }"
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['content'][0]['text']
    else:
        return f"Error: {response.status_code}, {response.text}"

def call_google_api(prompt, is_comparison=False):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": [{"parts": [{"text": prompt}]}]}
    if is_comparison:
        data["systemInstruction"] = {
            "role": "system",
            "parts": [
                {"text": "You must only respond with JSON (with no markup) in the format { \"primary_vote\": 1, \"secondary_vote\": 2 }"}
            ]
        }
    params = {
        "key": GOOGLE_API_KEY
    }
    response = requests.post(url, headers=headers, json=data, params=params)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"Error: {response.status_code}, {response.text}"

def determine_final_response(chat, gpt4_response, claude_response, google_response, gpt4_comparison, claude_comparison, google_comparison):
    primary_votes = {1: 0, 2: 0, 3: 0}
    secondary_votes = {1: 0, 2: 0, 3: 0}
    
    for comparison in [gpt4_comparison, claude_comparison, google_comparison]:
        try:
            result = json.loads(comparison)
            primary_votes[result["primary_vote"]] += 1
            secondary_votes[result["secondary_vote"]] += 1
        except (json.JSONDecodeError, KeyError):
            continue
    
    # Determine the winner based on primary votes first
    max_primary_votes = max(primary_votes.values())
    primary_winners = [k for k, v in primary_votes.items() if v == max_primary_votes]
    
    if len(primary_winners) == 1:
        winner = primary_winners[0]
    else:
        # If there's a tie in primary votes, use secondary votes as a tiebreaker
        winner = max(primary_winners, key=lambda k: secondary_votes[k])
    
    # Set votes for each model (primary votes only)
    chat.gpt4_votes = primary_votes[1]
    chat.claude_votes = primary_votes[2]
    chat.google_votes = primary_votes[3]
    
    if winner == 1:
        return gpt4_response
    elif winner == 2:
        return claude_response
    else:
        return google_response

def convert_markdown_to_html(text):
    return Markup(markdown2.markdown(text))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        db.session.commit()
    app.run(debug=True)