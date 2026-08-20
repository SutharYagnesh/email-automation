import os
import sys

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.__init__ import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    
    print(f"\n=======================================================")
    print(f"Bulk Email Automation Dashboard running on http://{host}:{port}")
    print(f"=======================================================\n")
    
    app.run(host=host, port=port, debug=debug)
