import os
import re

def check_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Simple heuristic: find setSomething( inside component but outside useEffect/useCallback/handlers
    # Actually, a common mistake is `<Component onChange={setFoo(true)} />` instead of `onChange={() => setFoo(true)}`
    
    matches = re.finditer(r'(on[A-Z][a-zA-Z]+)=\{([a-zA-Z0-9_]+)\(([^)]*)\)\}', content)
    for m in matches:
        # Ignore things like onClick={handleSubmit(e)} if handleSubmit is not a state setter, but it's suspicious
        # Especially if it's setSomething(true)
        print(f"Suspicious inline call in {filepath}: {m.group(0)}")
        
for root, _, files in os.walk('client/src'):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            check_file(os.path.join(root, file))
