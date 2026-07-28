#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FilmArşivi — Klasik Sinema (Public Domain) üreteci
Internet Archive'ın telifsiz film koleksiyonundan çeker ve şunları üretir:
  klasik.html               Ücretsiz/telifsiz filmler galerisi (sitene link)
  klasik/<id>.html          Her film için oynatıcı sayfası (Archive embed)
  klasik-veri.json          Ana siteye enjekte için veri
Filmler Archive.org sunucusunda kalır (embed), sen dosya barındırmazsın — bedava & yasal.
GitHub Actions bunu haftalık çalıştırır.
"""
import json, os, re, sys, time, html
from urllib.request import urlopen, Request
from urllib.parse import quote

BASE_URL = "https://deathbeam31.github.io/Dizify"   # domain alınca güncelle
IA = "https://archive.org"

# Kaliteli, gerçekten public domain film koleksiyonları (küratörlü)
COLLECTIONS = ["Feature_Films", "film_noir", "classic_cartoons", "SciFi_Horror", "silent_films"]
ROWS = 60   # koleksiyon başına çekilecek aday

def fetch_json(url):
    req = Request(url, headers={"User-Agent": "FilmArsivi-Klasik/1.0"})
    for a in range(3):
        try:
            with urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception as e:
            if a == 2:
                print(f"UYARI: {url[:70]}... alınamadı: {e}")
                return {}
            time.sleep(2)

def esc(t): return html.escape(t or "", quote=True)
TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
def slug(t):
    s = (t or "").translate(TR_MAP).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50] or "film"

def search_collection(coll):
    q = quote(f'collection:{coll} AND mediatype:movies')
    fields = "&fl[]=identifier&fl[]=title&fl[]=year&fl[]=description&fl[]=downloads&fl[]=runtime"
    url = (f"{IA}/advancedsearch.php?q={q}{fields}"
           f"&sort[]=downloads+desc&rows={ROWS}&page=1&output=json")
    data = fetch_json(url)
    return data.get("response", {}).get("docs", [])

def has_playable(identifier):
    """Öğede gerçekten oynatılabilir mp4/ogv var mı — embed öncesi doğrulama."""
    data = fetch_json(f"{IA}/metadata/{identifier}")
    files = data.get("files", [])
    for f in files:
        fmt = (f.get("format") or "").lower()
        if "512kb mpeg4" in fmt or "h.264" in fmt or fmt.endswith("mp4") or "ogg video" in fmt:
            return True
    return False

def collect(test=False):
    if test:
        return [{"identifier": "night_of_the_living_dead", "title": "Night of the Living Dead",
                 "year": "1968", "description": "Bir grup insan, dirilen ölülere karşı bir çiftlik evinde hayatta kalmaya çalışır.",
                 "downloads": 999999, "runtime": "01:36:00"}]
    seen, out = set(), []
    for coll in COLLECTIONS:
        docs = search_collection(coll)
        print(f"{coll}: {len(docs)} aday")
        added = 0
        for d in docs:
            ident = d.get("identifier")
            title = d.get("title")
            if not ident or not title or ident in seen:
                continue
            if isinstance(title, list): title = title[0]
            if len(title) > 90:
                continue
            seen.add(ident)
            d["title"] = title
            out.append(d)
            added += 1
            if added >= 24:   # koleksiyon başına en iyi 24
                break
        time.sleep(0.5)
    return out

# ---------- ŞABLONLAR ----------
LOGO = """<svg viewBox="0 0 200 200" width="28" height="28" aria-hidden="true"><defs>
<linearGradient id="fg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C50811"/><stop offset="1" stop-color="#99050D"/></linearGradient>
<linearGradient id="fr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FF2A33"/><stop offset="1" stop-color="#E50914"/></linearGradient></defs>
<rect x="82" y="40" width="26" height="120" fill="url(#fg)"/><rect x="74" y="40" width="72" height="26" fill="url(#fr)"/>
<rect x="74" y="92" width="62" height="26" fill="url(#fr)"/><rect x="74" y="40" width="8" height="26" fill="#B5070F"/>
<rect x="74" y="92" width="8" height="26" fill="#B5070F"/></svg>"""

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{background:#0E0E10;color:#F2F2F4;font-family:Outfit,system-ui,sans-serif;line-height:1.6}
header{position:sticky;top:0;background:rgba(14,14,16,.92);border-bottom:1px solid rgba(255,255,255,.07);z-index:10}
.bar{max-width:1100px;margin:0 auto;padding:.7rem 1.2rem;display:flex;align-items:center;gap:.5rem}
.brand{display:flex;align-items:center;gap:.5rem;font-weight:800;color:#F2F2F4;text-decoration:none;font-size:1rem}
.bar nav{margin-left:auto;display:flex;gap:1rem}
.bar nav a{color:#9A9AA3;text-decoration:none;font-size:.88rem;font-weight:600}
main{max-width:1100px;margin:0 auto;padding:2rem 1.2rem 3.5rem}
h1{font-size:1.6rem;font-weight:800;margin-bottom:.3rem}
.sub{color:#9A9AA3;font-size:.9rem;margin-bottom:1.6rem;max-width:640px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1rem}
.film{background:#1C1C21;border:1px solid rgba(255,255,255,.08);border-radius:12px;overflow:hidden;text-decoration:none;color:inherit;transition:transform .15s,border-color .2s;display:block}
.film:hover{transform:translateY(-3px);border-color:#E50914}
.film img{width:100%;aspect-ratio:2/3;object-fit:cover;background:#000}
.film .ft{padding:.6rem .7rem}
.film .ft b{font-size:.85rem;font-weight:700;display:block;line-height:1.3;max-height:2.6em;overflow:hidden}
.film .ft span{font-size:.72rem;color:#9A9AA3}
.badge{display:inline-block;background:rgba(40,184,172,.16);color:#4fd8c8;font-size:.68rem;font-weight:800;padding:.15rem .5rem;border-radius:999px;margin-bottom:.9rem}
.player{width:100%;aspect-ratio:16/9;border:0;border-radius:14px;background:#000}
.pinfo{margin-top:1.2rem}.pinfo h1{font-size:1.4rem}
.pmeta{color:#9A9AA3;font-size:.85rem;margin:.3rem 0 1rem}
.pdesc{color:#D9D9DE;font-size:.92rem;max-width:720px}
.back{display:inline-block;margin-bottom:1.2rem;color:#FF4B54;text-decoration:none;font-weight:600;font-size:.9rem}
footer{border-top:1px solid rgba(255,255,255,.07);padding:1.4rem 1.2rem;text-align:center;color:#9A9AA3;font-size:.78rem;margin-top:2rem}
footer a{color:#9A9AA3}
@media(max-width:560px){.grid{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}}"""

