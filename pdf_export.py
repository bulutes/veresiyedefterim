# -*- coding: utf-8 -*-
"""
CariiDefterim - PDF Ekstre Modülü (v3)
=======================================
reportlab ile logolu, ürün detaylı, ödeme takipli cari hesap ekstresi.
"""

import os, sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =============================================================================
# FONT
# =============================================================================

_font_kayitli = False

def _fontlari_kaydet():
    global _font_kayitli
    if _font_kayitli:
        return
    fd = "C:/Windows/Fonts"
    for ad, dosyalar in [("TRFont", ["segoeui.ttf","arial.ttf","calibri.ttf"]),
                          ("TRFontBold", ["segoeuib.ttf","arialbd.ttf","calibrib.ttf"])]:
        for d in dosyalar:
            yol = os.path.join(fd, d)
            if os.path.exists(yol):
                try:
                    pdfmetrics.registerFont(TTFont(ad, yol)); break
                except: continue
    _font_kayitli = True


def _base():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _tarih_f(t):
    try:
        p = t.split("-"); return f"{p[2]}.{p[1]}.{p[0]}"
    except: return t


def _para(v):
    s = f"-{abs(v):,.2f}" if v < 0 else f"{v:,.2f}"
    return s.replace(",","X").replace(".",",").replace("X",".") + " ₺"


# =============================================================================
# PDF OLUŞTURMA
# =============================================================================

