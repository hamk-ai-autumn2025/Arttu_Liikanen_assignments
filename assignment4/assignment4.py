import argparse
import sys
import requests
import csv
import docx
import PyPDF2
import os
import openai

def call_llm(text, prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{prompt}\n{text}"}
        ]
    )
    return response.choices[0].message.content

def read_text_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def read_url(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

def read_csv_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        return '\n'.join([', '.join(row) for row in reader])

def read_docx_file(path):
    doc = docx.Document(path)
    return '\n'.join([para.text for para in doc.paragraphs])

def read_pdf_file(path):
    text = ""
    with open(path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def get_source_text(source):
    if source.lower().startswith('http://') or source.lower().startswith('https://'):
        return read_url(source)
    elif source.lower().endswith('.txt'):
        return read_text_file(source)
    elif source.lower().endswith('.csv'):
        return read_csv_file(source)
    elif source.lower().endswith('.docx'):
        return read_docx_file(source)
    elif source.lower().endswith('.pdf'):
        return read_pdf_file(source)
    else:
        raise ValueError(f"Unsupported source type: {source}")

def main():
    parser = argparse.ArgumentParser(description="Feed input from files or URLs to LLM.")
    parser.add_argument('sources', nargs='*', help='Input sources: file paths or URLs')
    parser.add_argument('--prompt', type=str, default='Summarize the following content.', help='Prompt/query for the LLM')
    parser.add_argument('--output', type=str, help='Output file (default: stdout)')
    args = parser.parse_args()

    if not args.sources:
        print("Error: No input sources provided.", file=sys.stderr)
        sys.exit(1)

    all_text = ""
    for src in args.sources:
        try:
            all_text += get_source_text(src) + "\n"
        except Exception as e:
            print(f"Error reading {src}: {e}", file=sys.stderr)

    try:
        result = call_llm(all_text, args.prompt)
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        print(result)

if __name__ == '__main__':
    main()