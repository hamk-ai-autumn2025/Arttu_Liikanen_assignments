from openai import OpenAI

client = OpenAI()

prompt = input("Choose a topic for a poem: ")

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a creative writer who writes poems. The user will give you a topic and you must write 3 different poems about it. Clearly seperate and number these poems. don't answer with anything else but the poems and try to make them search engine optimized."},
        {"role": "user", "content": prompt},
    ],
    temperature=0.8,
    top_p=0.9,
    presence_penalty=0.6,
    frequency_penalty=0.6,
    max_completion_tokens=1000,
)

text = completion.choices[0].message.content
print(text)