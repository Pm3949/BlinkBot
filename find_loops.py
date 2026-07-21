import os
import re

def check_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for useEffect calling a state setter with no dependencies
    matches = re.finditer(r'useEffect\s*\(\s*\(\)\s*=>\s*\{[^\}]*(set[A-Z][a-zA-Z0-9_]+|setActive[a-zA-Z0-9_]+)[^\}]*\}\s*\)', content)
    for m in matches:
        print(f"No deps useEffect setting state in {filepath}: {m.group(0)}")
        
for root, _, files in os.walk('client/src'):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            check_file(os.path.join(root, file))
