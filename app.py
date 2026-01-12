import json
import os
import webbrowser
import winsound
import time
from flask import Flask, render_template, render_template_string, request, redirect

# ==========================================
# 1. ส่วนจัดการฐานข้อมูล (Database)
# ==========================================
DB_FILE = 'stock_db.json'

def load_db():
    if not os.path.exists(DB_FILE):
        initial_data = {
            "PART-001": {"name": "🔩 น็อต M5 (Screw)", "qty": 10, "min": 3},
            "PART-002": {"name": "⚙️ แหวนรอง (Washer)", "qty": 50, "min": 10},
            "CAN-COKE": {"name": "🥤 โค้กกระป๋อง", "qty": 5, "min": 2}
        }
        save_db(initial_data)
        return initial_data
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

inventory = load_db()
last_scan_result = {"status": "waiting", "data": None, "code": ""}

# ==========================================
# 2. ตั้งค่า Web Server
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
IMAGE_FOLDER = os.path.join('static', 'images')
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# ==========================================
# 3. HTML สำหรับหน้า Admin (ฝังไว้ในนี้)
# ==========================================
html_admin = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Stock</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Kanit', sans-serif; padding: 20px; max-width: 900px; margin: auto; background: #ecf0f1; color: #2c3e50; }
        .btn { padding: 8px 15px; border: none; cursor: pointer; text-decoration: none; display: inline-block; border-radius: 4px; font-size: 14px; margin: 2px; }
        .btn-back { background: #7f8c8d; color: white; margin-bottom: 20px; }
        .btn-save { background: #27ae60; color: white; font-size: 16px; padding: 10px 20px; }
        .btn-edit { background: #f1c40f; color: #2c3e50; } 
        .btn-del { background: #e74c3c; color: white; }
        table { width: 100%; background: white; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-top: 20px; }
        th { background-color: #34495e; color: white; padding: 12px; text-align: left; }
        td { border-bottom: 1px solid #eee; padding: 10px; vertical-align: middle; }
        tr:hover { background-color: #f9f9f9; }
        .form-box { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input[type="text"], input[type="number"] { padding: 10px; width: 100%; box-sizing: border-box; border: 1px solid #bdc3c7; border-radius: 4px; margin-top: 5px; }
        input[type="file"] { margin-top: 5px; padding: 5px; background: #ecf0f1; width: 100%; border-radius: 4px; }
        label { font-weight: bold; display: block; margin-top: 10px; }
        .table-img { width: 50px; height: 50px; object-fit: cover; border-radius: 5px; border: 1px solid #ddd; background-color: #eee; }
    </style>
</head>
<body>
    <a href="/" class="btn btn-back">⬅️ กลับหน้า Monitor</a>
    
    <h2>⚙️ จัดการฐานข้อมูลสินค้า</h2>

    <div class="form-box">
        <form action="/add" method="post" enctype="multipart/form-data" id="productForm">
            <h3 style="margin-top:0;">📝 เพิ่ม / แก้ไข สินค้า</h3>
            
            <label>รหัสบาร์โค้ด:</label>
            <input type="text" name="code" id="input_code" placeholder="ยิงบาร์โค้ด หรือพิมพ์รหัส" required>
            
            <label>ชื่อสินค้า:</label>
            <input type="text" name="name" id="input_name" placeholder="เช่น 🔩 น็อต M5" required>
            
            <div style="display: flex; gap: 20px;">
                <div style="flex:1;">
                    <label>จำนวนคงเหลือ:</label>
                    <input type="number" name="qty" id="input_qty" value="10" required>
                </div>
                <div style="flex:1;">
                    <label>เตือนเมื่อต่ำกว่า (Min):</label>
                    <input type="number" name="min" id="input_min" value="3" required>
                </div>
            </div>

            <label>🖼️ รูปภาพสินค้า (ถ้ามี):</label>
            <input type="file" name="image" accept=".jpg, .jpeg, .png">
            <div style="font-size: 12px; color: #7f8c8d; margin-top: 3px;">* แนะนำไฟล์ .jpg (ระบบจะเปลี่ยนชื่อไฟล์ให้ตรงกับรหัสสินค้าอัตโนมัติ)</div>
            
            <br>
            <button type="submit" class="btn btn-save">💾 บันทึกข้อมูล</button>
            <button type="button" class="btn" onclick="clearForm()" style="background:#bdc3c7; color:white;">ล้างค่า</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th width="10%">รูป</th>
                <th width="20%">รหัส</th>
                <th width="30%">ชื่อสินค้า</th>
                <th width="10%">คงเหลือ</th>
                <th width="10%">เตือนที่</th>
                <th width="20%">จัดการ</th>
            </tr>
        </thead>
        <tbody>
            {% for code, item in data.items() %}
            <tr>
                <td style="text-align: center;">
                    <img src="/static/images/{{code}}.jpg?t={{ timestamp }}" class="table-img" onerror="this.style.opacity='0'">
                </td>
                <td><b>{{ code }}</b></td>
                <td>{{ item.name }}</td>
                <td style="color: {{ 'red' if item.qty <= item.min else 'green' }}; font-weight:bold;">
                    {{ item.qty }}
                </td>
                <td>{{ item.min }}</td>
                
                <td style="white-space: nowrap;">
                    <button class="btn btn-edit" 
                        onclick="editItem('{{code}}', '{{item.name}}', {{item.qty}}, {{item.min}})">
                        ✏️ แก้ไข
                    </button>
                    <a href="/delete/{{ code }}" class="btn btn-del" onclick="return confirm('ยืนยันลบสินค้านี้?');">
                        🗑️ ลบ
                    </a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        function editItem(code, name, qty, min) {
            document.getElementById('input_code').value = code;
            document.getElementById('input_name').value = name;
            document.getElementById('input_qty').value = qty;
            document.getElementById('input_min').value = min;
            window.scrollTo({ top: 0, behavior: 'smooth' });
            const formBox = document.querySelector('.form-box');
            formBox.style.backgroundColor = '#fff3cd';
            setTimeout(() => { formBox.style.backgroundColor = 'white'; }, 500);
        }
        function clearForm() {
            document.getElementById('productForm').reset();
        }
    </script>
</body>
</html>
"""

# ==========================================
# 4. Server Routes
# ==========================================
@app.route('/')
def index():
    return render_template('index.html', result=last_scan_result)

@app.route('/scan/<code>')
def scan_process(code):
    global last_scan_result
    code = code.strip()
    if code in inventory:
        inventory[code]['qty'] -= 1
        save_db(inventory)
        last_scan_result = {
            "status": "found", "data": inventory[code], "code": code 
        }
        try: winsound.Beep(1000, 200)
        except: pass
    else:
        last_scan_result = { "status": "not_found", "code": code }
        try: winsound.Beep(500, 500)
        except: pass
    return redirect('/')

@app.route('/reset')
def reset():
    global last_scan_result
    last_scan_result = {"status": "waiting", "data": None, "code": ""}
    return redirect('/')

@app.route('/admin')
def admin():
    sorted_inventory = dict(sorted(inventory.items()))
    return render_template_string(html_admin, data=sorted_inventory, timestamp=int(time.time()))

@app.route('/add', methods=['POST'])
def add():
    code = request.form['code'].strip()
    inventory[code] = {
        "name": request.form['name'], 
        "qty": int(request.form['qty']), 
        "min": int(request.form['min'])
    }
    save_db(inventory)
    
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = code + ".jpg"
            file_path = os.path.join(IMAGE_FOLDER, filename)
            file.save(file_path)
            
    return redirect('/admin')

@app.route('/delete/<code>')
def delete(code):
    if code in inventory: 
        del inventory[code]
        save_db(inventory)
        try:
            os.remove(os.path.join(IMAGE_FOLDER, code + ".jpg"))
        except:
            pass
    return redirect('/admin')

# --- เพิ่มส่วน Dashboard (Route ใหม่) ---
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', data=inventory)

if __name__ == '__main__':
    webbrowser.open('http://localhost:5000')
    app.run(host='0.0.0.0', port=5000, debug=True)