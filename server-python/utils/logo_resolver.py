import os

def get_logo_path() -> str:
    """
    Dynamically locates the platform logo path.
    Works across local dev and production deployments by searching relative directories.
    """
    # 1. Environment variable override (highly recommended for production Docker/K8s)
    env_logo = os.getenv("PLATFORM_LOGO_PATH")
    if env_logo and os.path.exists(env_logo):
        return env_logo

    # 2. Local/Git structure check: ../client/public/logo1.png
    # __file__ is in server-python/utils/
    utils_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.dirname(utils_dir) # server-python/
    project_root = os.path.dirname(server_dir) # RAGMate/
    
    local_path = os.path.join(project_root, "client", "public", "logo1.png")
    if os.path.exists(local_path):
        return local_path

    # 3. Production directory fallback: check server static files directory
    prod_static_path = os.path.join(server_dir, "static", "logo1.png")
    if os.path.exists(prod_static_path):
        return prod_static_path

    # 4. Same directory fallback (e.g. if everything is zipped together)
    fallback_path = os.path.join(server_dir, "logo1.png")
    if os.path.exists(fallback_path):
        return fallback_path

    return ""
