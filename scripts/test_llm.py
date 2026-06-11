import os
from dotenv import load_dotenv
from litellm import LitelLM, completion

load_dotenv()

model = os.getenv("LITELLM_MODEL") 
print(f"Using model: {model}")

response = completion(
    model=model,
    messages=[{"role": "user", "content": "Say hello!"}],
)

print(response.choices[0].message.content)
print("✅ LiteLLM working!")