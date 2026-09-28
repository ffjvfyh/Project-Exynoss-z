from base64 import b64decode, b64encode
import hashlib
import importlib.util
import io
import ipaddress
import json
import math
import os
import platform
from pathlib import Path
import re
import secrets
import socket
import ssl
import stat
import string
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, simpledialog
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen


DEPENDENCIES = {
    "rich": {"required": True, "label": "Rich arayüzü"},
    "customtkinter": {"required": True, "label": "modern masaüstü arayüzü"},
    "psutil": {"required": False, "label": "sistem bilgileri"},
    "pygame": {"required": False, "label": "müzik desteği"},
}


def gerekli_kutuphaneyi_kur():
    eksikler = [paket for paket in DEPENDENCIES if importlib.util.find_spec(paket) is None]
    if not eksikler:
        return

    print("Eksik kütüphaneler kontrol ediliyor...")
    for paket in eksikler:
        print(f"{paket} kuruluyor ({DEPENDENCIES[paket]['label']})...")
        sonuc = subprocess.run(
            [sys.executable, "-m", "pip", "install", paket],
            check=False,
        )
        if sonuc.returncode != 0 and DEPENDENCIES[paket]["required"]:
            raise RuntimeError(
                f"Gerekli kütüphane kurulamadı: {paket}. "
                "İnternet bağlantısını ve pip kurulumunu kontrol edin."
            )

    kurulamayanlar = [
        paket for paket in eksikler
        if importlib.util.find_spec(paket) is None
    ]
    if kurulamayanlar:
        print(f"İsteğe bağlı kütüphaneler kullanılamayacak: {', '.join(kurulamayanlar)}")
    else:
        print("Eksik kütüphaneler başarıyla kuruldu.")


gerekli_kutuphaneyi_kur()

import customtkinter as ctk

try:
    import winreg
except ImportError:
    winreg = None

try:
    import winsound
except ImportError:
    winsound = None

try:
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame
except ImportError:
    pygame = None

try:
    import psutil
except ImportError:
    psutil = None

from rich import box, print as rich_print
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
URL_TIMEOUT = 5
GUI_OUTPUT = None


def print(*objects, **kwargs):
    if GUI_OUTPUT is None:
        rich_print(*objects, **kwargs)
        return
    buffer = io.StringIO()
    output_console = Console(file=buffer, color_system=None, force_terminal=False, width=120)
    output_console.print(*objects, **kwargs)
    GUI_OUTPUT(buffer.getvalue())

UI_THEME = {
    "primary": (0, 255, 170),
    "secondary": (0, 200, 255),
    "danger": (255, 100, 100),
}

THEME_PRESETS = {
    "neon": {"primary": (0, 255, 170), "secondary": (0, 200, 255), "danger": (255, 100, 100)},
    "cyan": {"primary": (0, 214, 255), "secondary": (102, 204, 255), "danger": (255, 120, 120)},
    "magenta": {"primary": (255, 95, 210), "secondary": (255, 170, 243), "danger": (255, 110, 110)},
    "amber": {"primary": (255, 180, 0), "secondary": (255, 210, 102), "danger": (255, 92, 92)},
}


def rgb_style(rgb):
    r, g, b = rgb
    return f"rgb({r},{g},{b})"


def live_theme_preview(title="LIVE RGB PREVIEW"):
    primary = rgb_style(UI_THEME["primary"])
    secondary = rgb_style(UI_THEME["secondary"])
    danger = rgb_style(UI_THEME["danger"])
    console.print(Panel(
        Group(
            f"[bold {primary}]●[/bold {primary}] Ana renk: {primary}",
            f"[bold {secondary}]●[/bold {secondary}] İkincil renk: {secondary}",
            f"[bold {danger}]●[/bold {danger}] Uyarı rengi: {danger}",
            "",
            f"[bold {primary}]EXYNOSS-Z[/bold {primary}]   [bold {secondary}]SECURITY TOOLKIT[/bold {secondary}]",
        ),
        title=f"[bold {primary}]{title}[/bold {primary}]",
        border_style=primary,
        box=box.ROUNDED,
    ))


def normalize_url(adres, default_scheme="https"):
    adres = str(adres).strip().strip('"')
    if not adres:
        return ""
    if "://" not in adres:
        if adres.startswith("localhost") or "." in adres or ":" in adres:
            return f"{default_scheme}://{adres}"
        return f"{default_scheme}://{adres}"
    return adres


