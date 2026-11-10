# TESTX Store - ระบบขายสินค้าดิจิทัล

เว็บขายของพร้อมระบบแอดมิน (Python Flask)

## บัญชีทดสอบ
- **แอดมิน**: `admin` / `admin123`
- **ผู้ใช้**: `user` / `1234`

---

## วิธี Deploy ขึ้น Railway (เปิดบน iPhone ได้)

### ขั้นตอน

1. สมัครบัญชีที่ [https://railway.app](https://railway.app) (ใช้ GitHub login ได้)

2. กด **New Project** → **Deploy from GitHub repo**
   - หรือเลือก **Empty Project** แล้วอัปโหลดโฟลเดอร์นี้

3. ถ้าใช้ GitHub:
   - อัปโหลดโฟลเดอร์ `testx-store` ขึ้น GitHub ก่อน
   - แล้วเลือก repo นั้นใน Railway

4. Railway จะตรวจจับ Python อัตโนมัติ และใช้ `Procfile`

5. รอ Deploy เสร็จ (ประมาณ 1-2 นาที)

6. กดที่ Service → **Settings** → **Networking** → **Generate Domain**

7. ได้ลิงก์ประมาณ:
   `https://testx-store-production-xxxx.up.railway.app`

8. เปิดลิงก์นี้บน Safari ของ iPhone ได้เลย

---

## รันบนคอมพิวเตอร์ (ทดสอบ)

```bash
pip install -r requirements.txt
python app.py
```

เปิด http://127.0.0.1:5000

---

## โครงสร้าง

```
testx-store/
├── app.py
├── requirements.txt
├── Procfile              ← สำหรับ Railway
├── runtime.txt
├── templates/
└── README.md
```
