# -*- coding: utf-8 -*-
"""
CariiDefterim - Veritabanı İşlemleri Modülü
============================================
SQLite veritabanı – CRUD, migration, bakiye hesaplama.
Yeni şema: ürün opsiyonel, ödeme takibi, birim, ödeme türü.
"""

import sqlite3
import os
import sys
import shutil


def _get_base_dir():
    """PyInstaller veya normal çalışma dizinini döndürür."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_ADI = "cari_defterim.db"
BASE_DIR = _get_base_dir()
DB_YOLU = os.path.join(BASE_DIR, DB_ADI)


# =============================================================================
# BAĞLANTI
# =============================================================================

def baglanti_al():
    conn = sqlite3.connect(DB_YOLU)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# YARDIMCI – GÜVENLİ SÜTUN EKLEME
# =============================================================================

def _sutun_var_mi(cursor, tablo, sutun):
    """Tabloda belirtilen sütun var mı kontrol eder."""
    cursor.execute(f"PRAGMA table_info({tablo})")
    return any(col[1] == sutun for col in cursor.fetchall())


def _sutun_ekle(cursor, tablo, sutun, tip_varsayilan):
    """Sütun yoksa güvenli şekilde ekler. Veri kaybı oluşmaz."""
    if not _sutun_var_mi(cursor, tablo, sutun):
        cursor.execute(f'ALTER TABLE "{tablo}" ADD COLUMN "{sutun}" {tip_varsayilan}')
        return True
    return False


# =============================================================================
# TABLO OLUŞTURMA & GÖÇ (MIGRATION)
# =============================================================================

def tablolari_olustur():
    """
    Tabloları oluşturur. Eski şemadan yeni şemaya güvenli göç yapar.
    Mevcut veriler ASLA silinmez.
    """
    conn = baglanti_al()
    cursor = conn.cursor()

    # ── Cariler ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cariler (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad  TEXT NOT NULL,
            telefon   TEXT,
            adres     TEXT,
            aciklama  TEXT
        )
    ''')

    # ── Hareketler – Tablo var mı? ──
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hareketler'")
    tablo_var = cursor.fetchone()

    if not tablo_var:
        # Tablo yok – sıfırdan oluştur
        _hareketler_tablosu_olustur(cursor)
    else:
        # Tablo var – eski şema kontrolü ve göç
        _hareketler_goc(cursor)

    conn.commit()
    conn.close()


def _hareketler_tablosu_olustur(cursor):
    """Hareketler tablosunu en güncel şema ile oluşturur."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hareketler (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cari_id       INTEGER NOT NULL,
            tarih         TEXT    NOT NULL,
            urun_adi      TEXT    DEFAULT '',
            miktar        REAL    DEFAULT 0,
            birim         TEXT    DEFAULT '',
            birim_fiyat   REAL    DEFAULT 0,
            toplam        REAL    NOT NULL DEFAULT 0,
            tur           TEXT    NOT NULL CHECK(tur IN ('BORC', 'ALACAK')),
            "not"         TEXT    DEFAULT '',
            odeme_turu    TEXT    DEFAULT '',
            odenen_tutar  REAL    DEFAULT 0,
            kalan_tutar   REAL    DEFAULT 0,
            durum         TEXT    DEFAULT 'ÖDENMEDİ',
            FOREIGN KEY (cari_id) REFERENCES cariler(id) ON DELETE CASCADE
        )
    ''')


def _hareketler_goc(cursor):
    """
    Mevcut hareketler tablosuna eksik sütunları güvenle ekler.
    Eski sütun yapıları korunur; yeni sütunlar varsayılan değerlerle eklenir.
    """
    # ── v1 → v2 göçü: 'tutar' → 'toplam' dönüşümü ──
    cursor.execute("PRAGMA table_info(hareketler)")
    mevcut_sutunlar = [col[1] for col in cursor.fetchall()]

    if 'tutar' in mevcut_sutunlar and 'toplam' not in mevcut_sutunlar:
        # Eski v1 tablosu: tutar sütununu toplam'a dönüştür
        cursor.execute("ALTER TABLE hareketler RENAME TO _hareketler_v1")
        _hareketler_tablosu_olustur(cursor)
        cursor.execute('''
            INSERT INTO hareketler (id, cari_id, tarih, urun_adi, miktar, birim_fiyat,
                                    toplam, tur, "not", kalan_tutar, durum)
            SELECT id, cari_id, tarih,
                   COALESCE(urun_adi, ''), COALESCE(miktar, 0), COALESCE(birim_fiyat, 0),
                   tutar, tur, "not", tutar, 'ÖDENMEDİ'
            FROM _hareketler_v1
        ''')
        cursor.execute("DROP TABLE _hareketler_v1")
        return

    # ── v2 → v3 göçü: yeni sütunları ekle ──
    yeni_sutunlar = [
        ("urun_adi",     "TEXT DEFAULT ''"),
        ("miktar",       "REAL DEFAULT 0"),
        ("birim",        "TEXT DEFAULT ''"),
        ("birim_fiyat",  "REAL DEFAULT 0"),
        ("toplam",       "REAL DEFAULT 0"),
        ("odeme_turu",   "TEXT DEFAULT ''"),
        ("odenen_tutar", "REAL DEFAULT 0"),
        ("kalan_tutar",  "REAL DEFAULT 0"),
        ("durum",        "TEXT DEFAULT 'ÖDENMEDİ'"),
    ]

    eklenen = False
    for sutun, tip in yeni_sutunlar:
        if _sutun_ekle(cursor, "hareketler", sutun, tip):
            eklenen = True

    if eklenen:
        # Yeni eklenen sütunlar için mevcut kayıtları düzelt:
        # kalan_tutar = toplam (ödenmemiş olanlar için)
        cursor.execute('''
            UPDATE hareketler
            SET kalan_tutar = toplam
            WHERE odenen_tutar = 0 AND kalan_tutar = 0 AND toplam > 0
        ''')
        cursor.execute('''
            UPDATE hareketler
            SET durum = 'ÖDENMEDİ'
            WHERE durum IS NULL OR durum = ''
        ''')


# =============================================================================
# DURUM HESAPLAMA
# =============================================================================

def _durum_hesapla(toplam, odenen):
    """Ödenen tutara göre durum belirler."""
    if odenen <= 0:
        return "ÖDENMEDİ"
    elif odenen >= toplam:
        return "TAMAMLANDI"
    else:
        return "KISMİ ÖDENDİ"


# =============================================================================
# CARİ İŞLEMLERİ
# =============================================================================

def cari_ekle(ad_soyad, telefon="", adres="", aciklama=""):
    conn = baglanti_al()
    cur = conn.cursor()
    cur.execute("INSERT INTO cariler (ad_soyad, telefon, adres, aciklama) VALUES (?,?,?,?)",
                (ad_soyad, telefon, adres, aciklama))
    cid = cur.lastrowid
    conn.commit(); conn.close()
    return cid


def cari_guncelle(cari_id, ad_soyad, telefon="", adres="", aciklama=""):
    conn = baglanti_al()
    conn.execute("UPDATE cariler SET ad_soyad=?, telefon=?, adres=?, aciklama=? WHERE id=?",
                 (ad_soyad, telefon, adres, aciklama, cari_id))
    conn.commit(); conn.close()


def cari_sil(cari_id):
    conn = baglanti_al()
    conn.execute("DELETE FROM cariler WHERE id=?", (cari_id,))
    conn.commit(); conn.close()


def cari_detay(cari_id):
    conn = baglanti_al()
    row = conn.execute("SELECT * FROM cariler WHERE id=?", (cari_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def cari_listesi(arama=""):
    """Carileri bakiye ile listeler. Borçlu cariler üstte."""
    conn = baglanti_al()
    q = '''
        SELECT c.id, c.ad_soyad, c.telefon,
            COALESCE(SUM(CASE WHEN h.tur='BORC'   THEN h.toplam ELSE 0 END),0) AS toplam_borc,
            COALESCE(SUM(CASE WHEN h.tur='ALACAK'  THEN h.toplam ELSE 0 END),0) AS toplam_alacak,
            COALESCE(SUM(CASE WHEN h.tur='ALACAK'    THEN h.kalan_tutar ELSE 0 END),0) -
            COALESCE(SUM(CASE WHEN h.tur='BORC'  THEN h.kalan_tutar ELSE 0 END),0) AS bakiye
        FROM cariler c LEFT JOIN hareketler h ON c.id = h.cari_id
    '''
    p = []
    if arama:
        q += " WHERE c.ad_soyad LIKE ?"
        p.append(f"%{arama}%")
    q += " GROUP BY c.id ORDER BY bakiye ASC, c.ad_soyad COLLATE NOCASE ASC"
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================================
# HAREKET İŞLEMLERİ
# =============================================================================

def hareket_ekle(cari_id, tarih, tur, toplam,
                 urun_adi="", miktar=0, birim="", birim_fiyat=0,
                 notu="", odeme_turu="", odenen_tutar=0):
    """
    Yeni hareket ekler.
    Ürün bilgileri opsiyoneldir – boş bırakılırsa finansal işlem olarak kaydedilir.
    """
    kalan = max(toplam - odenen_tutar, 0)
    durum = _durum_hesapla(toplam, odenen_tutar)

    conn = baglanti_al()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO hareketler
            (cari_id, tarih, urun_adi, miktar, birim, birim_fiyat,
             toplam, tur, "not", odeme_turu, odenen_tutar, kalan_tutar, durum)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (cari_id, tarih, urun_adi, miktar, birim, birim_fiyat,
          toplam, tur, notu, odeme_turu, odenen_tutar, kalan, durum))
    hid = cur.lastrowid
    conn.commit(); conn.close()
    return hid


def hareket_guncelle(hareket_id, tarih, tur, toplam,
                     urun_adi="", miktar=0, birim="", birim_fiyat=0,
                     notu="", odeme_turu="", odenen_tutar=0):
    """
    Mevcut hareketi tüm alanlarıyla günceller.
    kalan_tutar ve durum otomatik hesaplanır.
    odenen_tutar toplam'ı aşamaz.
    """
    odenen_tutar = min(odenen_tutar, toplam)
    odenen_tutar = max(odenen_tutar, 0)
    kalan = max(toplam - odenen_tutar, 0)
    durum = _durum_hesapla(toplam, odenen_tutar)

    conn = baglanti_al()
    conn.execute('''
        UPDATE hareketler SET
            tarih=?, tur=?, urun_adi=?, miktar=?, birim=?, birim_fiyat=?,
            toplam=?, "not"=?, odeme_turu=?, odenen_tutar=?, kalan_tutar=?, durum=?
        WHERE id=?
    ''', (tarih, tur, urun_adi, miktar, birim, birim_fiyat,
          toplam, notu, odeme_turu, odenen_tutar, kalan, durum, hareket_id))
    conn.commit(); conn.close()


def hareket_sil(hareket_id):
    conn = baglanti_al()
    conn.execute("DELETE FROM hareketler WHERE id=?", (hareket_id,))
    conn.commit(); conn.close()


def hareket_detay(hareket_id):
    conn = baglanti_al()
    row = conn.execute('''
        SELECT id, cari_id, tarih, urun_adi, miktar, birim, birim_fiyat,
               toplam, tur, "not", odeme_turu, odenen_tutar, kalan_tutar, durum
        FROM hareketler WHERE id=?
    ''', (hareket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def hareketler_listesi(cari_id, baslangic=None, bitis=None):
    """Carinin hareketlerini listeler. Opsiyonel tarih filtresi."""
    conn = baglanti_al()
    q = '''SELECT id, cari_id, tarih, urun_adi, miktar, birim, birim_fiyat,
                  toplam, tur, "not", odeme_turu, odenen_tutar, kalan_tutar, durum
           FROM hareketler WHERE cari_id=?'''
    p = [cari_id]
    if baslangic:
        q += " AND tarih >= ?"; p.append(baslangic)
    if bitis:
        q += " AND tarih <= ?"; p.append(bitis)
    q += " ORDER BY tarih DESC, id DESC"
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================================
# BAKİYE BİLGİSİ (GENİŞLETİLMİŞ)
# =============================================================================

def bakiye_bilgisi(cari_id):
    """
    Kapsamlı bakiye hesaplaması:
      toplam_borc, toplam_alacak,
      toplam_odenen, toplam_tahsil,
      acik_borc, acik_alacak,
      net_bakiye
    """
    conn = baglanti_al()
    row = conn.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN tur='BORC'   THEN toplam       ELSE 0 END),0) AS toplam_borc,
            COALESCE(SUM(CASE WHEN tur='ALACAK'  THEN toplam       ELSE 0 END),0) AS toplam_alacak,
            COALESCE(SUM(CASE WHEN tur='BORC'   THEN odenen_tutar ELSE 0 END),0) AS toplam_odenen,
            COALESCE(SUM(CASE WHEN tur='ALACAK'  THEN odenen_tutar ELSE 0 END),0) AS toplam_tahsil,
            COALESCE(SUM(CASE WHEN tur='BORC'   THEN kalan_tutar  ELSE 0 END),0) AS acik_borc,
            COALESCE(SUM(CASE WHEN tur='ALACAK'  THEN kalan_tutar  ELSE 0 END),0) AS acik_alacak
        FROM hareketler WHERE cari_id=?
    ''', (cari_id,)).fetchone()
    conn.close()

    return {
        "toplam_borc":    row["toplam_borc"],
        "toplam_alacak":  row["toplam_alacak"],
        "toplam_odenen":  row["toplam_odenen"],
        "toplam_tahsil":  row["toplam_tahsil"],
        "acik_borc":      row["acik_borc"],
        "acik_alacak":    row["acik_alacak"],
        "net_bakiye":     row["acik_alacak"] - row["acik_borc"],
    }


# =============================================================================
# YEDEKLEME
# =============================================================================

def veritabani_yedekle(hedef_yol):
    shutil.copy2(DB_YOLU, hedef_yol)

def veritabani_yolu():
    return DB_YOLU