def safe_json_request(url, timeout=URL_TIMEOUT):
    try:
        istek = Request(
            url,
            headers={"User-Agent": "EXYNOSS-Z Security Toolkit/0.3"},
        )
        with urlopen(istek, timeout=timeout) as yanit:
            icerik = yanit.read()
        return json.loads(icerik.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


VPN_SAGLAYICI_IPUCLARI = (
    "vpn", "proxy", "hosting", "cloud", "datacamp", "data center", "datacenter",
    "colocation", "server", "digitalocean", "ovh", "hetzner",
    "amazon", "aws", "microsoft azure", "google cloud", "oracle cloud",
    "vultr", "linode", "nordvpn", "expressvpn", "surfshark", "proton",
)

muzik_durumu = False
muzik_dosyasi = None


def pop_muzigi_degistir():
    global muzik_durumu, muzik_dosyasi
    if winsound is None and pygame is None:
        print("[yellow]Müzik için pygame kurulmalı veya Windows kullanılmalı.[/yellow]")
        return
    if muzik_durumu:
        muzik_durumu = False
        if pygame is not None and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        print("[yellow]Pop müzik kapatıldı.[/yellow]")
    else:
        if muzik_dosyasi is None:
            yol = console.input("[yellow]Müzik dosyasının yolu (WAV/MP3/OGG/M4A/FLAC): [/yellow]").strip().strip('"')
            aday = Path(yol)
            desteklenen = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
            if not aday.is_file() or aday.suffix.lower() not in desteklenen:
                print("[red]Geçerli bir WAV, MP3, OGG, M4A veya FLAC dosyası seçin.[/red]")
                return
            muzik_dosyasi = str(aday)
        if pygame is not None:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(muzik_dosyasi)
                pygame.mixer.music.play(-1)
            except pygame.error as hata:
                print(f"[red]Müzik oynatılamadı: {hata}[/red]")
                return
        elif Path(muzik_dosyasi).suffix.lower() == ".wav" and winsound is not None:
            winsound.PlaySound(muzik_dosyasi, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        else:
            print("[red]Bu format için pygame kurulmalı: pip install pygame[/red]")
            return
        muzik_durumu = True
        print(f"[green]Müzik açıldı:[/green] {muzik_dosyasi}")


def ana_menuye_don():
    print("\n[cyan]Ana menüye dönülüyor...[/cyan]")
    for kalan in range(10, 0, -1):
        print(f"[yellow]{kalan} saniye kaldı...[/yellow]", end="\r")
        time.sleep(1)
    print("[green]Ana menü açılıyor.          [/green]")


def baslik_goster():
    primary = rgb_style(UI_THEME["primary"])
    secondary = rgb_style(UI_THEME["secondary"])
    danger = rgb_style(UI_THEME["danger"])
    banner = Text()
    banner.append("EXYNOSS-Z", style=f"bold {secondary}")
    banner.append("  //  Defense Toolkit", style=f"dim {primary}")
    header = Panel(
        Group(
            Align.center(banner),
            Align.center(f"[bold {primary}]●[/bold {primary}] [dim]LOCAL CONSOLE[/dim]   [bold {secondary}]●[/bold {secondary}]   [dim]SAFE MODE[/dim]"),
        ),
        title=f"[bold {danger}]SECURITY TOOLKIT[/bold {danger}]",
        subtitle=f"[dim]{datetime.now():%d.%m.%Y  %H:%M}[/dim]",
        border_style=primary,
        box=box.DOUBLE,
        padding=(1, 3),
    )
    console.print(header)


def sistem_durumu_paneli():
    primary = rgb_style(UI_THEME["primary"])
    sicaklik = "Okunamadı"
    ram = "Okunamadı"
    if psutil is not None:
        try:
            ram = f"{psutil.Process().memory_info().rss / (1024 ** 2):.1f} MB"
        except (OSError, psutil.Error):
            pass
        try:
            sicakliklar = psutil.sensors_temperatures()
            degerler = [
                sicaklik.current
                for sensorler in sicakliklar.values()
                for sicaklik in sensorler
                if sicaklik.current is not None
            ]
            if degerler:
                sicaklik = f"{max(degerler):.1f} °C"
        except (AttributeError, OSError, psutil.Error):
            pass
    if sicaklik == "Okunamadı" and platform.system() == "Windows":
        try:
            komut = (
                "(Get-CimInstance -Namespace root/wmi "
                "-ClassName MSAcpi_ThermalZoneTemperature | "
                "Select-Object -First 1 -ExpandProperty CurrentTemperature)"
            )
            sonuc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", komut],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            deger = float(sonuc.stdout.strip())
            sicaklik = f"{deger / 10 - 273.15:.1f} °C"
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    durum = Table.grid(padding=(0, 1))
    durum.add_column(style=primary)
    durum.add_column(style="bold white")
    durum.add_row("CPU sıcaklığı", sicaklik)
    durum.add_row("Uygulama RAM", ram)
    durum.add_row("Müzik", "Açık" if muzik_durumu else "Kapalı")
    durum.add_row("Durum", "Hazır")
    return Panel(durum, title=f"[bold {primary}]SYSTEM STATUS[/bold {primary}]", border_style=primary, box=box.ROUNDED)


def menu_goster():
    primary = rgb_style(UI_THEME["primary"])
    secondary = rgb_style(UI_THEME["secondary"])
    tablo = Table(
        show_header=True,
        header_style=f"bold {primary}",
        border_style=primary,
        box=box.SIMPLE_HEAVY,
        expand=True,
        pad_edge=False,
    )
    tablo.add_column("#", style=f"bold {secondary}", justify="center", width=5)
    tablo.add_column("Kategori", style=f"bold {secondary}", width=15)
    tablo.add_column("Araç", style="white")
    araclar = [
        ("1", "KİMLİK", "Güvenli şifre oluştur"), ("2", "SİSTEM", "Program hakkında bilgi"),
        ("3", "KİMLİK", "Metin hash'le"), ("4", "KİMLİK", "Base64 kodla/çöz"),
        ("5", "KİMLİK", "Şifre gücünü kontrol et"), ("6", "AĞ", "IP/CIDR bilgisi göster"),
        ("7", "WEB", "URL analiz et"), ("8", "AĞ", "Port kontrolü yap"),
        ("9", "DOSYA", "Dosya hash'i hesapla"), ("10", "AĞ", "DNS çözümle"),
        ("11", "WEB", "HTTP güvenlik başlıklarını kontrol et"), ("12", "WEB", "TLS sertifikasını incele"),
        ("13", "SİSTEM", "Sistem bilgilerini göster"), ("14", "KİMLİK", "Güvenli token ve UUID üret"),
        ("15", "WEB", "URL kodla/çöz"), ("16", "DOSYA", "Dosya hash'ini karşılaştır"),
        ("17", "AĞ", "Yerel ağ bilgilerini göster"), ("18", "KİMLİK", "Uzun güvenli parola üret"),
        ("19", "MEDYA", "Pop müziği aç/kapat"), ("20", "DOSYA", "Dosya güvenlik analizi"),
        ("21", "WEB", "URL şüpheli parametre analizi"), ("22", "AĞ", "Ters DNS kontrolü"),
        ("23", "AĞ", "VPN bağlantısını test et"), ("24", "AĞ", "Ağ sağlık taraması"), ("25", "SİSTEM", "Arayüz ayarları"),
    ]
    for komut, kategori, arac in araclar:
        tablo.add_row(komut, kategori, arac)
    tablo.add_row("0", "SİSTEM", "Çıkış", style="dim")
    console.print(Panel.fit(Columns([tablo, sistem_durumu_paneli()], equal=False, expand=True), border_style=primary, box=box.HEAVY))
    console.print("[dim]Komut seçin  •  Araçlar güvenli ve savunma amaçlıdır  •  0: çıkış[/dim]")


def sifre_olustur():
    try:
        minimum = int(console.input("[yellow]Minimum uzunluk: [/yellow]"))
        maksimum = int(console.input("[yellow]Maximum uzunluk: [/yellow]"))
        if minimum < 4 or maksimum < minimum:
            raise ValueError
    except ValueError:
        print("[red]Geçerli değer girin: minimum en az 4 olmalı ve maksimumdan büyük olmamalı.[/red]")
        return

    uzunluk = secrets.randbelow(maksimum - minimum + 1) + minimum
    karakterler = string.ascii_letters + string.digits + string.punctuation
    sifre = "".join(secrets.choice(karakterler) for _ in range(uzunluk))
    print(f"[green]Oluşturulan şifre:[/green] {sifre}")


def metin_hashle():
    metin = console.input("[yellow]Hash'lenecek metin: [/yellow]")
    algoritma = console.input("[yellow]Algoritma (sha256/sha512/md5): [/yellow]").lower()
    if algoritma not in {"sha256", "sha512", "md5"}:
        print("[red]Desteklenen algoritmalar: sha256, sha512, md5[/red]")
        return
    sonuc = hashlib.new(algoritma, metin.encode("utf-8")).hexdigest()
    print(f"[green]{algoritma}:[/green] {sonuc}")


def base64_araci():
    secim = console.input("[yellow]Kodla mı çöz (k/c): [/yellow]").lower()
    veri = console.input("[yellow]Metin: [/yellow]")
    try:
        if secim == "k":
            sonuc = b64encode(veri.encode("utf-8")).decode("ascii")
        elif secim == "c":
            sonuc = b64decode(veri).decode("utf-8")
        else:
            print("[red]Seçim k veya c olmalı.[/red]")
            return
        print(f"[green]Sonuç:[/green] {sonuc}")
    except (ValueError, UnicodeDecodeError):
        print("[red]Geçersiz Base64 verisi.[/red]")


def sifre_gucu():
    sifre = console.input("[yellow]Kontrol edilecek şifre: [/yellow]")
    puan = sum((len(sifre) >= 12, any(c.islower() for c in sifre),
                any(c.isupper() for c in sifre), any(c.isdigit() for c in sifre),
                any(c in string.punctuation for c in sifre)))
    seviyeler = {0: "Çok zayıf", 1: "Çok zayıf", 2: "Zayıf", 3: "Orta", 4: "Güçlü", 5: "Çok güçlü"}
    print(f"[green]Şifre gücü:[/green] {seviyeler[puan]} ({puan}/5)")


def saglayici_bilgisi(ip_adresi):
    if ipaddress.ip_address(ip_adresi).is_private:
        print("[yellow]Özel IP adreslerinde internet sağlayıcısı sorgulanamaz.[/yellow]")
        return

    bilgi = safe_json_request(f"https://ipinfo.io/{ip_adresi}/json")
    if not bilgi:
        print("[yellow]Sağlayıcı bilgisi alınamadı; internet bağlantısını kontrol edin.[/yellow]")
        return

    organizasyon = bilgi.get("org", "Bilinmiyor")
    arama_metni = f"{organizasyon} {bilgi.get('hostname', '')}".lower()
    vpn_olasiligi = any(ipucu in arama_metni for ipucu in VPN_SAGLAYICI_IPUCLARI)
    guvenlik_bilgisi = {}
    ipwho_bilgisi = safe_json_request(f"https://ipwho.is/{ip_adresi}")
    if isinstance(ipwho_bilgisi, dict):
        guvenlik_bilgisi = ipwho_bilgisi.get("security", {})

    baglanti = ipwho_bilgisi.get("connection", {})
    ikinci_saglayici = baglanti.get("org") or baglanti.get("isp")
    arama_metni = f"{arama_metni} {ikinci_saglayici or ''}".lower()
    vpn_olasiligi = vpn_olasiligi or any(ipucu in arama_metni for ipucu in VPN_SAGLAYICI_IPUCLARI)
    servis_vpn = guvenlik_bilgisi.get("vpn") is True
    servis_proxy = guvenlik_bilgisi.get("proxy") is True
    servis_hosting = guvenlik_bilgisi.get("hosting") is True
    print(f"[green]Sağlayıcı/organizasyon:[/green] {organizasyon}")
    if ikinci_saglayici and ikinci_saglayici.lower() != organizasyon.lower():
        print(f"[green]Ek sağlayıcı kaydı:[/green] {ikinci_saglayici}")
    print(f"[green]Ülke:[/green] {bilgi.get('country', 'Bilinmiyor')}")
    print(f"[green]Bölge/şehir:[/green] {bilgi.get('region', 'Bilinmiyor')} / {bilgi.get('city', 'Bilinmiyor')}")
    if servis_vpn or "proton" in arama_metni:
        print("[yellow]VPN durumu: TESPİT EDİLDİ[/yellow]")
        if "proton" in arama_metni:
            print("[yellow]Tahmini VPN sağlayıcısı: Proton VPN[/yellow]")
    elif servis_proxy:
        print("[yellow]Proxy durumu: TESPİT EDİLDİ[/yellow]")
    elif vpn_olasiligi or servis_hosting:
        print("[yellow]VPN/proxy veya veri merkezi olasılığı: YÜKSEK[/yellow]")
    else:
        print("[green]VPN/proxy sağlayıcısı işareti: Bulunmadı[/green]")
    print("[dim]Not: Sonuç sağlayıcı adı ve IP istihbaratına dayanır; kesin VPN tespiti değildir.[/dim]")


def ip_bilgisi():
    adres = console.input("[yellow]IP veya CIDR adresi (boş bırakırsanız kendi IP'niz): [/yellow]").strip()
    if not adres:
        try:
            yerel_ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            yerel_ip = "Bulunamadı"
        print(f"[green]Yerel IP:[/green] {yerel_ip}")
        try:
            with urlopen("https://api.ipify.org", timeout=3) as yanit:
                genel_ip = yanit.read().decode("ascii").strip()
            print(f"[green]Genel IP:[/green] {genel_ip}")
            saglayici_bilgisi(genel_ip)
        except (OSError, UnicodeDecodeError):
            print("[yellow]Genel IP alınamadı; internet bağlantısını kontrol edin.[/yellow]")
        return

    try:
        ag = ipaddress.ip_network(adres, strict=False) if "/" in adres else ipaddress.ip_address(adres)
    except ValueError:
        print("[red]Geçersiz IP veya CIDR adresi.[/red]")
        return

    if isinstance(ag, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
        print(f"[green]Ağ:[/green] {ag}")
        print(f"[green]Versiyon:[/green] IPv{ag.version}")
        print(f"[green]Toplam adres:[/green] {ag.num_addresses}")
        print(f"[green]İlk adres:[/green] {ag.network_address}")
        print(f"[green]Son adres:[/green] {ag.broadcast_address}")
    else:
        print(f"[green]Adres:[/green] {ag}")
        print(f"[green]Versiyon:[/green] IPv{ag.version}")
        print(f"[green]Özel ağ:[/green] {'Evet' if ag.is_private else 'Hayır'}")
        print(f"[green]Döngü adresi:[/green] {'Evet' if ag.is_loopback else 'Hayır'}")
        if not ag.is_private:
            saglayici_bilgisi(str(ag))


def url_analiz_et():
    adres = normalize_url(console.input("[yellow]Analiz edilecek URL: [/yellow]").strip())
    if not adres:
        print("[red]Geçersiz URL.[/red]")
        return
    sonuc = urlparse(adres)
    if not sonuc.netloc:
        print("[red]Geçersiz URL.[/red]")
        return
    print(f"[green]Şema:[/green] {sonuc.scheme}")
    print(f"[green]Alan adı:[/green] {sonuc.hostname}")
    print(f"[green]Port:[/green] {sonuc.port or ('443' if sonuc.scheme == 'https' else '80')}")
    print(f"[green]Yol:[/green] {sonuc.path or '/'}")
    if sonuc.username or sonuc.password:
        print("[red]Uyarı: URL içinde kullanıcı adı veya parola bilgisi var.[/red]")


def port_kontrol():
    hedef = console.input("[yellow]Hedef (ör. localhost): [/yellow]").strip()
    try:
        baslangic = int(console.input("[yellow]Başlangıç portu (1-65535): [/yellow]"))
        bitis = int(console.input("[yellow]Bitiş portu (1-65535, en fazla 20 port): [/yellow]"))
        if not 1 <= baslangic <= bitis <= 65535 or bitis - baslangic >= 20:
            raise ValueError
    except ValueError:
        print("[red]Geçersiz port aralığı. En fazla 20 ardışık port kontrol edilebilir.[/red]")
        return

    print(f"[cyan]{hedef} için portlar kontrol ediliyor...[/cyan]")
    for port in range(baslangic, bitis + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as soket:
            soket.settimeout(0.3)
            acik = soket.connect_ex((hedef, port)) == 0
        durum = "AÇIK" if acik else "kapalı"
        renk = "green" if acik else "dim"
        print(f"[{renk}]{port}: {durum}[/{renk}]")


def dosya_hashle():
    yol = Path(console.input("[yellow]Dosya yolu: [/yellow]").strip())
    algoritma = console.input("[yellow]Algoritma (sha256/sha512): [/yellow]").lower()
    if algoritma not in {"sha256", "sha512"}:
        print("[red]Sadece sha256 veya sha512 kullanılabilir.[/red]")
        return
    if not yol.is_file():
        print("[red]Dosya bulunamadı.[/red]")
        return
    hasher = hashlib.new(algoritma)
    with yol.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b""):
            hasher.update(parca)
    print(f"[green]{algoritma}:[/green] {hasher.hexdigest()}")


def dns_cozümle():
    hedef = console.input("[yellow]Alan adı veya IP: [/yellow]").strip()
    if not hedef:
        print("[red]Bir alan adı veya IP girin.[/red]")
        return
    try:
        bilgiler = socket.getaddrinfo(hedef, None)
    except socket.gaierror:
        print("[red]Adres çözümlenemedi.[/red]")
        return
    adresler = sorted({bilgi[4][0] for bilgi in bilgiler})
    print(f"[green]Çözümlenen adresler ({len(adresler)}):[/green]")
    for adres in adresler:
        print(f"  {adres}")


def http_basliklarini_kontrol_et():
    adres = normalize_url(console.input("[yellow]HTTPS URL: [/yellow]").strip())
    try:
        yanit = urlopen(Request(adres, method="HEAD", headers={"User-Agent": "EXYNOSS-Z Security Toolkit/0.3"}), timeout=URL_TIMEOUT)
        basliklar = {anahtar.lower(): deger for anahtar, deger in yanit.headers.items()}
    except (OSError, ValueError):
        print("[red]Siteye erişilemedi veya URL geçersiz.[/red]")
        return

    guvenlik_basliklari = {
        "strict-transport-security": "HTTPS zorlaması",
        "content-security-policy": "XSS ve içerik politikası",
        "x-content-type-options": "MIME türü koruması",
        "x-frame-options": "Clickjacking koruması",
        "referrer-policy": "Referer gizlilik politikası",
        "permissions-policy": "Tarayıcı izin politikası",
    }
    print(f"[green]HTTP durumu:[/green] {yanit.status}")
    for baslik, aciklama in guvenlik_basliklari.items():
        if baslik in basliklar:
            print(f"[green]VAR[/green] {baslik}: {basliklar[baslik]}")
        else:
            print(f"[yellow]YOK[/yellow] {baslik} ({aciklama})")


def tls_sertifikasi():
    hedef = console.input("[yellow]TLS alan adı: [/yellow]").strip()
    if not hedef:
        print("[red]Bir alan adı girin.[/red]")
        return
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hedef, 443), timeout=5) as soket:
            with context.wrap_socket(soket, server_hostname=hedef) as tls_soket:
                sertifika = tls_soket.getpeercert()
                konu = dict(parca[0] for parca in sertifika.get("subject", ()))
                veren = dict(parca[0] for parca in sertifika.get("issuer", ()))
                print(f"[green]Alan adı:[/green] {konu.get('commonName', 'Bilinmiyor')}")
                print(f"[green]Veren:[/green] {veren.get('organizationName', 'Bilinmiyor')}")
                print(f"[green]Başlangıç:[/green] {sertifika.get('notBefore', 'Bilinmiyor')}")
                print(f"[green]Bitiş:[/green] {sertifika.get('notAfter', 'Bilinmiyor')}")
    except (OSError, ssl.SSLError):
        print("[red]TLS bağlantısı kurulamadı veya sertifika doğrulanamadı.[/red]")


def sistem_bilgisi():
    try:
        ip_adresi = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip_adresi = "Bulunamadı"

    islemci = platform.processor() or platform.machine() or "Bilinmiyor"
    if winreg is not None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as anahtar:
                islemci = winreg.QueryValueEx(anahtar, "ProcessorNameString")[0].strip()
        except (OSError, TypeError):
            pass
    print("[green]Sistem bilgileri[/green]")
    print(f"[cyan]İşlemci:[/cyan] {islemci}")
    print(f"[cyan]IP adresi:[/cyan] {ip_adresi}")
    print(f"[cyan]İşletim sistemi:[/cyan] {platform.system()} {platform.release()}")


def token_olustur():
    try:
        uzunluk = int(console.input("[yellow]Token uzunluğu (16/32/64 byte): [/yellow]"))
        if uzunluk not in {16, 32, 64}:
            raise ValueError
    except ValueError:
        print("[red]Uzunluk 16, 32 veya 64 olmalı.[/red]")
        return
    print(f"[green]Güvenli token:[/green] {secrets.token_urlsafe(uzunluk)}")
    print(f"[dim]UUID:[/dim] {uuid.uuid4()}")


def url_kodla_coz():
    secim = console.input("[yellow]Kodla mı çöz (k/c): [/yellow]").lower()
    metin = console.input("[yellow]Metin: [/yellow]")
    if secim == "k":
        sonuc = quote(metin, safe="")
    elif secim == "c":
        sonuc = unquote(metin)
    else:
        print("[red]Seçim k veya c olmalı.[/red]")
        return
    print(f"[green]Sonuç:[/green] {sonuc}")


def url_parametre_analizi():
    adres = normalize_url(console.input("[yellow]Analiz edilecek URL: [/yellow]").strip())
    sonuc = urlparse(adres)
    parametreler = parse_qs(sonuc.query)
    supheli_anahtarlar = {"cmd", "exec", "command", "redirect", "url", "file", "path", "token", "password"}
    supheliler = sorted(set(parametreler) & supheli_anahtarlar)
    print(f"[green]Alan adı:[/green] {sonuc.hostname or 'Bilinmiyor'}")
    print(f"[green]Parametre sayısı:[/green] {len(parametreler)}")
    if supheliler:
        print(f"[yellow]Dikkat gerektiren parametreler:[/yellow] {', '.join(supheliler)}")
    else:
        print("[green]Bilinen şüpheli parametre bulunmadı.[/green]")
    if sonuc.username or sonuc.password:
        print("[red]Uyarı: URL içinde kullanıcı adı veya parola var.[/red]")


def dosya_hash_karsilastir():
    yol = Path(console.input("[yellow]Dosya yolu: [/yellow]").strip())
    beklenen = console.input("[yellow]Beklenen SHA-256 hash: [/yellow]").strip().lower()
    if not yol.is_file() or len(beklenen) != 64:
        print("[red]Dosya bulunamadı veya hash geçersiz.[/red]")
        return
    hasher = hashlib.sha256()
    with yol.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b""):
            hasher.update(parca)
    gercek = hasher.hexdigest()
    print(f"[green]Gerçek hash:[/green] {gercek}")
    mesaj = "eşleşiyor" if secrets.compare_digest(gercek, beklenen) else "eşleşmiyor"
    print(f"[green]Sonuç: Hash {mesaj}.[/green]" if mesaj == "eşleşiyor" else f"[red]Sonuç: Hash {mesaj}.[/red]")


