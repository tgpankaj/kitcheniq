"""
KitchenIQ — Worker Routes
GET  /api/worker/status    scheduler status
POST /api/worker/run-now   trigger immediate sync
"""
from flask import Blueprint, jsonify

from app.utils.auth import token_required
from app.workers.sync_worker import scheduler_status, auto_sync_all


worker_bp = Blueprint('worker', __name__)


@worker_bp.route('/status', methods=['GET'])
@token_required
def status():
    return jsonify(scheduler_status())


@worker_bp.route('/run-now', methods=['POST'])
@token_required
def run_now():
    try:
        result = auto_sync_all()
        return jsonify({
            'message': 'Worker executed',
            'synced': result.get('synced', 0),
            'failed': result.get('failed', 0),
            'total': result.get('total', 0),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500