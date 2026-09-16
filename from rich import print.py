from base64 import b64decode, b64encode
import hashlib
import importlib.util
import ipaddress
import json
import math
import os
import platform
from pathlib import Path
import secrets
import socket
import ssl
import stat
import string
import subprocess
import sys
import time
import uuid
from datetime import datetime
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen


DEPENDENCIES = {
    "rich": {"required": True, "label": "Rich arayüzü"},
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

try:
    import winreg
except ImportError:
    winreg = None

try:
    import winsound
except ImportError:
    winsound = None

try:
    import pygame
except ImportError:
    pygame = None

try:
    import psutil
except ImportError:
    psutil = None

from rich import box, print
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
URL_TIMEOUT = 5

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


if __name__ == "__main__":
    if winsound is not None or pygame is not None:
        pop_muzigi_degistir()
    try:
        menu()
    finally:
        if muzik_durumu:
            if pygame is not None and pygame.mixer.get_init():
                pygame.mixer.music.stop()
            if winsound is not None:
                winsound.PlaySound(None, winsound.SND_PURGE)