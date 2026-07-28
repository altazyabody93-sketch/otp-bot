import sqlite3
from flask import Blueprint, jsonify, request

# إنشاء Blueprint لربط المسارات بتطبيق Flask الرئيسي
api_bp = Blueprint('api_bp', __name__)

DB_PATH = "otp_database.db"

# --------------------------------------------------
# 1. دالة جلب الأكواد المعلقة للتطبيق (Pending OTPs)
# --------------------------------------------------
@api_bp.route('/api/pending-otps', methods=['GET'])
def get_pending_otps():
    try:
        last_id = request.args.get('last_id', default=0, type=int)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, number, otp, platform, timestamp FROM otp_logs WHERE id > ? ORDER BY id ASC",
            (last_id,)
        )
        rows = c.fetchall()
        conn.close()

        otps = []
        for row in rows:
            otps.append({
                'id': row[0],
                'number': row[1],
                'code': row[2],
                'platform': row[3],
                'timestamp': row[4]
            })

        return jsonify({
            'success': True,
            'count': len(otps),
            'data': otps
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# --------------------------------------------------
# 2. دالة جلب آخر كود لرقم محدد (Get My Code)
# --------------------------------------------------
@api_bp.route('/api/get-my-code', methods=['GET'])
def get_my_code():
    try:
        user_number = request.args.get('number')
        if not user_number:
            return jsonify({'success': False, 'message': 'يرجى تحديد الرقم'})

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT number, otp, timestamp, platform FROM otp_logs WHERE number = ? ORDER BY id DESC LIMIT 1",
            (user_number,)
        )
        row = c.fetchone()
        conn.close()

        if row:
            return jsonify({
                'success': True,
                'number': row[0],
                'code': row[1],
                'timestamp': row[2],
                'platform': row[3]
            })

        return jsonify({'success': False, 'message': 'في انتظار وصول الكود...'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