def ekstre_olustur(hedef_yol, cari, hareketler, bakiye, logo_yolu=None):
    """
    Kapsamlı cari hesap ekstresi PDF'i oluşturur.
    Yeni sütunlar: Birim, Ödenen/Tahsil, Kalan, Durum, Ödeme Türü
    """
    _fontlari_kaydet()

    try:
        pdfmetrics.getFont("TRFont"); F = "TRFont"; FB = "TRFontBold"
    except:
        F = "Helvetica"; FB = "Helvetica-Bold"

    doc = SimpleDocTemplate(hedef_yol, pagesize=A4,
        topMargin=1.2*cm, bottomMargin=1.2*cm,
        leftMargin=1*cm, rightMargin=1*cm,
        title=f"Ekstre - {cari['ad_soyad']}", author="CariiDefterim")

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("T", parent=styles["Title"], fontName=FB,
        fontSize=16, textColor=colors.HexColor("#1a1a2e"), alignment=TA_CENTER, spaceAfter=3*mm)
    s_sub = ParagraphStyle("S", parent=styles["Normal"], fontName=F,
        fontSize=8, textColor=colors.HexColor("#6b7280"), alignment=TA_CENTER, spaceAfter=5*mm)
    s_lbl = ParagraphStyle("L", fontName=FB, fontSize=9, textColor=colors.HexColor("#374151"))
    s_val = ParagraphStyle("V", fontName=F, fontSize=9, textColor=colors.HexColor("#1a1a2e"))
    s_foot = ParagraphStyle("FT", fontName=F, fontSize=7,
        textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER)

    els = []

    # ── Logo ──
    lp = logo_yolu or os.path.join(_base(), "logo.png")
    if os.path.exists(lp):
        try:
            im = Image(lp, width=4.5*cm, height=2*cm); im.hAlign = "CENTER"
            els.append(im); els.append(Spacer(1, 3*mm))
        except: pass

    els.append(Paragraph("CARİ HESAP EKSTRESİ", s_title))
    els.append(Paragraph(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_sub))
    els.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d1d5db"),
        spaceAfter=3*mm, spaceBefore=1*mm))

    # ── Cari Bilgileri ──
    info = [
        [Paragraph("Cari:", s_lbl), Paragraph(cari.get("ad_soyad",""), s_val)],
        [Paragraph("Telefon:", s_lbl), Paragraph(cari.get("telefon","") or "–", s_val)],
        [Paragraph("Adres:", s_lbl), Paragraph(cari.get("adres","") or "–", s_val)],
    ]
    it = Table(info, colWidths=[2.5*cm, 16*cm])
    it.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))
    els.append(it); els.append(Spacer(1, 5*mm))

    # ── Hareket Tablosu ──
    hs = ParagraphStyle("TH", fontName=FB, fontSize=6.5, textColor=colors.white, alignment=TA_CENTER)
    hc = ParagraphStyle("TC", fontName=F, fontSize=6.5, textColor=colors.HexColor("#1a1a2e"))
    hr = ParagraphStyle("TR", fontName=F, fontSize=6.5, textColor=colors.HexColor("#1a1a2e"), alignment=TA_RIGHT)
    hm = ParagraphStyle("TM", fontName=F, fontSize=6.5, textColor=colors.HexColor("#1a1a2e"), alignment=TA_CENTER)

    basliklar = ["Tarih","Tür","Ürün/Açıklama","Miktar","Birim","B.Fiyat",
                 "Toplam","Ödenen","Kalan","Durum","Öd.Türü","Not"]
    th = [Paragraph(b, hs) for b in basliklar]
    rows = [th]

    for h in hareketler:
        tur = h.get("tur","")
        ts = "BORÇ" if tur == "BORC" else "ALACAK"
        tc = colors.HexColor("#dc2626") if tur == "BORC" else colors.HexColor("#16a34a")
        tur_s = ParagraphStyle("X", fontName=FB, fontSize=6.5, textColor=tc, alignment=TA_CENTER)

        urun = h.get("urun_adi","") or "–"
        mkt = h.get("miktar",0)
        mkt_s = f"{mkt:g}" if mkt else "–"
        brm = h.get("birim","") or "–"
        bf = h.get("birim_fiyat",0)
        bf_s = _para(bf) if bf else "–"
        durum = h.get("durum","") or "–"
        od_tur = h.get("odeme_turu","") or "–"

        # Durum rengi
        if durum == "TAMAMLANDI":
            d_renk = colors.HexColor("#16a34a")
        elif durum == "KISMİ ÖDENDİ":
            d_renk = colors.HexColor("#d97706")
        else:
            d_renk = colors.HexColor("#6b7280")
        ds = ParagraphStyle("D", fontName=FB, fontSize=6.5, textColor=d_renk, alignment=TA_CENTER)

        row = [
            Paragraph(_tarih_f(h.get("tarih","")), hm),
            Paragraph(ts, tur_s),
            Paragraph(urun, hc),
            Paragraph(mkt_s, hm),
            Paragraph(brm, hm),
            Paragraph(bf_s, hr),
            Paragraph(_para(h.get("toplam",0)), hr),
            Paragraph(_para(h.get("odenen_tutar",0)), hr),
            Paragraph(_para(h.get("kalan_tutar",0)), hr),
            Paragraph(durum, ds),
            Paragraph(od_tur, hm),
            Paragraph(h.get("not","") or "", hc),
        ]
        rows.append(row)

    cw = [1.6*cm, 1.2*cm, 2.8*cm, 1.1*cm, 1.1*cm, 1.5*cm,
          1.6*cm, 1.5*cm, 1.5*cm, 1.6*cm, 1.2*cm, 2.2*cm]

    ht = Table(rows, colWidths=cw, repeatRows=1)
    tsl = [
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR",(0,0),(-1,0), colors.white),
        ("FONTSIZE",(0,0),(-1,-1), 6.5),
        ("TOPPADDING",(0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("GRID",(0,0),(-1,-1), 0.4, colors.HexColor("#d1d5db")),
    ]
    for i in range(1, len(rows)):
        bg = colors.HexColor("#f9fafb") if i % 2 == 0 else colors.white
        tsl.append(("BACKGROUND",(0,i),(-1,i), bg))
    ht.setStyle(TableStyle(tsl))
    els.append(ht); els.append(Spacer(1, 6*mm))

    # ── Özet ──
    els.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d1d5db"),
        spaceAfter=4*mm, spaceBefore=2*mm))

    sl = ParagraphStyle("OE", fontName=FB, fontSize=10,
        textColor=colors.HexColor("#374151"), alignment=TA_RIGHT)

    nb = bakiye["net_bakiye"]
    if nb < 0:
        nb_c = colors.HexColor("#dc2626")
    elif nb > 0:
        nb_c = colors.HexColor("#16a34a")
    else:
        nb_c = colors.HexColor("#1a1a2e")

    def _ov(label, val, renk=None):
        r = renk or colors.HexColor("#374151")
        vs = ParagraphStyle("OV", fontName=FB, fontSize=10, textColor=r, alignment=TA_RIGHT)
        return [Paragraph(label, sl), Paragraph(_para(val), vs)]

    ozet = [
        _ov("Toplam Borç:", bakiye["toplam_borc"], colors.HexColor("#dc2626")),
        _ov("Toplam Alacak:", bakiye["toplam_alacak"], colors.HexColor("#16a34a")),
        _ov("Toplam Ödenen:", bakiye["toplam_odenen"]),
        _ov("Toplam Tahsil Edilen:", bakiye["toplam_tahsil"]),
        _ov("Açık Borç:", bakiye["acik_borc"], colors.HexColor("#dc2626")),
        _ov("Açık Alacak:", bakiye["acik_alacak"], colors.HexColor("#16a34a")),
    ]

    # Net Bakiye büyük
    nb_s = ParagraphStyle("NB", fontName=FB, fontSize=12, textColor=nb_c, alignment=TA_RIGHT)
    ozet.append([Paragraph("NET BAKİYE:", sl), Paragraph(_para(nb), nb_s)])

    ot = Table(ozet, colWidths=[13*cm, 5.5*cm])
    ot.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LINEABOVE",(0,-1),(-1,-1),1.5, colors.HexColor("#1e293b")),
        ("TOPPADDING",(0,-1),(-1,-1),6),
    ]))
    els.append(ot); els.append(Spacer(1, 8*mm))

    els.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=2*mm))
    els.append(Paragraph("Bu ekstre CariiDefterim tarafından otomatik oluşturulmuştur.", s_foot))

    doc.build(els)
