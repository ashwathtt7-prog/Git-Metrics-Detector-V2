
import asyncio
import os
import sys
import json

sys.path.append(os.getcwd())
from app.services import llm_service

async def test():
    print("--- 🧪 Testing Gemini Stage 3 (Project Overview) ---")
    
    # Mock data
    file_tree = ["src/index.js", "src/utils.js", "package.json", "README.md"]
    key_files = [
        {"path": "package.json", "content": '{"name": "test-project", "dependencies": {"express": "^4.17.1"}}'},
        {"path": "README.md", "content": "# Test Project\nThis is a simple express server."}
    ]
    
    print("Calling analyze_project_overview...")
    try:
        result = await llm_service.analyze_project_overview(file_tree, key_files)
        print("\n--- LLM Result ---")
        print(json.dumps(result, indent=2))
        print("\n✅ Gemini is working perfectly with the service account!")
    except Exception as e:
        print(f"\n❌ Gemini Test FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