def yerel_ag_bilgisi():
    try:
        bilgisayar, takma_adlar, adresler = socket.gethostbyname_ex(socket.gethostname())
    except socket.gaierror:
        print("[red]Yerel ağ bilgisi alınamadı.[/red]")
        return
    print(f"[green]Bilgisayar adı:[/green] {bilgisayar}")
    print(f"[green]Takma adlar:[/green] {', '.join(takma_adlar) or 'Yok'}")
    print("[green]Yerel adresler:[/green]")
    for adres in sorted(set(adresler)):
        print(f"  {adres}")


def guvenli_parola_uret():
    try:
        uzunluk = int(console.input("[yellow]Parola uzunluğu (8-128): [/yellow]"))
        if not 8 <= uzunluk <= 128:
            raise ValueError
    except ValueError:
        print("[red]Uzunluk 8 ile 128 arasında olmalı.[/red]")
        return
    karakterler = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    parola = "".join(secrets.choice(karakterler) for _ in range(uzunluk))
    print(f"[green]Güvenli parola:[/green] {parola}")


def dosya_guvenlik_analizi():
    yol = Path(console.input("[yellow]Analiz edilecek dosya: [/yellow]").strip().strip('"'))
    if not yol.is_file():
        print("[red]Dosya bulunamadı.[/red]")
        return
    bilgiler = yol.stat()
    hasher = hashlib.sha256()
    frekans = {}
    toplam = 0
    with yol.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b""):
            hasher.update(parca)
            toplam += len(parca)
            for byte in parca:
                frekans[byte] = frekans.get(byte, 0) + 1
    entropy = 0.0
    if toplam:
        entropy = -sum((adet / toplam) * math.log2(adet / toplam) for adet in frekans.values())
    print(f"[green]Dosya:[/green] {yol.name}")
    print(f"[green]Boyut:[/green] {bilgiler.st_size:,} byte")
    print(f"[green]Tür:[/green] {yol.suffix or 'uzantısız'}")
    print(f"[green]İzinler:[/green] {stat.filemode(bilgiler.st_mode)}")
    print(f"[green]SHA-256:[/green] {hasher.hexdigest()}")
    print(f"[green]Entropi:[/green] {entropy:.2f}/8.00")
    if entropy > 7.5:
        print("[yellow]Uyarı: Yüksek entropi sıkıştırılmış veya şifrelenmiş veri olabilir.[/yellow]")


