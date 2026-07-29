from groq import Groq

# Replace with your actual Groq API key
api_key = "**"
client = Groq(api_key=api_key)

# Test each model
models_to_test = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile", 
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32k",
    "gemma-7b-it",
]

print("Testing Groq models...\n")

for model in models_to_test:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=10,
        )
        print(f"✅ {model} - WORKS")
    except Exception as e:
        error_msg = str(e)
        if "decommissioned" in error_msg:
            print(f"❌ {model} - DECOMMISSIONED")
        else:
            print(f"⚠️  {model} - ERROR: {error_msg[:50]}")

print("\nUse the ✅ model in config.py")