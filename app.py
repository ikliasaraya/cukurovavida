from flask import Flask, render_template, request
import re
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Çevre değişkenlerini (.env) yüklemek için gerekli kütüphane
from dotenv import load_dotenv
load_dotenv() 

app = Flask(__name__)

# --- VERİ ÇEKME MOTORU ---
def get_products():
    json_path = os.path.join(app.root_path, 'products.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"JSON Okuma Hatası: {e}")
        return []

# --- DİL ÇEVİRİ MOTORU ---
def get_translations():
    json_path = os.path.join(app.root_path, 'translations.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Çeviri Dosyası Hatası: {e}")
        return {"tr": {}, "en": {}}

# Tüm sayfalara dili (t) otomatik gönderen bağlayıcı
@app.context_processor
def inject_translations():
    lang = request.args.get('lang', 'tr') # URL'de dil yoksa Türkçe (tr) say
    if lang not in ['tr', 'en']:
        lang = 'tr'
    
    translations = get_translations()
    return dict(t=translations.get(lang, {}), current_lang=lang)

# 1. Ana Sayfa
@app.route('/')
def home():
    products_data = get_products()
    return render_template('index.html', products=products_data)

# 2. Kurumsal Sayfa
@app.route('/kurumsal')
def kurumsal():
    return render_template('info.html')

# 3. Katalog Sayfası
@app.route('/katalog')
def catalog():
    products_data = get_products() 
    return render_template('catalog.html', products=products_data)

# 4. İletişim ve Form Sayfası (E-posta Entegrasyonlu)
@app.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    success = False
    errors = []
    urun_adi = ""

    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        firma_adi = request.form.get('firma_adi', '').strip()
        email = request.form.get('email', '').strip()
        telefon = request.form.get('telefon', '').strip()
        talep_urun = request.form.get('talep_urun', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        
        if not ad_soyad or len(ad_soyad) < 3:
            errors.append("Lütfen geçerli bir ad soyad giriniz (En az 3 karakter).")
            
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not email or not re.match(email_regex, email):
            errors.append("Lütfen geçerli bir e-posta adresi giriniz (Örn: info@sirket.com).")
            
        temiz_tel = re.sub(r'\D', '', telefon) 
        if not (re.match(r'^0?5\d{9}$', temiz_tel)):
            errors.append("Lütfen geçerli bir cep telefon numarası giriniz (05xx xxx xx xx).")

        if not errors:
            gonderen_mail = os.getenv("MAIL_ADRESI") 
            mail_sifresi = os.getenv("MAIL_SIFRESI")      
            alici_mail = os.getenv("MAIL_ADRESI")   
            
            msg = MIMEMultipart()
            msg['From'] = gonderen_mail
            msg['To'] = alici_mail
            msg['Subject'] = f"WEBSİTESİ YENİ TEKLİF TALEBİ: {firma_adi or ad_soyad}"
            
            body = f"""
            ÇUKUROVA VİDA - YENİ SİPARİŞ / TEKLİF TALEBİ
            ------------------------------------------------
            Müşteri Adı : {ad_soyad}
            Firma Ünvanı: {firma_adi if firma_adi else 'Belirtilmedi'}
            E-Posta     : {email}
            Telefon     : {temiz_tel}
            
            TALEP EDİLEN ÜRÜN:
            {talep_urun}
            
            PROJE NOTLARI:
            {mesaj if mesaj else 'Not eklenmedi.'}
            ------------------------------------------------
            Bu e-posta sistem tarafından otomatik gönderilmiştir.
            """
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            try:
                server = smtplib.SMTP_SSL('srvc43.trwww.com', 465)
                server.login(gonderen_mail, mail_sifresi)
                server.send_message(msg)
                server.quit()
                print("E-posta Turhost üzerinden başarıyla iletildi!")
                success = True
            except Exception as e:
                print(f"Mail gönderme hatası yaşandı: {e}")
                errors.append("Sistem yoğunluğu nedeniyle form iletilemedi, lütfen telefonla ulaşınız.")
           
        else:
            urun_adi = talep_urun

    if request.method == 'GET':
        secilen_id = request.args.get('urun', '')
        if secilen_id:
            products = get_products()
            for p in products:
                if str(p.get('id')) == str(secilen_id):
                    urun_adi = p.get('name_tr')
                    break

    return render_template('contact.html', urun_adi=urun_adi, success=success, errors=errors)

# 5. Dinamik Ürün Detay Sayfası
@app.route('/katalog/urun/<int:urun_id>')
def product_detail(urun_id):
    products = get_products()
    selected_product = None
    
    for p in products:
        if str(p.get('id')) == str(urun_id):
            selected_product = p
            break
            
    if selected_product:
        return render_template('product_detail.html', product=selected_product)
    else:
        return "Aradığınız ürün bulunamadı.", 404
    
# 6. KVKK ve Gizlilik Politikası
@app.route('/kvkk')
def kvkk():
    return render_template('kvkk.html')

@app.route('/gizlilik')
def gizlilik():
    return render_template('gizlilik.html')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)