def ters_dns_kontrolu():
    hedef = console.input("[yellow]IP adresi: [/yellow]").strip()
    try:
        ipaddress.ip_address(hedef)
        isim, _, adresler = socket.gethostbyaddr(hedef)
    except (ValueError, socket.herror, socket.gaierror):
        print("[red]Geçerli bir IP veya ters DNS kaydı bulunamadı.[/red]")
        return
    print(f"[green]Ters DNS adı:[/green] {isim}")
    print(f"[green]Adresler:[/green] {', '.join(adresler) or hedef}")


def vpn_testi():
    print("[cyan]VPN bağlantısı analiz ediliyor...[/cyan]")
    try:
        with urlopen("https://api.ipify.org", timeout=5) as yanit:
            genel_ip = yanit.read().decode("ascii").strip()
    except (OSError, UnicodeDecodeError):
        print("[red]Genel IP alınamadı; VPN testi yapılamadı.[/red]")
        return

    print(f"[green]Görünen genel IP:[/green] {genel_ip}")
    saglayici_bilgisi(genel_ip)
    proxy_degiskenleri = [
        ad for ad in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
        if os.environ.get(ad)
    ]
    if proxy_degiskenleri:
        print(f"[yellow]Sistem proxy değişkenleri aktif: {', '.join(proxy_degiskenleri)}[/yellow]")
    else:
        print("[green]Sistem proxy değişkeni bulunmadı.[/green]")
    print("[dim]Not: VPN sonucu sağlayıcı/IP istihbaratına dayanır; kesin tespit değildir.[/dim]")


def ag_saglik_taramasi():
    print("[cyan]Ağ sağlık taraması başlatıldı...[/cyan]")
    try:
        yerel_ip = socket.gethostbyname(socket.gethostname())
        print(f"[green]Yerel IP:[/green] {yerel_ip}")
    except socket.gaierror:
        print("[red]Yerel IP alınamadı.[/red]")

    dns_baslangic = time.perf_counter()
    try:
        dns_adresi = socket.gethostbyname("example.com")
        dns_ms = (time.perf_counter() - dns_baslangic) * 1000
        print(f"[green]DNS:[/green] Çalışıyor ({dns_adresi}, {dns_ms:.0f} ms)")
    except socket.gaierror:
        print("[red]DNS: Çalışmıyor veya yanıt vermiyor.[/red]")

    baglanti_baslangic = time.perf_counter()
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=5):
            baglanti_ms = (time.perf_counter() - baglanti_baslangic) * 1000
        print(f"[green]İnternet erişimi:[/green] Var ({baglanti_ms:.0f} ms)")
    except OSError:
        print("[red]İnternet erişimi: Başarısız[/red]")

    try:
        with urlopen("https://example.com", timeout=5) as yanit:
            print(f"[green]HTTPS:[/green] Çalışıyor (HTTP {yanit.status})")
    except OSError:
        print("[red]HTTPS: Bağlantı kurulamadı.[/red]")
    print("[dim]Bu tarama yalnızca bağlantı sağlığını ölçer; açık port taraması yapmaz.[/dim]")


def ayarlar_menu():
    while True:
        console.clear()
        console.print(Panel(
            Group(
                "[bold cyan]Arayüz Ayarları[/bold cyan]",
                "[green]1)[/green] Ön tanımlı tema seç",
                "[green]2)[/green] Ana RGB rengi ayarla",
                "[green]3)[/green] İkincil RGB rengi ayarla",
                "[green]4)[/green] Uyarı RGB rengi ayarla",
                "[green]0)[/green] Geri dön",
            ),
            title=f"[bold {rgb_style(UI_THEME['primary'])}]SETTINGS[/bold {rgb_style(UI_THEME['primary'])}]",
            border_style=rgb_style(UI_THEME['primary']),
            box=box.ROUNDED,
        ))
        secim = console.input("[yellow]Ayar seçimi: [/yellow]").strip().lower()

        if secim == "1":
            console.print("[cyan]Temalar:[/cyan] neon, cyan, magenta, amber")
            tema = console.input("[yellow]Tema adı: [/yellow]").strip().lower()
            if tema in THEME_PRESETS:
                UI_THEME.update(THEME_PRESETS[tema])
                console.print(f"[green]Tema uygulandı: {tema}[/green]")
                live_theme_preview()
            else:
                console.print("[red]Geçersiz tema adı.[/red]")
        elif secim in {"2", "3", "4"}:
            key = {"2": "primary", "3": "secondary", "4": "danger"}[secim]
            try:
                values = []
                for channel in ("R", "G", "B"):
                    value = int(console.input(f"[yellow]{channel} (0-255): [/yellow]"))
                    if not 0 <= value <= 255:
                        raise ValueError
                    values.append(value)
                r, g, b = values
                UI_THEME[key] = (r, g, b)
                console.print(f"[green]{key} RGB güncellendi: ({r}, {g}, {b})[/green]")
                live_theme_preview(f"LIVE RGB - {key.upper()}")
                console.print(f"[dim]Canlı değişim aktif: {rgb_style(UI_THEME[key])}[/dim]")
            except ValueError:
                console.print("[red]RGB değerleri 0-255 arasında olmalı.[/red]")
        elif secim == "0":
            return
        else:
            console.print("[red]Geçersiz seçim.[/red]")

        console.print("[dim]Ayarlar anında uygulanır...[/dim]")
        time.sleep(0.6)


def menu():
    while True:
        print()
        baslik_goster()
        menu_goster()
        secim = console.input("[yellow]Seçiminiz: [/yellow]")

        if secim == "1":
            sifre_olustur()
        elif secim == "2":
            print("Bu program güvenlik ve günlük metin araçlarını tek yerde toplar.")
        elif secim == "3":
            metin_hashle()
        elif secim == "4":
            base64_araci()
        elif secim == "5":
            sifre_gucu()
        elif secim == "6":
            ip_bilgisi()
        elif secim == "7":
            url_analiz_et()
        elif secim == "8":
            port_kontrol()
        elif secim == "9":
            dosya_hashle()
        elif secim == "10":
            dns_cozümle()
        elif secim == "11":
            http_basliklarini_kontrol_et()
        elif secim == "12":
            tls_sertifikasi()
        elif secim == "13":
            sistem_bilgisi()
        elif secim == "14":
            token_olustur()
        elif secim == "15":
            url_kodla_coz()
        elif secim == "16":
            dosya_hash_karsilastir()
        elif secim == "17":
            yerel_ag_bilgisi()
        elif secim == "18":
            guvenli_parola_uret()
        elif secim == "19":
            pop_muzigi_degistir()
        elif secim == "20":
            dosya_guvenlik_analizi()
        elif secim == "21":
            url_parametre_analizi()
        elif secim == "22":
            ters_dns_kontrolu()
        elif secim == "23":
            vpn_testi()
        elif secim == "24":
            ag_saglik_taramasi()
        elif secim == "25":
            ayarlar_menu()
        elif secim == "0":
            print("[green]Görüşürüz![/green]")
            break
        else:
            print("[red]Geçersiz seçim.[/red]")

        if secim in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "20", "21", "22", "23", "24", "25"}:
            ana_menuye_don()


class OperationCancelled(Exception):
    pass


def color_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


class PillButton(tk.Canvas):
    def __init__(self, master, text, command, background, foreground, hover_background, hover_foreground, padx=14, pady=8):
        self.text = text
        self.command = command
        self.background = background
        self.foreground = foreground
        self.hover_background = hover_background
        self.hover_foreground = hover_foreground
        self.current_background = background
        self.current_foreground = foreground
        self.button_state = "normal"
        self.font = ("Segoe UI", 9, "bold")
        self.font_object = tkfont.Font(master=master, font=self.font)
        self.button_height = max(32, self.font_object.metrics("linespace") + pady * 2)
        self.width = self.font_object.measure(text) + padx * 2
        super().__init__(master, width=self.width, height=self.button_height, bg=master.cget("bg"), highlightthickness=0, borderwidth=0, cursor="hand2", takefocus=True)
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Return>", self._on_click)
        self.bind("<space>", self._on_click)
        self._draw()

    def _draw(self, _event=None):
        self.delete("all")
        width = max(self.winfo_width(), self.width)
        height = max(self.winfo_height(), self.button_height)
        radius = height / 2
        self.create_oval(1, 1, radius * 2, height - 1, fill=self.current_background, outline=self.current_background)
        self.create_rectangle(radius, 1, width - radius, height - 1, fill=self.current_background, outline=self.current_background)
        self.create_oval(width - radius * 2, 1, width - 1, height - 1, fill=self.current_background, outline=self.current_background)
        self.create_text(width / 2, height / 2, text=self.text, fill=self.current_foreground, font=self.font)

    def _on_enter(self, _event=None):
        if self.button_state == "normal":
            self.current_background = self.hover_background
            self.current_foreground = self.hover_foreground
            self._draw()

    def _on_leave(self, _event=None):
        self._set_resting_colors()
        self._draw()

    def _set_resting_colors(self):
        if self.button_state == "disabled":
            self.current_background = "#303a34"
            self.current_foreground = "#87948c"
        else:
            self.current_background = self.background
            self.current_foreground = self.foreground

    def _on_click(self, _event=None):
        if self.button_state == "normal" and self.command:
            self.command()
        return "break"

    def configure(self, cnf=None, **kwargs):
        values = dict(cnf or {})
        values.update(kwargs)
        canvas_values = {}
        for key, value in values.items():
            if key == "text":
                self.text = value
            elif key == "command":
                self.command = value
            elif key == "state":
                self.button_state = value
                canvas_values["cursor"] = "hand2" if value == "normal" else "arrow"
            elif key == "bg":
                self.background = value
                canvas_values["bg"] = value
            elif key == "fg":
                self.foreground = value
            elif key == "activebackground":
                self.hover_background = value
            elif key == "activeforeground":
                self.hover_foreground = value
            elif key in {"padx", "pady"}:
                continue
            else:
                canvas_values[key] = value
        if canvas_values:
            super().configure(**canvas_values)
        self._set_resting_colors()
        self._draw()

    config = configure


