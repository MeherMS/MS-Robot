# backend/test_gemini_key.py - CORRECTED

import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("=" * 70)
print("GEMINI API KEY DEBUG")
print("=" * 70)

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    print("   Create/check: backend/.env")
    print("   Content should be: GEMINI_API_KEY=your_key_here")
else:
    print(f"✅ API Key found (length: {len(api_key)})")
    print(f"   First 10 chars: {api_key[:10]}...")
    print(f"   Last 10 chars: ...{api_key[-10:]}")

print("\nNow testing connection...")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    print("✅ genai.configure() successful")
    
    # Try to list models (convert generator to list)
    models = list(genai.list_models())  # FIXED: Wrap in list()
    print(f"✅ Successfully listed models")
    print(f"   Available models: {len(models)}")
    
    for model in models:
        print(f"     - {model.name}")
    
    # Try a simple generation
    print("\nTesting simple generation...")
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content("What is 2+2?")
    print(f"✅ Generation test successful")
    print(f"   Response: {response.text}")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - GEMINI API IS READY!")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"   Type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("=" * 70)