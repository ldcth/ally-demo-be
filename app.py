from flask import Flask, request, jsonify
import os
from openai import OpenAI
from flask_cors import CORS
import json
import pandas as pd

app = Flask(__name__)
CORS(app)

XAI_API_KEY = os.getenv('OPENAI_API_KEY')
@app.route('/')
def index():
    return "Hello, World!"

def extract_intent(question):
    prompt = f"""You are an expert in extracting the intent from user questions.
    Check format of the questions and return whether it is plan for a trip or vacation or not.
    Return yes or no, nothing else
    """
    client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1",
    )

    completion = client.chat.completions.create(
        model="grok-beta",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
    )
    # Handle potential null response
    if not completion or not completion.choices or not completion.choices[0].message.content:
        return ""
    return completion.choices[0].message.content 

def extract_requirements(question):
    prompt = f"""You are a tourism expert in extracting the requirements from user questions.
    You must generate the output in a JSON format 
    Check format of the question and extract:
    - Place
    - Date
    - Special interests (if any)
    IMPORTANT NOTES: keeping format of characters in the question, do not hallucinate
    """
    client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1",
    )

    completion = client.chat.completions.create(
        model="grok-beta",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],       
        temperature=0.1,
    )
    # Input string
    data = completion.choices[0].message.content
    # Find the first and last square brackets
    start = data.find("{")
    end = data.rfind("}") + 1

    cleaned_data = ""
    # Extract only the content within the brackets
    if start != -1 and end != -1:
        cleaned_data = data[start:end]

    json_data = json.loads(cleaned_data)
    # json_data = json.dumps(json_data, indent=2, ensure_ascii=False)
    # print(type(json_data))
    return json_data
    # return cleaned_data
def extract_answer(question):
    intent = extract_intent(question)
    if intent == "Yes":
        df = pd.read_csv('./google-maps-businesses-cleaned.csv')
        requirements = extract_requirements(question)
        places = df[df['country'] == requirements['Place']]
        print(len(places))
        if len(places) == 0:
            return "Sorry, I couldn't find any places in that country."
        else:
            # Data
            filtered_df = places[places["rating"] > 4.0]
            print(len(filtered_df))

            if len(filtered_df) < 10:
                return "Sorry, I couldn't find any places in that country."
            else:
                # Randomly select one row per distinct category
                sampled_df = (
                filtered_df.groupby("category")
                .apply(lambda x: x.sample(n=1))  # Randomly pick one row per category
                .reset_index(drop=True)
                )

                # If we want exactly 10 rows
                result = sampled_df.sample(n=10, random_state=42)  # Adjust n if fewer than 10 categories exist
                print(len(result))

                # Prompt
                prompt = f"""You are an expert in recommending place to go based on specific list of places.
                Your task is to build a plan in {requirements['Date']} based on the following list of places:
                {result[['name', 'category', 'address', 'rating']].to_dict('records')}
                IMPORTANT NOTES:\n- Plan must be separated by time (morning, afternoon, evening),
                \n Each value must come with the name of the place, the address, and the rating, no hallucination
                \n Save the plan in a list, each element is a string, the string is the plan for each time
                \n Just return the list, nothing else
                """
                client = OpenAI(
                api_key=XAI_API_KEY,
                    base_url="https://api.x.ai/v1",
                )

                completion = client.chat.completions.create(
                model="grok-beta",
                messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": question},
                    ],       
                    temperature=0.1,
                )
                # Input string
                data = completion.choices[0].message.content
                # Find the first and last square brackets
                start = data.find("[") + 1
                end = data.rfind("]") 

                cleaned_data = ""
                # Extract only the content within the brackets
                if start != -1 and end != -1:
                    cleaned_data = data[start:end]
                # if not completion or not completion.choices or not completion.choices[0].message.content:
                #     return ""
                # return completion.choices[0].message.content 
                return cleaned_data.strip()
    else:
        return question

@app.post("/api/intent")
def get_intent_answer():
    data = request.json
    try:
        # intent = extract_intent(data["content"])
        intent = extract_answer(data["content"])
        # print(type(intent))
        return jsonify({"intent": intent})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.post("/api/answer")
def get_chat_answer():
    data = request.json
    try:
        answer = extract_answer(data["content"])
        # print(type(intent))
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)