class _LegacyToolkitApp:
    BG = "#101815"
    SURFACE = "#18231e"
    PANEL = "#202e27"
    TEXT = "#e7f1eb"
    MUTED = "#91a69a"

    TOOLS = [
        ("Kimlik", "Güvenli şifre oluştur", "Uzunluk aralığından rastgele parola üretir.", sifre_olustur),
        ("Sistem", "Program hakkında", "EXYNOSS-Z araç seti hakkında bilgi verir.", lambda: print("EXYNOSS-Z güvenlik ve günlük metin araçlarını tek yerde toplar.")),
        ("Kimlik", "Metin hash'le", "Metni SHA-256, SHA-512 veya MD5 ile özetler.", metin_hashle),
        ("Kimlik", "Base64 kodla / çöz", "Metni Base64 biçimine dönüştürür veya çözer.", base64_araci),
        ("Kimlik", "Şifre gücünü kontrol et", "Parola için temel uzunluk ve karakter çeşitliliği kontrolü yapar.", sifre_gucu),
        ("Ağ", "IP / CIDR bilgisi", "IP adresi veya ağ bloğu hakkında bilgi gösterir.", ip_bilgisi),
        ("Web", "URL analiz et", "URL şeması, alan adı, port ve yolunu inceler.", url_analiz_et),
        ("Ağ", "Port kontrolü", "Belirtilen en fazla 20 portu kontrol eder.", port_kontrol),
        ("Dosya", "Dosya hash'i hesapla", "Dosyanın SHA-256 veya SHA-512 özetini hesaplar.", dosya_hashle),
        ("Ağ", "DNS çözümle", "Alan adını veya IP adresini çözümler.", dns_cozümle),
        ("Web", "HTTP güvenlik başlıkları", "Bir sitenin yaygın HTTP güvenlik başlıklarını denetler.", http_basliklarini_kontrol_et),
        ("Web", "TLS sertifikası", "Alan adının TLS sertifikası bilgilerini gösterir.", tls_sertifikasi),
        ("Sistem", "Sistem bilgileri", "İşlemci, IP ve işletim sistemi bilgisini gösterir.", sistem_bilgisi),
        ("Kimlik", "Token ve UUID üret", "Güvenli token ve UUID oluşturur.", token_olustur),
        ("Web", "URL kodla / çöz", "Metni URL biçiminde kodlar veya çözer.", url_kodla_coz),
        ("Dosya", "Dosya hash'ini karşılaştır", "Dosyanın SHA-256 değerini beklenen hash ile karşılaştırır.", dosya_hash_karsilastir),
        ("Ağ", "Yerel ağ bilgileri", "Bilgisayar adını ve çözümlenen yerel IP adreslerini gösterir.", yerel_ag_bilgisi),
        ("Kimlik", "Güvenli parola üret", "Belirtilen uzunlukta güçlü parola üretir.", guvenli_parola_uret),
        ("Medya", "Müziği aç / kapat", "Yerel bir müzik dosyasını çalar veya durdurur.", pop_muzigi_degistir),
        ("Dosya", "Dosya güvenlik analizi", "Dosya hash'i, boyutu, izinleri ve entropisini hesaplar.", dosya_guvenlik_analizi),
        ("Web", "URL parametre analizi", "URL sorgu parametrelerinde dikkat gerektiren anahtarları bulur.", url_parametre_analizi),
        ("Ağ", "Ters DNS kontrolü", "IP adresi için ters DNS kaydı arar.", ters_dns_kontrolu),
        ("Ağ", "VPN bağlantı testi", "Görünen genel IP ve sağlayıcı işaretlerini inceler.", vpn_testi),
        ("Ağ", "Ağ sağlık taraması", "DNS, internet erişimi ve HTTPS bağlantısını kontrol eder.", ag_saglik_taramasi),
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("EXYNOSS-Z | Security Toolkit")
        self.root.geometry("1220x760")
        self.root.minsize(980, 620)
        self.root.configure(bg=self.BG)
        self.widgets = []
        self.tool_card_widgets = []
        self.category = "Tümü"
        self.selected_tool = None
        self.settings_loading = False
        self.categories = ["Tümü", "Kimlik", "Ağ", "Web", "Dosya", "Sistem", "Medya"]
        self._build()

        global GUI_OUTPUT
        GUI_OUTPUT = lambda text: self.root.after(0, self._append_output, text)
        console.input = self._request_input
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.apply_theme()
        self.refresh_tools()

    def register(self, widget, role):
        self.widgets.append((widget, role))
        return widget

    def make_button(self, parent, text, command, role, padx=14, pady=7):
        primary = color_hex(UI_THEME["primary"])
        secondary = color_hex(UI_THEME["secondary"])
        if role == "primary_button" or (role == "nav_button" and text == self.category):
            background, foreground = primary, self.BG
            hover_background, hover_foreground = secondary, self.BG
        else:
            background, foreground = self.PANEL, self.TEXT
            hover_background, hover_foreground = secondary, self.BG
        return PillButton(parent, text, command, background, foreground, hover_background, hover_foreground, padx, pady)

    def _build(self):
        header = self.register(tk.Frame(self.root, padx=28, pady=18), "bg")
        header.pack(fill="x")
        brand = self.register(tk.Frame(header), "bg")
        brand.pack(side="left", anchor="w")
        self.register(tk.Label(brand, text="EXYNOSS-Z", font=("Segoe UI Variable", 23, "bold")), "primary_text").pack(anchor="w")
        self.register(tk.Label(brand, text="SECURITY TOOLKIT     /     LOCAL DEFENSE CONSOLE", font=("Segoe UI", 9)), "muted_text").pack(anchor="w", pady=(2, 0))
        self.header_status = self.register(tk.Label(header, text="●  READY", font=("Segoe UI", 9, "bold"), padx=12, pady=8), "status_badge")
        self.header_status.pack(side="right", anchor="n", pady=7)

        toolbar = self.register(tk.Frame(self.root, padx=20, pady=9), "surface")
        toolbar.pack(fill="x", padx=18)
        self.register(tk.Label(toolbar, text="SAFE MODE", font=("Segoe UI", 9, "bold")), "secondary_text").pack(side="left")
        self.toolbar_summary = self.register(tk.Label(toolbar, text="24 araç  ·  6 kategori", font=("Segoe UI", 9)), "muted_text")
        self.toolbar_summary.pack(side="left", padx=(14, 0))
        self.register(self.make_button(toolbar, "Arayüz ayarları", self.open_settings, "button"), "button").pack(side="right")

        content = self.register(tk.Frame(self.root, padx=18, pady=14), "bg")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(1, weight=1, minsize=300)
        content.grid_columnconfigure(2, weight=2, minsize=390)
        content.grid_rowconfigure(0, weight=1)

        nav = self.register(tk.Frame(content, padx=10, pady=14, width=175), "surface")
        nav.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        nav.grid_propagate(False)
        self.register(tk.Label(nav, text="KATEGORİLER", font=("Segoe UI", 9, "bold")), "muted_text").pack(anchor="w", padx=9, pady=(3, 12))
        self.category_buttons = {}
        for category in self.categories:
            button = self.register(
                self.make_button(nav, category, lambda value=category: self.select_category(value), "nav_button", padx=12, pady=6),
                "nav_button",
            )
            button.pack(fill="x", pady=2)
            self.category_buttons[category] = button

        tools_panel = self.register(tk.Frame(content, padx=15, pady=15), "surface")
        tools_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        self.register(tk.Label(tools_panel, text="Araç kitaplığı", font=("Segoe UI Variable", 14, "bold")), "text").pack(anchor="w")
        self.tool_count_label = self.register(tk.Label(tools_panel, text="24 araç", font=("Segoe UI", 9)), "muted_text")
        self.tool_count_label.pack(anchor="w", pady=(2, 10))
        self.search_entry = self.register(tk.Entry(tools_panel, relief="flat", font=("Segoe UI", 10)), "input")
        self.search_entry.pack(fill="x", pady=(0, 10), ipady=9)
        self.search_entry.insert(0, "Araç ara...")
        self.search_entry.bind("<FocusIn>", self._clear_search_hint)
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh_tools())
        list_container = self.register(tk.Frame(tools_panel), "surface")
        list_container.pack(fill="both", expand=True)
        self.tool_canvas = self.register(tk.Canvas(list_container, highlightthickness=0, borderwidth=0), "canvas")
        self.tool_canvas.pack(side="left", fill="both", expand=True)
        self.tool_scrollbar = self.register(tk.Scrollbar(list_container, orient="vertical", command=self.tool_canvas.yview), "scrollbar")
        self.tool_scrollbar.pack(side="right", fill="y")
        self.tool_canvas.configure(yscrollcommand=self.tool_scrollbar.set)
        self.tool_rows = self.register(tk.Frame(self.tool_canvas), "surface")
        self.tool_rows_window = self.tool_canvas.create_window((0, 0), window=self.tool_rows, anchor="nw")
        self.tool_rows.bind("<Configure>", lambda _event: self.tool_canvas.configure(scrollregion=self.tool_canvas.bbox("all")))
        self.tool_canvas.bind("<Configure>", lambda event: self.tool_canvas.itemconfigure(self.tool_rows_window, width=event.width))
        self.tool_canvas.bind_all("<MouseWheel>", self._scroll_tools)
        self.selected_label = self.register(tk.Label(tools_panel, text="Bir araç seçerek ayrıntılarını görün.", justify="left", wraplength=290, font=("Segoe UI", 9)), "muted_text")
        self.selected_label.pack(fill="x", anchor="w", pady=(10, 5))
        self.run_button = self.register(self.make_button(tools_panel, "Aracı çalıştır", self.run_selected, "primary_button", padx=18, pady=9), "primary_button")
        self.run_button.pack(fill="x", pady=(5, 0))

        output_panel = self.register(tk.Frame(content, padx=16, pady=15), "surface")
        output_panel.grid(row=0, column=2, sticky="nsew")
        output_panel.grid_rowconfigure(1, weight=1)
        output_panel.grid_columnconfigure(0, weight=1)
        output_header = self.register(tk.Frame(output_panel), "surface")
        output_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.register(tk.Label(output_header, text="ÇIKTI", font=("Segoe UI", 11, "bold")), "text").pack(side="left")
        self.register(self.make_button(output_header, "Temizle", self.clear_output, "button", padx=12, pady=5), "button").pack(side="right")
        self.output_text = self.register(tk.Text(output_panel, wrap="word", relief="flat", borderwidth=0, padx=12, pady=12, font=("Consolas", 10), state="disabled"), "output")
        self.output_text.grid(row=1, column=0, sticky="nsew")
        self.status_var = tk.StringVar(value="Hazır")
        self.status_label = self.register(tk.Label(self.root, textvariable=self.status_var, anchor="w", padx=22, pady=9, font=("Segoe UI", 9)), "surface")
        self.status_label.pack(fill="x", side="bottom")
        self.root.bind("<Control-k>", lambda _event: self._focus_search())
        self.root.bind("<Return>", lambda _event: self.run_selected())
        self.root.bind("<Escape>", lambda _event: self._clear_search())

    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")
        return "break"

    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self.refresh_tools()
        return "break"

    def _scroll_tools(self, event):
        left = self.tool_canvas.winfo_rootx()
        top = self.tool_canvas.winfo_rooty()
        right = left + self.tool_canvas.winfo_width()
        bottom = top + self.tool_canvas.winfo_height()
        if left <= event.x_root <= right and top <= event.y_root <= bottom:
            self.tool_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _clear_search_hint(self, _event):
        if self.search_entry.get() == "Araç ara...":
            self.search_entry.delete(0, "end")

    def select_category(self, category):
        self.category = category
        self.apply_theme()
        self.refresh_tools()

    def refresh_tools(self):
        query = self.search_entry.get().strip().casefold()
        if query == "araç ara...":
            query = ""
        self.visible_tools = [
            tool for tool in self.TOOLS
            if (self.category == "Tümü" or tool[0] == self.category)
            and (not query or query in tool[1].casefold() or query in tool[2].casefold() or query in tool[0].casefold())
        ]
        for row in self.tool_rows.winfo_children():
            row.destroy()
        self.tool_card_widgets = []
        for index, tool in enumerate(self.visible_tools):
            card = tk.Frame(self.tool_rows, padx=10, pady=8, cursor="hand2")
            card.pack(fill="x", pady=3)
            title = tk.Label(card, text=tool[1], anchor="w", font=("Segoe UI", 10, "bold"), cursor="hand2")
            title.pack(fill="x")
            meta = tk.Label(card, text=f"{tool[0].upper()}   ·   {tool[2]}", anchor="w", justify="left", wraplength=270, font=("Segoe UI", 8), cursor="hand2")
            meta.pack(fill="x", pady=(3, 0))
            self.tool_card_widgets.append((card, title, meta, index))
            for widget in (card, title, meta):
                widget.bind("<Button-1>", lambda _event, item=index: self._select_tool(item))
                widget.bind("<Double-Button-1>", lambda _event, item=index: self._run_tool_at(item))
        self.selected_tool = None
        self.selected_label.configure(text=f"{len(self.visible_tools)} araç gösteriliyor. Birini seçerek ayrıntılarını görün.")
        self.run_button.configure(state="disabled")
        self.tool_count_label.configure(text=f"{len(self.visible_tools)} / {len(self.TOOLS)} araç")
        self.toolbar_summary.configure(text=f"{len(self.TOOLS)} araç  ·  {len(self.categories) - 1} kategori  ·  {self.category}")
        self.tool_canvas.yview_moveto(0)
        self.apply_theme()

    def _select_tool(self, index):
        if not 0 <= index < len(self.visible_tools):
            return
        self.selected_tool = self.visible_tools[index]
        self.selected_label.configure(text=self.selected_tool[2])
        self.run_button.configure(state="normal")
        self.apply_theme()

    def _run_tool_at(self, index):
        self._select_tool(index)
        self.run_selected()

    def _request_input(self, prompt):
        event = threading.Event()
        answer = {"value": None}
        prompt_text = re.sub(r"\[/?[^\]]+\]", "", str(prompt)).strip()

        def ask():
            try:
                lowered = prompt_text.casefold()
                if "dosya yolu" in lowered or "analiz edilecek dosya" in lowered or "müzik dosyasının yolu" in lowered:
                    answer["value"] = filedialog.askopenfilename(parent=self.root, title=prompt_text) or None
                else:
                    mask = "*" if "kontrol edilecek şifre" in lowered else None
                    answer["value"] = simpledialog.askstring("EXYNOSS-Z", prompt_text, parent=self.root, show=mask)
            finally:
                event.set()

        self.root.after(0, ask)
        event.wait()
        if answer["value"] is None:
            raise OperationCancelled
        return answer["value"]

    def run_selected(self):
        if self.selected_tool is None:
            return
        tool = self.selected_tool
        self.clear_output()
        self.status_var.set(f"Çalışıyor: {tool[1]}")
        self.header_status.configure(text="●  ÇALIŞIYOR")
        self.run_button.configure(state="disabled")

        def execute():
            try:
                print(f"{tool[1]}\n{'-' * len(tool[1])}")
                tool[3]()
            except OperationCancelled:
                print("İşlem iptal edildi.")
            except Exception as error:
                print(f"İşlem sırasında hata: {error}")
            finally:
                self.root.after(0, lambda: self._finished(tool[1]))

        threading.Thread(target=execute, daemon=True).start()

    def _finished(self, name):
        self.status_var.set(f"Tamamlandı: {name}")
        self.header_status.configure(text="●  HAZIR")
        self.run_button.configure(state="normal" if self.selected_tool else "disabled")

    def _append_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def open_settings(self):
        window = tk.Toplevel(self.root)
        window.title("Arayüz Ayarları")
        window.geometry("460x550")
        window.resizable(False, False)
        window.transient(self.root)
        window.configure(bg=self.BG)
        self.register(tk.Label(window, text="Canlı RGB teması", font=("Segoe UI", 16, "bold"), padx=22, pady=18), "primary_text").pack(anchor="w")
        self.register(tk.Label(window, text="Renk kanallarını sürükleyerek arayüz rengini anında değiştir.", font=("Segoe UI", 9), padx=22), "muted_text").pack(anchor="w")

        preset_frame = self.register(tk.Frame(window, padx=18, pady=16), "bg")
        preset_frame.pack(fill="x")
        for preset in THEME_PRESETS:
            self.register(self.make_button(preset_frame, preset.title(), lambda name=preset: self.apply_preset(name, target_var, sliders, preview), "button", padx=10, pady=6), "button").pack(side="left", padx=(0, 6))

        self.register(tk.Label(window, text="Düzenlenecek renk", font=("Segoe UI", 9, "bold"), padx=22), "text").pack(anchor="w", pady=(4, 4))
        target_var = tk.StringVar(value="primary")
        target = tk.OptionMenu(window, target_var, "primary", "secondary", "danger", command=lambda _value: self.load_color_controls(target_var, sliders, preview))
        self.register(target, "button")
        target.pack(anchor="w", padx=22)

        sliders = {}
        for channel, color_name in zip("RGB", ("red", "green", "blue")):
            row = self.register(tk.Frame(window, padx=20, pady=4), "bg")
            row.pack(fill="x")
            self.register(tk.Label(row, text=channel, width=3, font=("Segoe UI", 10, "bold")), "text").pack(side="left")
            scale = self.register(tk.Scale(row, from_=0, to=255, orient="horizontal", showvalue=True, length=340, command=lambda _value: self.update_live_color(target_var, sliders, preview)), "scale")
            scale.pack(side="left", fill="x", expand=True)
            sliders[channel] = scale

        preview = self.register(tk.Label(window, text="RGB(0, 255, 170)", font=("Segoe UI", 12, "bold"), padx=14, pady=16), "preview")
        preview.pack(fill="x", padx=22, pady=18)
        self.load_color_controls(target_var, sliders, preview)
        self.register(self.make_button(window, "Kapat", command=window.destroy, role="button"), "button").pack(anchor="e", padx=22)
        self.apply_theme()

    def apply_preset(self, name, target_var, sliders, preview):
        UI_THEME.update(THEME_PRESETS[name])
        self.load_color_controls(target_var, sliders, preview)
        self.apply_theme()

    def load_color_controls(self, target_var, sliders, preview):
        color = UI_THEME[target_var.get()]
        for channel, value in zip("RGB", color):
            sliders[channel].set(value)
        preview.configure(text=f"{target_var.get().upper()}  ·  RGB({color[0]}, {color[1]}, {color[2]})", bg=color_hex(color))
        self.apply_theme()

    def update_live_color(self, target_var, sliders, preview):
        color = tuple(int(sliders[channel].get()) for channel in "RGB")
        UI_THEME[target_var.get()] = color
        preview.configure(text=f"{target_var.get().upper()}  ·  RGB({color[0]}, {color[1]}, {color[2]})", bg=color_hex(color))
        self.apply_theme()

    def apply_theme(self):
        primary = color_hex(UI_THEME["primary"])
        secondary = color_hex(UI_THEME["secondary"])
        palette = {
            "bg": self.BG,
            "surface": self.SURFACE,
            "panel": self.PANEL,
            "text": self.TEXT,
            "muted_text": self.MUTED,
            "primary_text": primary,
            "secondary_text": secondary,
            "input": {"bg": "#0c120f", "fg": self.TEXT, "insertbackground": self.TEXT, "selectbackground": primary},
            "output": {"bg": "#0c120f", "fg": self.TEXT, "insertbackground": self.TEXT, "selectbackground": primary},
            "button": {"bg": self.PANEL, "fg": self.TEXT, "activebackground": secondary, "activeforeground": self.BG},
            "nav_button": {"bg": primary if self.category == "Tümü" else self.SURFACE, "fg": self.BG if self.category == "Tümü" else self.TEXT, "activebackground": primary, "activeforeground": self.BG},
            "primary_button": {"bg": primary, "fg": self.BG, "activebackground": secondary, "activeforeground": self.BG},
            "scale": {"bg": self.BG, "fg": self.TEXT, "troughcolor": self.PANEL, "activebackground": primary, "highlightthickness": 0},
            "preview": {"bg": primary, "fg": self.BG},
            "canvas": {"bg": self.SURFACE},
            "scrollbar": {"bg": self.PANEL, "activebackground": secondary, "troughcolor": self.SURFACE, "highlightthickness": 0, "borderwidth": 0},
            "status_badge": {"bg": self.PANEL, "fg": primary},
        }
        for category, button in getattr(self, "category_buttons", {}).items():
            role = "nav_button"
            if category == self.category:
                style = {"bg": primary, "fg": self.BG, "activebackground": secondary, "activeforeground": self.BG}
            else:
                style = palette[role]
            try:
                button.configure(**style)
            except tk.TclError:
                pass
        for widget, role in self.widgets:
            if widget in getattr(self, "category_buttons", {}).values():
                continue
            try:
                value = palette[role]
                widget.configure(**value if isinstance(value, dict) else {"bg": value})
            except (tk.TclError, KeyError):
                pass
        for card, title, meta, index in self.tool_card_widgets:
            selected = self.selected_tool is not None and self.visible_tools[index] == self.selected_tool
            background = primary if selected else self.PANEL
            foreground = self.BG if selected else self.TEXT
            muted = self.BG if selected else self.MUTED
            card.configure(bg=background)
            title.configure(bg=background, fg=foreground)
            meta.configure(bg=background, fg=muted)

    def close(self):
        global GUI_OUTPUT
        GUI_OUTPUT = None
        if muzik_durumu:
            if pygame is not None and pygame.mixer.get_init():
                pygame.mixer.music.stop()
            if winsound is not None:
                winsound.PlaySound(None, winsound.SND_PURGE)
        self.root.destroy()