def player_page(f):
    ident = f["identifier"]
    title = f["title"]
    year = str(f.get("year", "") or "")
    desc = f.get("description", "") or ""
    if isinstance(desc, list): desc = " ".join(desc)
    desc = re.sub(r"<[^>]+>", "", desc)[:600]
    runtime = f.get("runtime", "") or ""
    embed = f"{IA}/embed/{ident}"
    canon = f"{BASE_URL}/klasik/{ident}.html"
    return f"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} ({year}) — Ücretsiz İzle (Public Domain) | FilmArşivi</title>
<meta name="description" content="{esc(title)} ({year}) klasik filmini FilmArşivi'nde ücretsiz ve yasal izleyin. Telifsiz (public domain) sinema arşivi.">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)} ({year}) — Ücretsiz İzle">
<meta name="theme-color" content="#0E0E10">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body>
<header><div class="bar"><a class="brand" href="../index.html">{LOGO} FilmArşivi</a>
<nav><a href="../klasik.html">← Klasik Sinema</a></nav></div></header>
<main>
<a class="back" href="../klasik.html">← Tüm klasik filmler</a>
<span class="badge">✓ TELİFSİZ · ÜCRETSİZ İZLE</span>
<iframe class="player" src="{embed}" allowfullscreen frameborder="0" title="{esc(title)}"></iframe>
<div class="pinfo">
<h1>{esc(title)} ({year})</h1>
<div class="pmeta">{esc(runtime) + ' · ' if runtime else ''}Public Domain · Kaynak: Internet Archive</div>
<p class="pdesc">{esc(desc)}</p>
</div>
</main>
<footer>© FilmArşivi · <a href="../index.html">Ana Sayfa</a> · <a href="../klasik.html">Klasik Sinema</a><br>
Film, kamuya açık (public domain) olup Internet Archive üzerinden yayınlanmaktadır.</footer>
</body></html>"""

def gallery_page(films):
    cards = ""
    for f in films:
        ident = f["identifier"]
        title = f["title"]
        year = str(f.get("year", "") or "")
        thumb = f"{IA}/services/img/{ident}"
        cards += (f'<a class="film" href="klasik/{ident}.html">'
                  f'<img src="{thumb}" alt="{esc(title)}" loading="lazy">'
                  f'<div class="ft"><b>{esc(title)}</b><span>{year}</span></div></a>')
    return f"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Klasik Sinema — Ücretsiz &amp; Telifsiz Filmler | FilmArşivi</title>
<meta name="description" content="Telifsiz (public domain) klasik filmleri FilmArşivi'nde ücretsiz ve yasal izleyin: kült korku, bilim kurgu, film noir ve sessiz sinema.">
<link rel="canonical" href="{BASE_URL}/klasik.html">
<meta name="theme-color" content="#0E0E10">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body>
<header><div class="bar"><a class="brand" href="index.html">{LOGO} FilmArşivi</a>
<nav><a href="index.html">Ana Sayfa</a><a href="blog.html">Blog</a></nav></div></header>
<main>
<span class="badge">✓ HEPSİ TELİFSİZ · YASAL · ÜCRETSİZ</span>
<h1>Klasik Sinema</h1>
<p class="sub">Telifi kamuya geçmiş (public domain) klasikleri burada ücretsiz ve yasal izleyebilirsin.
Kült korku filmlerinden film noir'lara, bilim kurgudan sessiz sinemaya — sinema tarihinin taşları.
Filmler Internet Archive üzerinden yayınlanır.</p>
<div class="grid">{cards}</div>
</main>
<footer>© FilmArşivi · <a href="index.html">Ana Sayfa</a><br>
Tüm filmler kamuya açık (public domain) olup Internet Archive üzerinden sunulmaktadır.</footer>
</body></html>"""

def main():
    test = "--test" in sys.argv
    os.makedirs("klasik", exist_ok=True)
    films = collect(test)

    # Oynatılabilirlik doğrulaması (test'te atla)
    valid = []
    for f in films:
        if test or has_playable(f["identifier"]):
            valid.append(f)
        if not test:
            time.sleep(0.3)
    print(f"Oynatılabilir doğrulanan: {len(valid)}/{len(films)}")

    for f in valid:
        with open(f"klasik/{f['identifier']}.html", "w", encoding="utf-8") as fp:
            fp.write(player_page(f))

    with open("klasik.html", "w", encoding="utf-8") as fp:
        fp.write(gallery_page(valid))

    # Ana siteye enjekte için hafif veri
    data = [{"id": f["identifier"], "title": f["title"], "year": str(f.get("year", "") or "")}
            for f in valid]
    with open("klasik-veri.json", "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False)

    print(f"BİTTİ: {len(valid)} klasik film + klasik.html")

if __name__ == "__main__":
    main()
