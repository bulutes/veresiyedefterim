# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import database

db_yolu = os.path.join(os.path.dirname(__file__), "cari_defterim.db")

print("Migration ve veritabanı testi başlatılıyor...")
database.tablolari_olustur()
print("Tablolar başarıyla oluşturuldu ve migration yapıldı.")

# Test cari ekle
cid = database.cari_ekle("Test Müşteri V3", "0555", "Adres")
print(f"Cari Eklendi ID: {cid}")

# Ürünlü borç: Kısmi ödemeli
hid1 = database.hareket_ekle(cid, "2026-04-15", "BORC", 3000, 
                             urun_adi="Ürün 1", miktar=10, birim="Adet", birim_fiyat=300, 
                             odeme_turu="Nakit", odenen_tutar=1000)

h1 = database.hareket_detay(hid1)
assert h1["kalan_tutar"] == 2000
assert h1["durum"] == "KISMİ ÖDENDİ"
print("Kısmi Ödemeli Borç başarılı.")

# Ürünsüz tam ödenmiş alacak
hid2 = database.hareket_ekle(cid, "2026-04-16", "ALACAK", 500, 
                             odeme_turu="Kart", odenen_tutar=500)
h2 = database.hareket_detay(hid2)
assert h2["kalan_tutar"] == 0
assert h2["durum"] == "TAMAMLANDI"
print("Ürünsüz Tam Tahsilatlı Alacak başarılı.")

# Bakiye kontrolü
bak = database.bakiye_bilgisi(cid)
print(f"Bakiye Bilgisi: {bak}")
assert bak["toplam_borc"] == 3000
assert bak["toplam_alacak"] == 500
assert bak["toplam_odenen"] == 1000
assert bak["toplam_tahsil"] == 500
assert bak["acik_borc"] == 2000
assert bak["acik_alacak"] == 0
assert bak["net_bakiye"] == -2000 # (acik alacak 0 - acik borç 2000)

print("Tüm Testler Başarılı.")