class ToolkitApp:
    BG = "#0b100e"
    SURFACE = "#121a16"
    PANEL = "#18231d"
    CARD = "#1d2a23"
    TEXT = "#e7f0ea"
    MUTED = "#91a197"
    SOFT = "#c3cec7"

    TOOLS = _LegacyToolkitApp.TOOLS

    def __init__(self, root):
        self.root = root
        self.root.title("EXYNOSS-Z | Security Toolkit")
        self.root.geometry("1380x850")
        self.root.minsize(1120, 700)
        self.root.configure(fg_color=self.BG)
        self.categories = ["Tümü", "Kimlik", "Ağ", "Web", "Dosya", "Sistem", "Medya"]
        self.category = "Tümü"
        self.selected_tool = None
        self.widgets = []
        self.cards = []
        self.category_buttons = {}
        self.settings_theme_controls = None
        self._build()

        global GUI_OUTPUT
        GUI_OUTPUT = lambda text: self.root.after(0, self._append_output, text)
        console.input = self._request_input
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Control-k>", lambda _event: self.search_entry.focus_set())
        self.root.bind("<Return>", lambda _event: self.run_selected())
        self.root.bind("<Escape>", lambda _event: self.clear_search())
        self.refresh_tools()
        self.apply_theme()

    def register(self, widget, role):
        self.widgets.append((widget, role))
        return widget

    def _build(self):
        header = self.register(ctk.CTkFrame(self.root, fg_color="transparent"), "transparent")
        header.pack(fill="x", padx=30, pady=(25, 18))
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", fill="x", expand=True)
        self.register(ctk.CTkLabel(brand, text="EXYNOSS-Z", font=ctk.CTkFont(family="Segoe UI", size=27, weight="bold"), anchor="w"), "primary_title").pack(anchor="w")
        self.register(ctk.CTkLabel(brand, text="GÜVENLİK ARAÇLARI     /     YEREL SAVUNMA PANELİ", font=ctk.CTkFont(size=10, weight="bold"), anchor="w"), "muted").pack(anchor="w", pady=(2, 0))

        self.header_status = self.register(ctk.CTkLabel(header, text="●  HAZIR", width=100, height=34, corner_radius=18, font=ctk.CTkFont(size=10, weight="bold")), "status")
        self.header_status.pack(side="right", anchor="n", pady=5)

        toolbar = self.register(ctk.CTkFrame(self.root, corner_radius=16, height=52), "surface")
        toolbar.pack(fill="x", padx=30)
        toolbar.pack_propagate(False)
        self.register(ctk.CTkLabel(toolbar, text="GÜVENLİ MOD", font=ctk.CTkFont(size=10, weight="bold")), "secondary_text").pack(side="left", padx=(18, 10))
        self.toolbar_summary = self.register(ctk.CTkLabel(toolbar, text="24 araç  ·  6 kategori", font=ctk.CTkFont(size=10)), "muted")
        self.toolbar_summary.pack(side="left")
        self.register(ctk.CTkButton(toolbar, text="Arayüz ayarları", command=self.open_settings, height=34, corner_radius=20, font=ctk.CTkFont(size=10, weight="bold")), "button").pack(side="right", padx=9)

        body = self.register(ctk.CTkFrame(self.root, fg_color="transparent"), "transparent")
        body.pack(fill="both", expand=True, padx=30, pady=16)
        body.grid_columnconfigure(0, weight=0, minsize=180)
        body.grid_columnconfigure(1, weight=5, minsize=340)
        body.grid_columnconfigure(2, weight=6, minsize=430)
        body.grid_rowconfigure(0, weight=1)

        sidebar = self.register(ctk.CTkFrame(body, corner_radius=16, width=180), "surface")
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        sidebar.grid_propagate(False)
        self.register(ctk.CTkLabel(sidebar, text="KATEGORİLER", font=ctk.CTkFont(size=9, weight="bold")), "muted").pack(anchor="w", padx=16, pady=(19, 12))
        for category in self.categories:
            button = self.register(
                ctk.CTkButton(sidebar, text=category, anchor="w", height=38, corner_radius=20, command=lambda value=category: self.select_category(value), font=ctk.CTkFont(size=11, weight="bold")),
                "category_button",
            )
            button.pack(fill="x", padx=9, pady=3)
            self.category_buttons[category] = button
        self.register(ctk.CTkLabel(sidebar, text="YEREL  ·  GÜVENLİ MOD", font=ctk.CTkFont(size=9, weight="bold")), "muted").pack(side="bottom", anchor="w", padx=16, pady=17)

        library = self.register(ctk.CTkFrame(body, corner_radius=16), "surface")
        library.grid(row=0, column=1, sticky="nsew", padx=(0, 14))
        self.register(ctk.CTkLabel(library, text="Araç kitaplığı", font=ctk.CTkFont(size=17, weight="bold"), anchor="w"), "text").pack(fill="x", padx=17, pady=(18, 1))
        self.tool_count_label = self.register(ctk.CTkLabel(library, text="24 araç", font=ctk.CTkFont(size=10), anchor="w"), "muted")
        self.tool_count_label.pack(fill="x", padx=17, pady=(0, 12))
        self.search_entry = self.register(ctk.CTkEntry(library, placeholder_text="Araç veya kategori ara", height=40, corner_radius=12, border_width=1, font=ctk.CTkFont(size=11)), "input")
        self.search_entry.pack(fill="x", padx=13, pady=(0, 12))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh_tools())
        self.tool_list = self.register(ctk.CTkScrollableFrame(library, fg_color="transparent", corner_radius=0), "transparent")
        self.tool_list.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.selected_label = self.register(ctk.CTkLabel(library, text="Bir araç seçerek ayrıntılarını görüntüle.", justify="left", anchor="w", wraplength=310, font=ctk.CTkFont(size=10)), "muted")
        self.selected_label.pack(fill="x", padx=16, pady=(8, 9))
        self.run_button = self.register(ctk.CTkButton(library, text="Aracı çalıştır", command=self.run_selected, height=43, corner_radius=24, font=ctk.CTkFont(size=11, weight="bold"), state="disabled"), "primary_button")
        self.run_button.pack(fill="x", padx=13, pady=(0, 14))

        output_panel = self.register(ctk.CTkFrame(body, corner_radius=16), "surface")
        output_panel.grid(row=0, column=2, sticky="nsew")
        output_panel.grid_rowconfigure(1, weight=1)
        output_panel.grid_columnconfigure(0, weight=1)
        output_header = self.register(ctk.CTkFrame(output_panel, fg_color="transparent"), "transparent")
        output_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 11))
        self.register(ctk.CTkLabel(output_header, text="İşlem çıktısı", font=ctk.CTkFont(size=17, weight="bold")), "text").pack(side="left")
        self.register(ctk.CTkButton(output_header, text="Temizle", command=self.clear_output, height=30, corner_radius=18, font=ctk.CTkFont(size=10, weight="bold")), "button").pack(side="right")
        self.output_text = self.register(ctk.CTkTextbox(output_panel, wrap="word", corner_radius=12, border_width=0, font=ctk.CTkFont(family="Consolas", size=11)), "output")
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=13, pady=(0, 13))
        self.output_text.configure(state="disabled")

        footer = self.register(ctk.CTkFrame(self.root, corner_radius=0, height=35), "footer")
        footer.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Hazır")
        self.status_label = self.register(ctk.CTkLabel(footer, textvariable=self.status_var, anchor="w", font=ctk.CTkFont(size=10)), "muted")
        self.status_label.pack(fill="x", padx=30, pady=8)

    def refresh_tools(self):
        query = self.search_entry.get().strip().casefold()
        matches = [
            tool for tool in self.TOOLS
            if (self.category == "Tümü" or tool[0] == self.category)
            and (not query or query in tool[0].casefold() or query in tool[1].casefold() or query in tool[2].casefold())
        ]
        for child in self.tool_list.winfo_children():
            child.destroy()
        self.cards = []
        self.visible_tools = matches
        for index, tool in enumerate(matches):
            card = ctk.CTkFrame(self.tool_list, corner_radius=11, border_width=1)
            card.pack(fill="x", padx=3, pady=4)
            category = ctk.CTkLabel(card, text=tool[0].upper(), font=ctk.CTkFont(size=8, weight="bold"), anchor="w")
            category.pack(fill="x", padx=11, pady=(8, 0))
            title = ctk.CTkLabel(card, text=tool[1], font=ctk.CTkFont(size=11, weight="bold"), anchor="w", wraplength=290)
            title.pack(fill="x", padx=11, pady=(2, 0))
            description = ctk.CTkLabel(card, text=tool[2], font=ctk.CTkFont(size=9), anchor="w", justify="left", wraplength=290)
            description.pack(fill="x", padx=11, pady=(2, 9))
            self.cards.append((card, category, title, description, index))
            for widget in (card, category, title, description):
                widget.bind("<Button-1>", lambda _event, item=index: self.select_tool(item))
                widget.bind("<Double-Button-1>", lambda _event, item=index: self.run_tool(item))
        self.selected_tool = None
        self.selected_label.configure(text=f"{len(matches)} araç gösteriliyor. Bir aracı seçerek devam et.")
        self.tool_count_label.configure(text=f"{len(matches)} / {len(self.TOOLS)} araç")
        self.toolbar_summary.configure(text=f"{len(self.TOOLS)} araç  ·  {len(self.categories) - 1} kategori  ·  {self.category}")
        self.run_button.configure(state="disabled")
        self.apply_theme()

    def select_category(self, category):
        self.category = category
        self.refresh_tools()

    def select_tool(self, index):
        if not 0 <= index < len(self.visible_tools):
            return
        self.selected_tool = self.visible_tools[index]
        self.selected_label.configure(text=self.selected_tool[2])
        self.run_button.configure(state="normal")
        self.apply_theme()

    def run_tool(self, index):
        self.select_tool(index)
        self.run_selected()

    def _request_input(self, prompt):
        event = threading.Event()
        answer = {"value": None}
        prompt_text = re.sub(r"\[/?[^\]]+\]", "", str(prompt)).strip()

        def ask():
            try:
                lowered = prompt_text.casefold()
                if "dosya yolu" in lowered or "analiz edilecek dosya" in lowered or "müzik dosyasının yolu" in lowered:
                    answer["value"] = filedialog.askopenfilename(parent=self.root, title=prompt_text) or None
                else:
                    mask = "*" if "kontrol edilecek şifre" in lowered else None
                    answer["value"] = simpledialog.askstring("EXYNOSS-Z", prompt_text, parent=self.root, show=mask)
            finally:
                event.set()

        self.root.after(0, ask)
        event.wait()
        if answer["value"] is None:
            raise OperationCancelled
        return answer["value"]

    def run_selected(self):
        if self.selected_tool is None:
            return
        tool = self.selected_tool
        self.clear_output()
        self.status_var.set(f"Çalışıyor: {tool[1]}")
        self.header_status.configure(text="●  RUNNING")
        self.run_button.configure(state="disabled", text="Çalışıyor…")

        def execute():
            try:
                print(f"{tool[1]}\n{'-' * len(tool[1])}")
                tool[3]()
            except OperationCancelled:
                print("İşlem iptal edildi.")
            except Exception as error:
                print(f"İşlem sırasında hata: {error}")
            finally:
                self.root.after(0, lambda: self._finished(tool[1]))

        threading.Thread(target=execute, daemon=True).start()

    def _finished(self, name):
        self.status_var.set(f"Tamamlandı: {name}")
        self.header_status.configure(text="●  READY")
        self.run_button.configure(state="normal" if self.selected_tool else "disabled", text="Aracı çalıştır")

    def _append_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def open_settings(self):
        window = ctk.CTkToplevel(self.root)
        window.title("Arayüz Ayarları")
        window.geometry("470x590")
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()
        self.style_settings(window)
        ctk.CTkLabel(window, text="Görünüm", font=ctk.CTkFont(size=21, weight="bold")).pack(anchor="w", padx=24, pady=(25, 2))
        ctk.CTkLabel(window, text="Renkleri değiştir; arayüz anında güncellensin.", text_color=self.MUTED, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=24)

        presets = ctk.CTkFrame(window, fg_color="transparent")
        presets.pack(fill="x", padx=20, pady=(20, 17))
        preset_buttons = []
        for name in THEME_PRESETS:
            button = ctk.CTkButton(
                presets,
                text=name.title(),
                width=88,
                height=35,
                corner_radius=20,
                command=lambda value=name: self.apply_preset(value, color_var, sliders, value_labels, preview, preview_label),
            )
            button.pack(side="left", padx=3)
            preset_buttons.append(button)

        ctk.CTkLabel(window, text="Düzenlenecek renk", font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=24, pady=(3, 7))
        color_var = tk.StringVar(value="Ana")
        color_picker = ctk.CTkSegmentedButton(
            window,
            values=["Ana", "İkincil", "Uyarı"],
            variable=color_var,
            command=lambda _value: self.load_color_controls(color_var, sliders, value_labels, preview, preview_label),
        )
        color_picker.pack(fill="x", padx=24, pady=(0, 18))

        sliders = {}
        value_labels = {}
        for channel in "RGB":
            row = ctk.CTkFrame(window, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=6)
            ctk.CTkLabel(row, text=channel, width=24, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
            value_label = ctk.CTkLabel(row, text="0", width=38, anchor="e", font=ctk.CTkFont(family="Consolas", size=10))
            value_label.pack(side="right")
            slider = ctk.CTkSlider(
                row,
                from_=0,
                to=255,
                number_of_steps=255,
                command=lambda value, key=channel: self.update_live_color(color_var, sliders, value_labels, preview, preview_label, key, value),
            )
            slider.pack(side="left", fill="x", expand=True, padx=12)
            sliders[channel] = slider
            value_labels[channel] = value_label

        preview = ctk.CTkFrame(window, corner_radius=12, height=90)
        preview.pack(fill="x", padx=24, pady=(22, 12))
        preview.pack_propagate(False)
        preview_label = ctk.CTkLabel(preview, text="CANLI ÖNİZLEME", font=ctk.CTkFont(size=12, weight="bold"))
        preview_label.pack(expand=True)
        self.settings_theme_controls = {
            "window": window,
            "presets": preset_buttons,
            "picker": color_picker,
            "sliders": sliders,
        }
        window.bind(
            "<Destroy>",
            lambda event: setattr(self, "settings_theme_controls", None) if event.widget is window else None,
            add="+",
        )
        self.load_color_controls(color_var, sliders, value_labels, preview, preview_label)
        ctk.CTkButton(window, text="Tamam", width=110, height=38, corner_radius=22, command=window.destroy).pack(anchor="e", padx=24, pady=(5, 22))

    def style_settings(self, window):
        window.configure(fg_color=self.BG)

    def apply_preset(self, name, color_var, sliders, value_labels, preview, preview_label):
        UI_THEME.update(THEME_PRESETS[name])
        self.load_color_controls(color_var, sliders, value_labels, preview, preview_label)
        self.apply_theme()

    def load_color_controls(self, color_var, sliders, value_labels, preview, preview_label):
        key = self._theme_key(color_var.get())
        color = UI_THEME[key]
        for channel, value in zip("RGB", color):
            sliders[channel].set(value)
            value_labels[channel].configure(text=str(value))
        preview.configure(fg_color=color_hex(color))
        preview_label.configure(text=f"{color_var.get().upper()}   ·   RGB({color[0]}, {color[1]}, {color[2]})", text_color=self.BG)
        self.apply_theme()

    def update_live_color(self, color_var, sliders, value_labels, preview, preview_label, channel, value):
        key = self._theme_key(color_var.get())
        current = list(UI_THEME[key])
        index = "RGB".index(channel)
        current[index] = round(value)
        color = tuple(current)
        UI_THEME[key] = color
        value_labels[channel].configure(text=str(color[index]))
        preview.configure(fg_color=color_hex(color))
        preview_label.configure(text=f"{color_var.get().upper()}   ·   RGB({color[0]}, {color[1]}, {color[2]})")
        self.apply_theme()

    @staticmethod
    def _theme_key(label):
        return {"Ana": "primary", "İkincil": "secondary", "Uyarı": "danger"}[label]

    def apply_theme(self):
        primary = color_hex(UI_THEME["primary"])
        secondary = color_hex(UI_THEME["secondary"])
        palette = {
            "transparent": {"fg_color": "transparent"},
            "surface": {"fg_color": self.SURFACE},
            "footer": {"fg_color": self.BG},
            "text": {"text_color": self.TEXT},
            "muted": {"text_color": self.MUTED},
            "primary_title": {"text_color": primary},
            "secondary_text": {"text_color": secondary},
            "status": {"fg_color": self.PANEL, "text_color": primary},
            "input": {"fg_color": self.PANEL, "border_color": self.CARD, "text_color": self.TEXT, "placeholder_text_color": self.MUTED},
            "output": {"fg_color": "#0e1511", "text_color": self.TEXT},
            "button": {"fg_color": self.CARD, "hover_color": secondary, "text_color": self.TEXT},
            "primary_button": {"fg_color": primary, "hover_color": secondary, "text_color": self.BG},
        }
        self.root.configure(fg_color=self.BG)
        for widget, role in self.widgets:
            style = palette.get(role)
            if style:
                try:
                    widget.configure(**style)
                except (tk.TclError, RuntimeError):
                    pass
        for category, button in self.category_buttons.items():
            active = category == self.category
            button.configure(
                fg_color=primary if active else self.SURFACE,
                hover_color=secondary,
                text_color=self.BG if active else self.SOFT,
            )
        self.run_button.configure(fg_color=primary, hover_color=secondary, text_color=self.BG)
        for card, category_label, title, description, index in self.cards:
            selected = self.selected_tool is not None and self.visible_tools[index] == self.selected_tool
            card.configure(
                fg_color=self.CARD if not selected else self.PANEL,
                border_color=primary if selected else self.CARD,
            )
            category_label.configure(text_color=primary)
            title.configure(text_color=self.TEXT)
            description.configure(text_color=self.MUTED)
        if self.settings_theme_controls:
            controls = self.settings_theme_controls
            try:
                for button in controls["presets"]:
                    button.configure(fg_color=self.CARD, hover_color=secondary, text_color=self.TEXT)
                controls["picker"].configure(
                    selected_color=primary,
                    selected_hover_color=secondary,
                    unselected_color=self.PANEL,
                    unselected_hover_color=self.CARD,
                    text_color=self.TEXT,
                )
                for slider in controls["sliders"].values():
                    slider.configure(progress_color=primary, button_color=secondary, button_hover_color=primary)
            except (tk.TclError, RuntimeError):
                pass

    def close(self):
        global GUI_OUTPUT
        GUI_OUTPUT = None
        if muzik_durumu:
            if pygame is not None and pygame.mixer.get_init():
                pygame.mixer.music.stop()
            if winsound is not None:
                winsound.PlaySound(None, winsound.SND_PURGE)
        self.root.destroy()


def launch_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    ToolkitApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()