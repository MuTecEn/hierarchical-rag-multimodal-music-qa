from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:1337/v1", # replace with actual URL if different, following step 3
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="janhq\Jan-v3-4b-base-instruct-Q4_K_XL",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)

print(response.choices[0].message.content)