import os
import google.generativeai as genai

word = input("Enter a word: ")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(f"Your job is to create a JSON object about the supplied word: {word}. This JSON object represents an entry in a dictionary. This entry should include the word itself and the definition as well as synonyms, antonyms and examples of how to use the word. Please provide a valid raw JSON object as the output without any preamble or formatting before the object. The JSON object should be in a similar format to this: {{'word': 'example', 'definition': 'a representative form or pattern', 'synonyms': ['instance', 'case'], 'antonyms': ['counterexample'], 'examples': ['This is an example of how to use the word.']}}")

response_text = response.text
# Remove markdown code block formatting
if response_text.startswith('```json'):
    response_text = response_text.replace('```json', '').replace('```', '').strip()

print(response_text)