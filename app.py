"""
Root application entry point.
Enables running the application via `python app.py` or `flask run`.
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
