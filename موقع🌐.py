from flask import Flask, request, jsonify
import sqlite3
import json
import random
import os

app = Flask(__name__)

DB_PATH = "bot.db"

# ===== دوال قاعدة البيانات =====
def get_combo(platform, country_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT numbers FROM combos WHERE platform=? AND country_code=?", (platform, country_code))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def get_platforms():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT platform FROM combos")
    platforms = [row[0] for row in c.fetchall()]
    conn.close()
    return platforms

def get_countries_by_platform(platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code FROM combos WHERE platform=?", (platform,))
    countries = [row[0] for row in c.fetchall()]
    conn.close()
    return countries

def get_country_name(code):
    names = {
        "20": "Egypt", "966": "Saudi Arabia", "971": "UAE", "1": "USA/Canada",
        "44": "UK", "90": "Turkey", "91": "India", "49": "Germany",
        "7": "Russia", "33": "France", "34": "Spain", "39": "Italy"
    }
    return names.get(code, "Unknown")

# ===== مسار الصفحة الرئيسية =====
@app.route('/')
def home():
    platforms = get_platforms()
    
    # ===== HTML مضمن داخل بايثون =====
    html_content = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP Generator</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 420px;
            backdrop-filter: blur(10px);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #333;
            font-size: 28px;
            font-weight: 700;
        }}
        .header p {{
            color: #666;
            margin-top: 10px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 8px;
            color: #444;
            font-weight: 600;
            font-size: 14px;
        }}
        .form-group select {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e5ee;
            border-radius: 10px;
            font-size: 16px;
            background: white;
            transition: border 0.3s ease;
            outline: none;
            appearance: none;
            background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23007bff%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
            background-repeat: no-repeat;
            background-position: right 15px top 50%;
            background-size: 12px auto;
        }}
        .form-group select:focus {{
            border-color: #667eea;
        }}
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 20px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }}
        .btn:active {{
            transform: translateY(0);
        }}
        #result {{
            margin-top: 25px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            display: none;
        }}
        .success {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .platform-icons {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .platform-icon {{
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            opacity: 0.6;
            transition: 0.3s;
        }}
        .platform-icon.active {{
            opacity: 1;
            transform: scale(1.1);
        }}
        .wa {{ background: #25D366; }}
        .tg {{ background: #0088cc; }}
        .fb {{ background: #1877f2; }}
        .ig {{ background: #E4405F; }}
        .tt {{ background: #000; color: #fff; }}
        .sn {{ background: #FFFC00; color: #000; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 OTP Generator</h1>
            <p>احصل على رقم وهمي لتفعيل حساباتك</p>
        </div>
        
        <div class="platform-icons">
            <div class="platform-icon wa active" data-platform="whatsapp">📱</div>
            <div class="platform-icon tg" data-platform="telegram">✈️</div>
            <div class="platform-icon fb" data-platform="facebook">📘</div>
            <div class="platform-icon ig" data-platform="instagram">📸</div>
            <div class="platform-icon tt" data-platform="tiktok">🎵</div>
            <div class="platform-icon sn" data-platform="snapchat">👻</div>
        </div>
        
        <div class="form-group">
            <label for="platform">اختر المنصة:</label>
            <select id="platform">
                <option value="">-- اختر --</option>
                {{''.join([f'<option value="{p}">{p.capitalize()}</option>' for p in platforms])}}
            </select>
        </div>
        
        <div class="form-group">
            <label for="country">اختر الدولة:</label>
            <select id="country" disabled>
                <option value="">-- اختر الدولة أولاً --</option>
            </select>
        </div>
        
        <button class="btn" onclick="getNumber()">🚀 احصل على رقم</button>
        
        <div id="result"></div>
    </div>

    <script>
        const platformSelect = document.getElementById('platform');
        const countrySelect = document.getElementById('country');
        const resultDiv = document.getElementById('result');
        
        document.querySelectorAll('.platform-icon').forEach(icon => {
            icon.addEventListener('click', function() {
                document.querySelectorAll('.platform-icon').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                platformSelect.value = this.dataset.platform;
                platformSelect.dispatchEvent(new Event('change'));
            });
        });

        platformSelect.addEventListener('change', async function() {
            const platform = this.value;
            if (!platform) {
                countrySelect.innerHTML = '<option value="">-- اختر الدولة أولاً --</option>';
                countrySelect.disabled = true;
                return;
            }
            countrySelect.disabled = true;
            countrySelect.innerHTML = '<option value="">جاري التحميل...</option>';
            
            const response = await fetch('/get_countries', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{platform: platform}})
            }});
            const countries = await response.json();
            
            let options = '<option value="">-- اختر الدولة --</option>';
            countries.forEach(c => {{
                options += `<option value="${{c.code}}">${{c.name}}</option>`;
            }});
            countrySelect.innerHTML = options;
            countrySelect.disabled = false;
        });

        async function getNumber() {{
            const platform = platformSelect.value;
            const country = countrySelect.value;
            
            if (!platform || !country) {{
                resultDiv.className = 'error';
                resultDiv.textContent = '⚠️ يرجى اختيار المنصة والدولة.';
                resultDiv.style.display = 'block';
                return;
            }}

            resultDiv.style.display = 'none';
            
            const response = await fetch('/get_number', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{platform: platform, country: country}})
            }});
            const data = await response.json();
            
            resultDiv.style.display = 'block';
            if (data.status === 'success') {{
                resultDiv.className = 'success';
                resultDiv.textContent = `✅ رقمك هو: ${{data.number}}`;
            }} else {{
                resultDiv.className = 'error';
                resultDiv.textContent = data.message;
            }}
        }}
    </script>
</body>
</html>
    """
    return html_content

# ===== مسارات API =====
@app.route('/get_countries', methods=['POST'])
def api_get_countries():
    platform = request.json.get('platform')
    countries = get_countries_by_platform(platform)
    country_list = [{'code': c, 'name': get_country_name(c)} for c in countries]
    return jsonify(country_list)

@app.route('/get_number', methods=['POST'])
def api_get_number():
    platform = request.json.get('platform')
    country = request.json.get('country')
    numbers = get_combo(platform, country)
    if numbers:
        number = random.choice(numbers)
        return jsonify({'status': 'success', 'number': number})
    return jsonify({'status': 'error', 'message': 'No numbers available'})

if __name__ == '__main__':
    print("🔥 الموقع يعمل على http://127.0.0.1:5000")
    app.run(debug=True, port=5000)