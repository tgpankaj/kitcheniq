"""
KitchenIQ — Upload Routes
POST /api/upload/csv
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_one
from app.utils.auth import token_required
from app.services.csv_service import parse_csv, process_orders


upload_bp = Blueprint('upload', __name__)


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


@upload_bp.route('/csv', methods=['POST'])
@token_required
def upload_csv():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found for this user'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded. Use form field "file".'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only CSV files are allowed'}), 400

    file_bytes = file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB
        return jsonify({'error': 'File too large (max 10 MB)'}), 400

    df, err = parse_csv(file_bytes)
    if err:
        return jsonify({'error': err}), 400

    result = process_orders(kitchen_id, df)

    return jsonify({
        'message': f"Imported {result['created']} orders",
        'created': result['created'],
        'failed': result['failed'],
        'errors': result['errors'],
    }), 201