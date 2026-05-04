# -*- coding: utf-8 -*-
"""
CariiDefterim - Kullanıcı Arayüzü Modülü (v3)
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, sys, json, csv
from datetime import datetime

import database


# =============================================================================
# TEMALAR
# =============================================================================

TEMALAR = {
    "aydinlik": {
        "bg": "#eef1f5", "surface": "#ffffff", "surface_alt": "#f7f8fa",
        "fg": "#1a1a2e", "fg_secondary": "#6b7280",
        "accent": "#2563eb", "accent_hover": "#1d4ed8", "accent_fg": "#ffffff",
        "borc": "#dc2626", "alacak": "#16a34a", "border": "#d1d5db",
        "tree_bg": "#ffffff", "tree_fg": "#1a1a2e",
        "tree_selected_bg": "#2563eb", "tree_selected_fg": "#ffffff",
        "tree_heading_bg": "#e5e7eb", "tree_heading_fg": "#374151",
        "entry_bg": "#ffffff", "entry_fg": "#1a1a2e", "entry_border": "#d1d5db",
        "danger": "#dc2626", "danger_hover": "#b91c1c", "danger_fg": "#ffffff",
        "success": "#16a34a", "success_hover": "#15803d",
        "kucuk_lbl": "#4b5563"
    },
    "karanlik": {
        "bg": "#0f172a", "surface": "#1e293b", "surface_alt": "#273548",
        "fg": "#e2e8f0", "fg_secondary": "#94a3b8",
        "accent": "#3b82f6", "accent_hover": "#60a5fa", "accent_fg": "#ffffff",
        "borc": "#f87171", "alacak": "#4ade80", "border": "#334155",
        "tree_bg": "#1e293b", "tree_fg": "#e2e8f0",
        "tree_selected_bg": "#3b82f6", "tree_selected_fg": "#ffffff",
        "tree_heading_bg": "#334155", "tree_heading_fg": "#e2e8f0",
        "entry_bg": "#1e293b", "entry_fg": "#e2e8f0", "entry_border": "#475569",
        "danger": "#ef4444", "danger_hover": "#f87171", "danger_fg": "#ffffff",
        "success": "#22c55e", "success_hover": "#4ade80",
        "kucuk_lbl": "#cbd5e1"
    }
}

ODEME_TURLERI = ["", "Nakit", "Kart", "Çek", "Havale", "EFT", "Diğer"]


# =============================================================================
# AYARLAR
# =============================================================================

def _ayar_yolu():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "ayarlar.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ayarlar.json")

def _ayarlari_yukle():
    try:
        with open(_ayar_yolu(), "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {"tema": "aydinlik", "font_boyutu": 10}

def _ayarlari_kaydet(a):
    try:
        with open(_ayar_yolu(), "w", encoding="utf-8") as f:
            json.dump(a, f)
    except: pass


# =============================================================================
# APP
# =============================================================================

class CariDefterimApp:

    def __init__(self, root):
        self.root = root
        self.root.title("CariiDefterim – Kapsamlı Cari Takibi")
        self.root.geometry("1480x880")
        self.root.minsize(1200, 700)

        self.secili_cari_id = None
        self.tam_ekran = False
        self.htree_siralama = {"col": "tarih", "asc": False}

        a = _ayarlari_yukle()
        self.tema_adi = a.get("tema", "aydinlik")
        self.font_boyutu = a.get("font_boyutu", 10)
        self.r = TEMALAR[self.tema_adi]

        self._font_ayarla()
        database.tablolari_olustur()
        self._stilleri_ayarla()
        self._menu_olustur()
        self._arayuz_olustur()
        self._cari_listesini_yukle()

        self.root.bind("<Escape>", self._tam_ekrandan_cik)
        self.root.bind("<F11>", lambda e: self._tam_ekran_degistir())
        self.root.protocol("WM_DELETE_WINDOW", self._kapat)

    def _font_ayarla(self):
        b = self.font_boyutu
        self.font = ("Segoe UI", b)
        self.font_bold = ("Segoe UI", b, "bold")
        self.font_h = ("Segoe UI", b+2, "bold")
        self.font_xl = ("Segoe UI", b+5, "bold")
        self.font_s = ("Segoe UI", max(8, b-2))

    def _stilleri_ayarla(self):
        r = self.r
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=r["tree_bg"], foreground=r["tree_fg"],
                        fieldbackground=r["tree_bg"], font=self.font, rowheight=int(self.font_boyutu*2.6))
        style.map("Treeview", background=[("selected", r["tree_selected_bg"])],
                  foreground=[("selected", r["tree_selected_fg"])])
        style.configure("Treeview.Heading", background=r["tree_heading_bg"],
                        foreground=r["tree_heading_fg"], font=self.font_bold)
        style.configure("TCombobox", fieldbackground=r["entry_bg"], background=r["bg"])

    # =========================================================================
    # YARDIMCILAR
    # =========================================================================

    def _btn(self, p, t, bg, fg, hbg, cmd):
        b = tk.Button(p, text=t, font=self.font, bg=bg, fg=fg,
                      activebackground=hbg, activeforeground=fg, relief="flat", bd=0, padx=12, pady=5,
                      cursor="hand2", command=cmd)
        b.bind("<Enter>", lambda e: b.configure(bg=hbg))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def _para(self, v):
        s = f"-{abs(v):,.2f}" if v < 0 else f"{v:,.2f}"
        return s.replace(",","X").replace(".",",").replace("X",".") + " ₺"

    def _tarih_getir(self, t):
        try:
            p = t.split("-")
            return f"{p[2]}.{p[1]}.{p[0]}"
        except: return t

    def _tarih_kaydet(self, t):
        p = t.strip().split(".")
        if len(p)!=3: raise ValueError
        return f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}"

    def _float(self, val):
        if not str(val).strip(): return 0.0
        return float(str(val).replace(",","."))

    # =========================================================================
    # MENÜ
    # =========================================================================

    def _menu_olustur(self):
        r = self.r
        mb = tk.Menu(self.root, bg=r["surface"], fg=r["fg"], font=self.font, relief="flat")

        dosya = tk.Menu(mb, tearoff=0, bg=r["surface"], fg=r["fg"], font=self.font)
        dosya.add_command(label="💾 Yedek Al", command=self._yedek_al)
        dosya.add_command(label="📋 PDF Ekstre Seçili", command=self._pdf_ekstre_olustur)
        dosya.add_command(label="❌ Çıkış", command=self._kapat)
        mb.add_cascade(label=" Dosya ", menu=dosya)

        gorunum = tk.Menu(mb, tearoff=0, bg=r["surface"], fg=r["fg"], font=self.font)
        gorunum.add_command(label="🔼 Yazı Büyüt", command=self._font_buyut)
        gorunum.add_command(label="🔽 Yazı Küçült", command=self._font_kucult)
        gorunum.add_command(label="☀️ Aydınlık Tema", command=lambda: self._tema("aydinlik"))
        gorunum.add_command(label="🌙 Karanlık Tema", command=lambda: self._tema("karanlik"))
        mb.add_cascade(label=" Görünüm ", menu=gorunum)

        self.root.config(menu=mb)

    # =========================================================================
    # ANA ARAYÜZ
    # =========================================================================

    def _arayuz_olustur(self):
        r = self.r
        self.ana = tk.Frame(self.root, bg=r["bg"])
        self.ana.pack(fill="both", expand=True)

        ust = tk.Frame(self.ana, bg=r["surface"], pady=6, padx=12)
        ust.pack(fill="x")
        tk.Label(ust, text="CariiDefterim", font=self.font_xl, bg=r["surface"], fg=r["accent"]).pack(side="left")

        af = tk.Frame(ust, bg=r["surface"])
        af.pack(side="left", padx=20, fill="x", expand=True)
        tk.Label(af, text="🔍", font=self.font, bg=r["surface"], fg=r["fg_secondary"]).pack(side="left")
        self.arama_var = tk.StringVar()
        self.arama_var.trace_add("write", lambda *a: self._cari_listesini_yukle())
        tk.Entry(af, textvariable=self.arama_var, font=self.font, bg=r["entry_bg"], fg=r["entry_fg"],
                 relief="flat", bd=1, highlightthickness=1, highlightcolor=r["accent"]).pack(side="left", fill="x", expand=True, padx=5, ipady=3)

        self.ic = tk.Frame(self.ana, bg=r["bg"])
        self.ic.pack(fill="both", expand=True, padx=8, pady=8)

        self._sol_panel(self.ic)
        self._sag_panel(self.ic)

    # =========================================================================
    # SOL PANEL (CARİ LİSTESİ)
    # =========================================================================

    def _sol_panel(self, p):
        r = self.r
        sol = tk.Frame(p, bg=r["bg"], width=320)
        sol.pack(side="left", fill="y", padx=(0,5))
        sol.pack_propagate(False)

        tk.Label(sol, text="📋 Müşteriler", font=self.font_h, bg=r["bg"], fg=r["fg"]).pack(anchor="w", pady=(0,5))

        self.ctree = ttk.Treeview(sol, columns=("ad","bak"), show="headings", selectmode="browse")
        self.ctree.heading("ad", text="Ad Soyad")
        self.ctree.heading("bak", text="Bakiye")
        self.ctree.column("ad", width=190)
        self.ctree.column("bak", width=100, anchor="e")
        self.ctree.tag_configure("borclu", foreground=r["borc"])
        self.ctree.tag_configure("alacakli", foreground=r["alacak"])
        self.ctree.tag_configure("notr", foreground=r["fg"])

        sc = ttk.Scrollbar(sol, orient="vertical", command=self.ctree.yview)
        self.ctree.configure(yscrollcommand=sc.set)
        self.ctree.pack(side="top", fill="both", expand=True)
        sc.place(relx=1, rely=0, relheight=1, anchor="ne")

        self.ctree.bind("<<TreeviewSelect>>", self._on_cari_sec)

        bf = tk.Frame(sol, bg=r["bg"], pady=8)
        bf.pack(anchor="center")
        self._btn(bf, "➕", r["accent"], r["accent_fg"], r["accent_hover"], self._cari_ekle).pack(side="left", padx=4)
        self._btn(bf, "✏️", r["success"], "#fff", r["success_hover"], self._cari_guncelle).pack(side="left", padx=4)
        self._btn(bf, "🗑️", r["danger"], r["danger_fg"], r["danger_hover"], self._cari_sil).pack(side="left", padx=4)

    def _cari_listesini_yukle(self):
        for i in self.ctree.get_children(): self.ctree.delete(i)
        cariler = database.cari_listesi(self.arama_var.get().strip())
        for c in cariler:
            b = c["bakiye"]
            t = "borclu" if b < 0 else ("alacakli" if b > 0 else "notr")
            self.ctree.insert("", "end", iid=str(c["id"]), values=(c["ad_soyad"], self._para(b)), tags=(t,))
        if self.secili_cari_id:
            try:
                self.ctree.selection_set(str(self.secili_cari_id))
                self.ctree.see(str(self.secili_cari_id))
            except: pass

    # =========================================================================
    # SAĞ PANEL (DETAY VE HAREKETLER)
    # =========================================================================

    def _sag_panel(self, p):
        r = self.r
        self.sag = tk.Frame(p, bg=r["bg"])
        self.sag.pack(side="left", fill="both", expand=True)

        # -- ÖZET PANOSU --
        ozet_f = tk.Frame(self.sag, bg=r["surface"], highlightbackground=r["border"], highlightthickness=1)
        ozet_f.pack(fill="x", pady=(0,8), ipady=5, ipadx=10)

        # Başlık ve Adres satırı
        self.l_cari_ad = tk.Label(ozet_f, text="Lütfen cari seçin", font=self.font_xl, bg=r["surface"], fg=r["fg"])
        self.l_cari_ad.grid(row=0, column=0, columnspan=2, sticky="w", pady=(5,0))

        self.l_telefon = tk.Label(ozet_f, text="", font=self.font, bg=r["surface"], fg=r["fg_secondary"])
        self.l_telefon.grid(row=1, column=0, sticky="w")
        self.l_adres = tk.Label(ozet_f, text="", font=self.font, bg=r["surface"], fg=r["fg_secondary"])
        self.l_adres.grid(row=1, column=1, sticky="w", padx=20)

        # Bakiye Kutu Paneli
        bkf = tk.Frame(self.sag, bg=r["bg"])
        bkf.pack(fill="x", pady=(0,8))

        def _kutu(parent, text):
            f = tk.Frame(parent, bg=r["surface"], highlightbackground=r["border"], highlightthickness=1, padx=10, pady=5)
            tk.Label(f, text=text, font=self.font_s, bg=r["surface"], fg=r["kucuk_lbl"]).pack(anchor="w")
            l = tk.Label(f, text="0,00 ₺", font=self.font_bold, bg=r["surface"])
            l.pack(anchor="w")
            return f, l

        f_borc, self.l_tborc = _kutu(bkf, "T.Borç")
        f_alac, self.l_talac = _kutu(bkf, "T.Alacak")
        f_oden, self.l_toden = _kutu(bkf, "T.Ödenen")
        f_tahs, self.l_ttahs = _kutu(bkf, "T.Tahsil")
        f_aborc, self.l_aborc = _kutu(bkf, "Açık Borç")
        f_aalac, self.l_aalac = _kutu(bkf, "Açık Alacak")

        # Net bakiye büyük kutu
        f_net = tk.Frame(bkf, bg=r["surface"], highlightbackground=r["border"], highlightthickness=1, padx=15, pady=5)
        tk.Label(f_net, text="NET BAKİYE", font=self.font_s, bg=r["surface"], fg=r["kucuk_lbl"]).pack(anchor="e")
        self.l_net = tk.Label(f_net, text="0,00 ₺", font=self.font_xl, bg=r["surface"])
        self.l_net.pack(anchor="e")

        f_borc.pack(side="left", fill="x", expand=True, padx=(0,2))
        f_alac.pack(side="left", fill="x", expand=True, padx=2)
        f_oden.pack(side="left", fill="x", expand=True, padx=2)
        f_tahs.pack(side="left", fill="x", expand=True, padx=2)
        f_aborc.pack(side="left", fill="x", expand=True, padx=2)
        f_aalac.pack(side="left", fill="x", expand=True, padx=2)
        f_net.pack(side="right", padx=(2,0))

        # -- HAREKETLER TABLOSU --
        hf = tk.Frame(self.sag, bg=r["bg"])
        hf.pack(fill="both", expand=True)

        cols = ("tarih", "tur", "urun", "miktar", "birim", "bfiyat", "toplam", "odenen", "kalan", "durum", "oturu", "not")
        self.htree = ttk.Treeview(hf, columns=cols, show="headings", selectmode="browse")

        hdgs = [("tarih","Tarih",80), ("tur","Tür",60), ("urun","Ürün/Açıkl.",140),
                ("miktar","Mkt",45), ("birim","Brm",45), ("bfiyat","B.Fiyat",70),
                ("toplam","Toplam",80), ("odenen","Ödenen",80), ("kalan","Kalan",80),
                ("durum","Durum",80), ("oturu","Ö.Türü",70), ("not","Not",100)]

        for c, t, w in hdgs:
            self.htree.heading(c, text=t, command=lambda _c=c: self._htree_sort(_c))
            a = "center" if c in ("tarih","tur","miktar","birim","durum","oturu") else ("e" if c in ("bfiyat","toplam","odenen","kalan") else "w")
            self.htree.column(c, width=w, minwidth=w, anchor=a)

        self.htree.tag_configure("BORC", foreground=r["borc"])
        self.htree.tag_configure("ALACAK", foreground=r["alacak"])
        self.htree.tag_configure("TAMAM", foreground=r["fg_secondary"])

        hsc = ttk.Scrollbar(hf, orient="vertical", command=self.htree.yview)
        self.htree.configure(yscrollcommand=hsc.set)
        self.htree.pack(side="left", fill="both", expand=True)
        hsc.pack(side="right", fill="y")

        self.htree.bind("<Double-1>", lambda e: self._hareket_duzenle())

        # -- ALT BUTONLAR --
        ab = tk.Frame(self.sag, bg=r["bg"], pady=8)
        ab.pack(anchor="center")
        self._btn(ab, "💰 Yeni İşlem", r["accent"], r["accent_fg"], r["accent_hover"], self._islem_ekle).pack(side="left", padx=6)
        self._btn(ab, "✏️ Düzenle", r["success"], "#fff", r["success_hover"], self._hareket_duzenle).pack(side="left", padx=6)
        self._btn(ab, "🗑️ Sil", r["danger"], r["danger_fg"], r["danger_hover"], self._hareket_sil).pack(side="left", padx=6)

    def _on_cari_sec(self, e):
        s = self.ctree.selection()
        if s:
            self.secili_cari_id = int(s[0])
            self._detayi_guncelle()
        else:
            self.secili_cari_id = None

    def _detayi_guncelle(self):
        r = self.r
        if not self.secili_cari_id:
            self.l_cari_ad.config(text="Cari seçilmedi")
            for i in self.htree.get_children(): self.htree.delete(i)
            return

        c = database.cari_detay(self.secili_cari_id)
        if not c: return
        self.l_cari_ad.config(text=c["ad_soyad"])
        self.l_telefon.config(text=c["telefon"] or "")
        self.l_adres.config(text=c["adres"] or "")

        bak = database.bakiye_bilgisi(self.secili_cari_id)
        self.l_tborc.config(text=self._para(bak["toplam_borc"]), fg=r["borc"])
        self.l_talac.config(text=self._para(bak["toplam_alacak"]), fg=r["alacak"])
        self.l_toden.config(text=self._para(bak["toplam_odenen"]))
        self.l_ttahs.config(text=self._para(bak["toplam_tahsil"]))
        self.l_aborc.config(text=self._para(bak["acik_borc"]), fg=r["borc"])
        self.l_aalac.config(text=self._para(bak["acik_alacak"]), fg=r["alacak"])

        nb = bak["net_bakiye"]
        nrenk = r["borc"] if nb < 0 else (r["alacak"] if nb > 0 else r["fg"])
        self.l_net.config(text=self._para(nb), fg=nrenk)

        self._hareketleri_yukle()

    def _hareketleri_yukle(self):
        for i in self.htree.get_children(): self.htree.delete(i)
        if not self.secili_cari_id: return

        hl = database.hareketler_listesi(self.secili_cari_id)

        # Basit sıralama
        col = self.htree_siralama["col"]
        asc = self.htree_siralama["asc"]
        if col == "tarih":
            hl.sort(key=lambda x: (x["tarih"], x["id"]), reverse=not asc)
        elif col in ("odenen","kalan","toplam","bfiyat","miktar"):
            k = {"odenen":"odenen_tutar", "kalan":"kalan_tutar", "toplam":"toplam", "bfiyat":"birim_fiyat", "miktar":"miktar"}
            hl.sort(key=lambda x: x[k[col]], reverse=not asc)

        for h in hl:
            t = "BORÇ" if h["tur"]=="BORC" else "ALACAK"
            tg = h["tur"]
            if h["durum"] == "TAMAMLANDI": tg = "TAMAM"

            vals = (
                self._tarih_getir(h["tarih"]), t, h["urun_adi"],
                f"{h['miktar']:g}" if h['miktar'] else "", h["birim"] or "",
                self._para(h["birim_fiyat"]) if h["birim_fiyat"] else "",
                self._para(h["toplam"]), self._para(h["odenen_tutar"]), self._para(h["kalan_tutar"]),
                h["durum"], h["odeme_turu"], h["not"]
            )
            self.htree.insert("", "end", iid=str(h["id"]), values=vals, tags=(tg,))

    def _htree_sort(self, col):
        if self.htree_siralama["col"] == col:
            self.htree_siralama["asc"] = not self.htree_siralama["asc"]
        else:
            self.htree_siralama["col"] = col
            self.htree_siralama["asc"] = True
        self._hareketleri_yukle()

    # =========================================================================
    # CARİ CRUD
    # =========================================================================

    def _dialog(self, title, w, h):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.configure(bg=self.r["surface"])
        d.geometry(f"{w}x{h}")
        d.transient(self.root); d.grab_set()
        x = self.root.winfo_x() + (self.root.winfo_width()-w)//2
        y = self.root.winfo_y() + (self.root.winfo_height()-h)//2
        d.geometry(f"+{x}+{y}")
        return d

    def _tk_lbl_ent(self, p, r, title, val=""):
        tk.Label(p, text=title, font=self.font_bold, bg=self.r["surface"], fg=self.r["fg"]).grid(row=r, column=0, sticky="w", pady=4, padx=(0,5))
        e = tk.Entry(p, font=self.font, bg=self.r["entry_bg"], fg=self.r["entry_fg"], relief="flat", bd=1, highlightthickness=1)
        e.grid(row=r, column=1, sticky="w", pady=4)
        if val: e.insert(0, str(val))
        return e

    def _cari_ekle(self):
        d = self._dialog("Yeni Cari", 350, 250)
        f = tk.Frame(d, bg=self.r["surface"], padx=15, pady=15); f.pack()
        ea = self._tk_lbl_ent(f, 0, "Ad Soyad:")
        et = self._tk_lbl_ent(f, 1, "Telefon:")
        ed = self._tk_lbl_ent(f, 2, "Adres:")
        ea.focus_set()

        def save():
            ad = ea.get().strip()
            if not ad: return messagebox.showwarning("!", "Ad gerekli", parent=d)
            database.cari_ekle(ad, et.get(), ed.get())
            self._cari_listesini_yukle(); d.destroy()
        self._btn(d, "Kaydet", self.r["accent"], "#fff", self.r["accent_hover"], save).pack()

    def _cari_guncelle(self):
        if not self.secili_cari_id: return
        c = database.cari_detay(self.secili_cari_id)
        d = self._dialog("Cari Güncelle", 350, 250)
        f = tk.Frame(d, bg=self.r["surface"], padx=15, pady=15); f.pack()
        ea = self._tk_lbl_ent(f, 0, "Ad Soyad:", c["ad_soyad"])
        et = self._tk_lbl_ent(f, 1, "Telefon:", c["telefon"])
        ed = self._tk_lbl_ent(f, 2, "Adres:", c["adres"])

        def save():
            ad = ea.get().strip()
            if not ad: return
            database.cari_guncelle(c["id"], ad, et.get(), ed.get())
            self._cari_listesini_yukle(); self._detayi_guncelle(); d.destroy()
        self._btn(d, "Kaydet", self.r["accent"], "#fff", self.r["accent_hover"], save).pack()

    def _cari_sil(self):
        if not self.secili_cari_id: return
        cr = database.cari_detay(self.secili_cari_id)
        if messagebox.askyesno("Emin misiniz?", f"'{cr['ad_soyad']}' silinecek!"):
            database.cari_sil(self.secili_cari_id)
            self.secili_cari_id = None
            self._cari_listesini_yukle()
            self._detayi_guncelle()

    # =========================================================================
    # İŞLEM (HAREKET) EKLE / GÜNCELLE
    # =========================================================================

    def _islem_ekle(self):
        if not self.secili_cari_id: return messagebox.showinfo("!","Cari seçin")
        self._islem_formu()

    def _hareket_duzenle(self):
        s = self.htree.selection()
        if not s: return messagebox.showinfo("!","İşlem seçin")
        hid = int(s[0])
        h = database.hareket_detay(hid)
        self._islem_formu(h)

    def _hareket_sil(self):
        s = self.htree.selection()
        if not s: return
        if messagebox.askyesno("?","Seçili işlem silinecek?"):
            database.hareket_sil(int(s[0]))
            self._cari_listesini_yukle()
            self._detayi_guncelle()

    def _islem_formu(self, veri=None):
        md = "Ekle" if not veri else "Düzenle"
        r = self.r
        d = self._dialog(f"İşlem {md}", 550, 520)

        # Form grid'i
        f = tk.Frame(d, bg=r["surface"], padx=20, pady=15)
        f.pack(fill="both", expand=True)

        v_tarih = self._tarih_getir(veri["tarih"]) if veri else datetime.now().strftime("%d.%m.%Y")
        e_tar = self._tk_lbl_ent(f, 0, "Tarih:", v_tarih)

        tk.Label(f, text="İşlem Tipi:", font=self.font_bold, bg=r["surface"], fg=r["fg"]).grid(row=1, column=0, sticky="w")
        cb_tur = ttk.Combobox(f, values=["BORÇ", "ALACAK"], state="readonly", font=self.font, width=17)
        cb_tur.grid(row=1, column=1, sticky="w", pady=4)
        v_tur = "BORÇ" if not veri else ("BORÇ" if veri["tur"]=="BORC" else "ALACAK")
        cb_tur.set(v_tur)

        # Ürün Bilgileri (Opsiyonel)
        tk.Label(f, text="--- Ürün Bilgisi (Opsiyonel) ---", font=self.font_s, bg=r["surface"], fg=r["fg_secondary"]).grid(row=2, columnspan=2, pady=(10,5))

        e_urun = self._tk_lbl_ent(f, 3, "Ürün/Hizmet:", veri["urun_adi"] if veri else "")

        fr_mkt = tk.Frame(f, bg=r["surface"])
        fr_mkt.grid(row=4, column=1, sticky="w", pady=4)
        tk.Label(f, text="Miktar & Birim:", font=self.font_bold, bg=r["surface"], fg=r["fg"]).grid(row=4, column=0, sticky="w")
        v_mkt = str(veri["miktar"]) if veri and veri["miktar"] else ""
        e_mkt = tk.Entry(fr_mkt, font=self.font, width=8)
        e_mkt.pack(side="left")
        e_mkt.insert(0, v_mkt)
        v_brm = veri["birim"] if veri else ""
        cb_brm = ttk.Combobox(fr_mkt, values=["Adet","Kg","Litre","Metre","Ay","Saat"], font=self.font, width=7)
        cb_brm.pack(side="left", padx=5)
        cb_brm.set(v_brm)

        v_bfiyat = str(veri["birim_fiyat"]) if veri and veri["birim_fiyat"] else ""
        e_bfiyat = self._tk_lbl_ent(f, 5, "Birim Fiyat:", v_bfiyat)

        # Finans
        tk.Label(f, text="--- Tutar ve Ödeme ---", font=self.font_s, bg=r["surface"], fg=r["fg_secondary"]).grid(row=6, columnspan=2, pady=(10,5))

        e_toplam = self._tk_lbl_ent(f, 7, "*Toplam Tutar (₺):", veri["toplam"] if veri else "")
        e_toplam.config(font=self.font_bold, fg=r["accent"])

        e_odenen = self._tk_lbl_ent(f, 8, "Ödenen/Tahsil (₺):", veri["odenen_tutar"] if veri else "0")

        tk.Label(f, text="Ödeme Türü:", font=self.font_bold, bg=r["surface"], fg=r["fg"]).grid(row=9, column=0, sticky="w")
        cb_odeme = ttk.Combobox(f, values=ODEME_TURLERI, state="readonly", font=self.font, width=17)
        cb_odeme.grid(row=9, column=1, sticky="w", pady=4)
        cb_odeme.set(veri["odeme_turu"] if veri else "")

        e_not = self._tk_lbl_ent(f, 10, "Not/Açıklama:", veri["not"] if veri else "")

        # Otomatik Hesaplama
        def _calc(*a):
            try:
                m = self._float(e_mkt.get())
                b = self._float(e_bfiyat.get())
                if m > 0 and b > 0:
                    e_toplam.delete(0, "end")
                    e_toplam.insert(0, str(round(m*b, 2)))
            except: pass
        e_mkt.bind("<KeyRelease>", _calc)
        e_bfiyat.bind("<KeyRelease>", _calc)

        # Kaydet
        def _save():
            try: tar = self._tarih_kaydet(e_tar.get())
            except: return messagebox.showwarning("!","Geçersiz tarih GG.AA.YYYY", parent=d)

            tur = "BORC" if cb_tur.get()=="BORÇ" else "ALACAK"
            toplam = self._float(e_toplam.get())
            if toplam <= 0: return messagebox.showwarning("!","Toplam tutar 0'dan büyük olmalı", parent=d)
            odenen = self._float(e_odenen.get())

            args = (
                tar, tur, toplam, e_urun.get().strip(),
                self._float(e_mkt.get()), cb_brm.get().strip(), self._float(e_bfiyat.get()),
                e_not.get().strip(), cb_odeme.get().strip(), odenen
            )

            if veri:
                database.hareket_guncelle(veri["id"], *args)
            else:
                database.hareket_ekle(self.secili_cari_id, *args)

            self._cari_listesini_yukle()
            self._detayi_guncelle()
            d.destroy()

        bf = tk.Frame(d, bg=r["surface"])
        bf.pack(pady=10)
        self._btn(bf, "✅ KAYDET", r["accent"], "#fff", r["accent_hover"], _save).pack()


    # =========================================================================
    # DİĞERLERİ
    # =========================================================================

    def _PDF(self): self._pdf_ekstre_olustur()

    def _pdf_ekstre_olustur(self):
        if not self.secili_cari_id: return messagebox.showinfo("!","Cari seçin")
        
        d = self._dialog("PDF Çıktı Seçenekleri", 380, 260)
        tk.Label(d, text="Hangi kayıtlar eklensin?", font=self.font_h, bg=self.r["surface"], fg=self.r["fg"]).pack(pady=10)
        
        v = tk.StringVar(value="TÜM")
        rb_bg = self.r["surface"]
        tk.Radiobutton(d, text="Tüm hareketler (Borç ve Alacak)", variable=v, value="TÜM", bg=rb_bg, fg=self.r["fg"], font=self.font, selectcolor=self.r["bg"]).pack(anchor="w", padx=30, pady=5)
        tk.Radiobutton(d, text="Sadece alacaklı olduğum kayıtlar (Borç İşlemleri)", variable=v, value="ALACAKLIYIM", bg=rb_bg, fg=self.r["fg"], font=self.font, selectcolor=self.r["bg"]).pack(anchor="w", padx=30, pady=5)
        tk.Radiobutton(d, text="Sadece borçlu olduğum kayıtlar (Alacak İşlemleri)", variable=v, value="BORCLUYUM", bg=rb_bg, fg=self.r["fg"], font=self.font, selectcolor=self.r["bg"]).pack(anchor="w", padx=30, pady=5)
        
        def _olustur():
            secim = v.get()
            d.destroy()
            self._pdf_gercekten_olustur(secim)
            
        self._btn(d, "📄 PDF Oluştur", self.r["accent"], "#fff", self.r["accent_hover"], _olustur).pack(pady=15)

    def _pdf_gercekten_olustur(self, filtre_tipi):
        try: import pdf_export
        except: return messagebox.showwarning("!", "reportlab kurulu değil.")

        c = database.cari_detay(self.secili_cari_id)
        z = datetime.now().strftime("%Y%m%d_%H%M")
        g = c["ad_soyad"].replace(" ","_")
        h = filedialog.asksaveasfilename(initialfile=f"{g}_{z}.pdf", defaultextension=".pdf")
        if not h: return

        hl = database.hareketler_listesi(self.secili_cari_id)
        
        # Filtreleme
        if filtre_tipi == "ALACAKLIYIM":
            hl = [x for x in hl if x['tur'] == 'BORC']
        elif filtre_tipi == "BORCLUYUM":
            hl = [x for x in hl if x['tur'] == 'ALACAK']
            
        # Filtreye özel bakiye hesaplaması
        bak = {
            "toplam_borc": sum(self._float(x["toplam"]) for x in hl if x["tur"] == "BORC"),
            "toplam_alacak": sum(self._float(x["toplam"]) for x in hl if x["tur"] == "ALACAK"),
            "toplam_odenen": sum(self._float(x["odenen_tutar"]) for x in hl if x["tur"] == "BORC"),
            "toplam_tahsil": sum(self._float(x["odenen_tutar"]) for x in hl if x["tur"] == "ALACAK"),
            "acik_borc": sum(self._float(x["kalan_tutar"]) for x in hl if x["tur"] == "BORC"),
            "acik_alacak": sum(self._float(x["kalan_tutar"]) for x in hl if x["tur"] == "ALACAK"),
        }
        bak["net_bakiye"] = bak["acik_alacak"] - bak["acik_borc"]

        pdf_export.ekstre_olustur(h, c, hl, bak)
        if os.path.exists(h): os.startfile(h)

    def _yedek_al(self):
        h = filedialog.asksaveasfilename(initialfile="yedek.db", defaultextension=".db")
        if h:
            database.veritabani_yedekle(h)
            messagebox.showinfo("!", "Yedek alındı.")

    def _tema(self, t):
        self.tema_adi = t
        self.r = TEMALAR[t]
        _ayarlari_kaydet({"tema":t, "font_boyutu":self.font_boyutu})
        self.root.destroy()
        from main import main; main()

    def _font_buyut(self):
        self.font_boyutu += 1
        _ayarlari_kaydet({"tema":self.tema_adi, "font_boyutu":self.font_boyutu})
        self.root.destroy()
        from main import main; main()

    def _font_kucult(self):
        if self.font_boyutu > 8:
            self.font_boyutu -= 1
            _ayarlari_kaydet({"tema":self.tema_adi, "font_boyutu":self.font_boyutu})
            self.root.destroy()
            from main import main; main()

    def _tam_ekran_degistir(self):
        self.tam_ekran = not self.tam_ekran
        self.root.attributes("-fullscreen", self.tam_ekran)

    def _tam_ekrandan_cik(self, e):
        self.tam_ekran = False
        self.root.attributes("-fullscreen", False)

    def _kapat(self):
        self.root.destroy()
