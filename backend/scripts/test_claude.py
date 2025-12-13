#!/usr/bin/env python3
"""Test Claude API key."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import anthropic

key = os.getenv("CLAUDE_API_KEY")
if not key:
    print("ERROR: CLAUDE_API_KEY not set")
    sys.exit(1)

print(f"Testing key: {key[:20]}...{key[-10:]}")

client = anthropic.Anthropic(api_key=key)

# Try different model names
models_to_try = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-instant-1.2",
]

for model in models_to_try:
    try:
        message = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ {model}: Works - {message.content[0].text[:30]}")
    except anthropic.NotFoundError:
        print(f"❌ {model}: Not found")
    except anthropic.AuthenticationError as e:
        print(f"❌ {model}: Auth error - {e}")
    except Exception as e:
        print(f"❌ {model}: {type(e).__name__} - {str(e)[:50]}")
