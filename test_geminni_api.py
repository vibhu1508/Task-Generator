import os
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai
import json

load_dotenv(find_dotenv())

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found in environment variables.")
    exit()

try:
    genai.configure(api_key=api_key)

    models_to_test = ["gemini-1.5-flash", "gemini-2.5-flash"]

    for model_name in models_to_test:
        print(f"\n--- Testing Model: {model_name} ---")
        model = genai.GenerativeModel(model_name)

        test_prompt = f"List 5 popular Python libraries for web development."

        try:
            response = model.generate_content(test_prompt)
            output = response.text.strip()

            print("Success!")
            try:
                json_output = json.loads(output)
                print(json.dumps(json_output, indent=2))
            except:
                print(output[:1000])

        except Exception as e:
            print(f"Failed to generate response from {model_name}: {e}")

except Exception as config_error:
    print(f"Configuration error: {config_error}")
