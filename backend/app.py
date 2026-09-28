"""
KitchenIQ — Flask Application
Minimal starting point. Features add honge step by step.
"""
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

    CORS(app, origins=['http://localhost:5500', 'http://127.0.0.1:5500'])

    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'ok',
            'service': 'KitchenIQ API',
            'version': '0.1.0',
        })

    @app.route('/')
    def root():
        return jsonify({
            'service': 'KitchenIQ',
            'message': 'API is running. Visit /api/health',
        })

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)