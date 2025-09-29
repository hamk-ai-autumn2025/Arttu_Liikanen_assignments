import os
import google.generativeai as genai
from markdown_pdf import MarkdownPdf, Section

topic = input("Enter a topic: ")
print("Generating article...")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(f"Your job is to create a scientific article about the topic {topic}. It should follow a typical article structure from abstract to conclusion and be divided into chapters and subchapters with their respective headers. If relevant to the topic, it can also include tables. At the end, include a reference list and reference inside the text body using APA style. Please provide the article in markdown format.")

pdf = MarkdownPdf(toc_level=0)
pdf.add_section(Section(response.text))
pdf.meta["title"] = topic

pdf_filename = f"{topic.replace(' ', '_')}_article.pdf"
pdf.save(pdf_filename)

print(f"PDF saved as {pdf_filename}")