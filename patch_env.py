import os
import glob

# 1. Update Frontend JS/JSX files
frontend_dir = "/home/mp3949/Documents/RAGMate/client/src"
for root, _, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith(".js") or file.endswith(".jsx"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            
            original_content = content
            
            # Replace explicit hardcoded fetches
            content = content.replace("'http://localhost:8000", "`${import.meta.env.VITE_API_BASE_URL}")
            content = content.replace("`http://localhost:8000", "`${import.meta.env.VITE_API_BASE_URL}")
            
            import re
            
            content = re.sub(r"['\"]http://localhost:8000([^'\"]*)['\"]", r"`${import.meta.env.VITE_API_BASE_URL}\1`", content)
            
            content = content.replace(' || "http://localhost:8000"', '')
            content = content.replace(" || 'http://localhost:8000'", "")
            
            if content != original_content:
                with open(path, "w") as f:
                    f.write(content)
                print(f"Updated {path}")

# 2. Update Backend main.py
main_py_path = "/home/mp3949/Documents/RAGMate/server-python/main.py"
with open(main_py_path, "r") as f:
    main_content = f.read()

cors_target = """app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)"""

cors_replacement = """from dotenv import load_dotenv
load_dotenv()

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allow_origins = [frontend_url] if frontend_url != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)"""

if cors_target in main_content:
    main_content = main_content.replace(cors_target, cors_replacement)
    with open(main_py_path, "w") as f:
        f.write(main_content)
    print(f"Updated {main_py_path}")
else:
    print("CORS target not found in main.py")
