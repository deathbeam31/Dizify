#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FilmArşivi — otomatik sayfa üretici
Her çalıştığında TMDB'den güncel yapımları çeker ve şunları üretir:
  film/<id>-<isim>.html   her film için SEO sayfası
  dizi/<id>-<isim>.html   her dizi için SEO sayfası
  arsiv.html              tüm sayfaların listesi
  sitemap.xml, robots.txt Google haritası
GitHub Actions bu betiği her gece çalıştırır (bkz. .github/workflows/gunluk.yml)
"""
import json, os, re, sys, time, html
from urllib.request import urlopen, Request

# ==================== AYARLAR ====================
BASE_URL = "https://deathbeam31.github.io/Dizify"   # Domain alınca burayı değiştir (sonda / olmasın)
API_KEY  = "4167c70c2f1823cb24e347d8a88e748b"
API      = "https://api.themoviedb.org/3"           # Actions ABD'de çalışır, TMDB engeli yoktur
IMG      = "https://dizify-api.bsbr-oyunda.workers.dev/t/p"  # Görseller TR ziyaretçi için köprüden
LANG     = "tr-TR"

MOVIE_LISTS = [("/movie/popular", 5), ("/trending/movie/week", 2), ("/movie/top_rated", 3), ("/movie/now_playing", 2)]
TV_LISTS    = [("/tv/popular", 4), ("/trending/tv/week", 2), ("/tv/top_rated", 2)]

# ==================== YARDIMCILAR ====================
def fetch(path, page=1):
    url = f"{API}{path}?api_key={API_KEY}&language={LANG}&page={page}&region=TR"
    req = Request(url, headers={"User-Agent": "FilmArsivi-Bot/1.0"})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                print(f"UYARI: {path} s.{page} alınamadı: {e}")
                return {}
            time.sleep(2)

TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
def slug(text):
    s = (text or "").translate(TR_MAP).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "yapim"

def esc(t): return html.escape(t or "", quote=True)

# ==================== VERİ TOPLAMA ====================
def collect(lists, kind):
    seen = {}
    for path, pages in lists:
        for p in range(1, pages + 1):
            data = fetch(path, p)
            for it in data.get("results", []):
                if it.get("id") and it.get("overview") and it.get("poster_path"):
                    seen[it["id"]] = it
            time.sleep(0.25)
    print(f"{kind}: {len(seen)} yapım toplandı")
    return list(seen.values())

def genre_map(kind):
    data = fetch(f"/genre/{kind}/list")
    return {g["id"]: g["name"] for g in data.get("genres", [])}

def get_providers(kind, mid):
    """Türkiye izleme sağlayıcılarını döndürür: {flatrate:[...], rent:[...], buy:[...]}"""
    data = fetch(f"/{kind}/{mid}/watch/providers")
    tr = (data.get("results") or {}).get("TR") or {}
    def names(key):
        seen, out = set(), []
        for p in tr.get(key, []):
            n = p.get("provider_name")
            if n and n not in seen:
                seen.add(n)
                out.append({"name": n, "logo": p.get("logo_path")})
        return out
    return {"flatrate": names("flatrate"), "rent": names("rent"), "buy": names("buy")}

# ==================== SAYFA ŞABLONU ====================
LOGO = """<svg viewBox="0 0 200 200" width="28" height="28" aria-hidden="true"><defs>
<linearGradient id="fg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C50811"/><stop offset="1" stop-color="#99050D"/></linearGradient>
<linearGradient id="fr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FF2A33"/><stop offset="1" stop-color="#E50914"/></linearGradient></defs>
<rect x="82" y="40" width="26" height="120" fill="url(#fg)"/><rect x="74" y="40" width="72" height="26" fill="url(#fr)"/>
<rect x="74" y="92" width="62" height="26" fill="url(#fr)"/><rect x="74" y="40" width="8" height="26" fill="#B5070F"/>
<rect x="74" y="92" width="8" height="26" fill="#B5070F"/></svg>"""

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{background:#0E0E10;color:#F2F2F4;font-family:Outfit,system-ui,sans-serif;line-height:1.7}
header{position:sticky;top:0;background:rgba(14,14,16,.92);border-bottom:1px solid rgba(255,255,255,.07);z-index:10}
.bar{max-width:800px;margin:0 auto;padding:.7rem 1.2rem;display:flex;align-items:center;gap:.5rem}
.brand{display:flex;align-items:center;gap:.5rem;font-weight:800;color:#F2F2F4;text-decoration:none;font-size:1rem}
main{max-width:800px;margin:0 auto;padding:2rem 1.2rem 3.5rem}
.hero{display:flex;gap:1.4rem;align-items:flex-start;flex-wrap:wrap}
.hero img{width:200px;border-radius:12px;border:1px solid rgba(255,255,255,.1)}
.info{flex:1;min-width:240px}
h1{font-size:1.5rem;font-weight:800;margin-bottom:.3rem}
.meta{display:flex;gap:.8rem;flex-wrap:wrap;color:#9A9AA3;font-size:.85rem;margin-bottom:.9rem}
.meta b{color:#FFB33C}
.genres{margin-bottom:1rem}
.genres span{display:inline-block;background:rgba(229,9,20,.14);color:#FF6B72;font-size:.72rem;font-weight:700;padding:.2rem .6rem;border-radius:999px;margin:0 .25rem .25rem 0}
p.ov{color:#D9D9DE;font-size:.95rem}
.cta{display:inline-block;margin-top:1.3rem;background:linear-gradient(180deg,#FF2A33,#E50914);color:#fff;font-weight:700;text-decoration:none;padding:.65rem 1.4rem;border-radius:999px;font-size:.9rem}
footer{border-top:1px solid rgba(255,255,255,.07);padding:1.4rem 1.2rem;text-align:center;color:#9A9AA3;font-size:.78rem}
footer a{color:#9A9AA3}
.list{columns:2;gap:2rem}
.list a{display:block;color:#D9D9DE;text-decoration:none;font-size:.9rem;padding:.22rem 0;border-bottom:1px solid rgba(255,255,255,.05)}
.list a:hover{color:#FF4B54}
h2{font-size:1.1rem;font-weight:800;margin:1.6rem 0 .7rem}
.providers{margin-top:2.2rem;border-top:1px solid rgba(255,255,255,.08);padding-top:1.6rem}
.providers h2{font-size:1.25rem;font-weight:800;margin-bottom:.6rem}
.pv-intro{color:#D9D9DE;font-size:.95rem;margin-bottom:1.2rem}
.pv-row{margin-bottom:1.1rem}
.pv-row h3{font-size:.95rem;font-weight:700;margin-bottom:.5rem;color:#fff}
.pv-list{display:flex;flex-wrap:wrap;gap:.5rem}
.pv{display:inline-flex;align-items:center;gap:.4rem;background:#1C1C21;border:1px solid rgba(255,255,255,.09);border-radius:10px;padding:.4rem .7rem;font-size:.83rem;font-weight:600}
.pv img{width:22px;height:22px;border-radius:5px}
.pv-note{color:#9A9AA3;font-size:.83rem;margin-top:.5rem}
.pv-empty{color:#9A9AA3;font-size:.9rem;background:rgba(229,9,20,.06);border:1px solid rgba(229,9,20,.18);border-radius:10px;padding:.9rem 1.1rem}
.pv-src{color:#6b6b73;font-size:.75rem;margin-top:1rem}
@media(max-width:560px){.list{columns:1}.hero img{width:150px}}"""

def providers_block(title, year, is_tv, prov):
    """Nerede izlenir bölümü + SEO metni (JSON-LD dahil)."""
    tur = "dizisi" if is_tv else "filmi"
    flat, rent, buy = prov["flatrate"], prov["rent"], prov["buy"]

    def chip(p):
        logo = f'<img src="{IMG}/w45{p["logo"]}" alt="" loading="lazy">' if p["logo"] else ""
        return f'<span class="pv">{logo}{esc(p["name"])}</span>'
    def chips(items):
        return "".join(chip(p) for p in items)

    rows = ""
    if flat:
        names = ", ".join(p["name"] for p in flat)
        rows += f'<div class="pv-row"><h3>📺 Abonelikle (dahil)</h3><div class="pv-list">{chips(flat)}</div>'
        rows += f'<p class="pv-note">{esc(title)} {tur}, Türkiye\'de {esc(names)} aboneliğiyle ek ücret ödemeden izlenebilir.</p></div>'
    if rent:
        rows += f'<div class="pv-row"><h3>💳 Kiralık</h3><div class="pv-list">{chips(rent)}</div></div>'
    if buy:
        rows += f'<div class="pv-row"><h3>🛒 Satın Al</h3><div class="pv-list">{chips(buy)}</div></div>'

    if not (flat or rent or buy):
        body = (f'<p class="pv-empty">{esc(title)} {tur} için şu anda Türkiye\'de abonelikle izlenebilecek '
                f'bir dijital platform bulunmuyor. Yeni platformlar eklendikçe bu sayfa otomatik güncellenir; '
                f'fragmanı ve benzer yapımlar için FilmArşivi ana sayfasını ziyaret edebilirsiniz.</p>')
    else:
        body = rows

    all_names = [p["name"] for p in flat + rent + buy]
    intro = (f'<p class="pv-intro"><strong>{esc(title)} nerede izlenir?</strong> '
             + (f'{esc(title)} ({year}) {tur}, Türkiye\'de {esc(", ".join(dict.fromkeys(all_names)))} '
                f'üzerinden izlenebilir. Güncel izleme seçenekleri aşağıdadır.'
                if all_names else
                f'{esc(title)} ({year}) {tur} için güncel izleme seçenekleri aşağıda listelenmiştir.')
             + '</p>')

    return f'<section class="providers"><h2>Nerede İzlenir?</h2>{intro}{body}' \
           f'<p class="pv-src">Kaynak: JustWatch · TMDB</p></section>'

def page_html(it, kind, genres, prov):
    is_tv = kind == "tv"
    title = it.get("title") or it.get("name") or ""
    year = (it.get("release_date") or it.get("first_air_date") or "")[:4]
    rating = f'{it.get("vote_average", 0):.1f}'
    votes = it.get("vote_count", 0)
    ov = it.get("overview", "")
    gnames = [genres.get(g) for g in it.get("genre_ids", []) if genres.get(g)]
    tur = "dizisi" if is_tv else "filmi"
    flat_names = [p["name"] for p in prov["flatrate"]]
    where = f" {', '.join(flat_names[:2])}'de izlenebilir." if flat_names else ""
    desc = f"{title} ({year}) {tur} nerede izlenir?{where} Konusu, TMDB puanı ({rating}) ve izleme platformları FilmArşivi'nde."
    poster = f"{IMG}/w342{it['poster_path']}"
    canon = f"{BASE_URL}/{'dizi' if is_tv else 'film'}/{it['id']}-{slug(title)}.html"
    gsp = "".join(f"<span>{esc(g)}</span>" for g in gnames)

    # JSON-LD yapısal veri (Google zengin sonuç için)
    schema = {
        "@context": "https://schema.org",
        "@type": "TVSeries" if is_tv else "Movie",
        "name": title, "datePublished": year,
        "genre": gnames, "description": ov[:300],
        "image": poster,
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": rating,
                            "ratingCount": votes, "bestRating": "10"} if votes else None,
    }
    schema = {k: v for k, v in schema.items() if v}

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} ({year}) Nerede İzlenir? Konusu ve Puanı | FilmArşivi</title>
<meta name="description" content="{esc(desc[:158])}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)} ({year}) — Nerede İzlenir? | FilmArşivi">
<meta property="og:description" content="{esc(desc[:158])}">
<meta property="og:image" content="{poster}">
<meta name="theme-color" content="#0E0E10">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<header><div class="bar"><a class="brand" href="../index.html">{LOGO} FilmArşivi</a></div></header>
<main>
<div class="hero">
<img src="{poster}" alt="{esc(title)} afişi" loading="lazy">
<div class="info">
<h1>{esc(title)} ({year})</h1>
<div class="meta"><span><b>★ {rating}</b> / 10</span><span>{votes:,} oy</span><span>{'Dizi' if is_tv else 'Film'}</span></div>
<div class="genres">{gsp}</div>
<p class="ov">{esc(ov)}</p>
<a class="cta" href="../index.html">▶ FilmArşivi'nde fragmanı izle ve keşfet</a>
</div>
</div>
{providers_block(title, year, is_tv, prov)}
</main>
<footer>© FilmArşivi · <a href="../index.html">Ana Sayfa</a> · <a href="../arsiv.html">Arşiv</a><br>
Veri kaynağı: TMDB · JustWatch. Bu site TMDB tarafından onaylanmamıştır.</footer>
</body>
</html>"""

# ==================== ÜRETİM ====================
def main():
    test = "--test" in sys.argv
    if test:
        genres_m = {28: "Aksiyon"}; genres_t = {18: "Dram"}
        movies = [{"id": 1, "title": "Deneme Filmi: Işık & 'Gölge'", "overview": "Test özeti.",
                   "poster_path": "/x.jpg", "vote_average": 7.5, "vote_count": 1234,
                   "release_date": "2026-01-01", "genre_ids": [28]}]
        tvs = [{"id": 2, "name": "Çılgın Şüpheliler", "overview": "Dizi özeti.",
                "poster_path": "/y.jpg", "vote_average": 8.1, "vote_count": 999,
                "first_air_date": "2025-05-05", "genre_ids": [18]}]
    else:
        genres_m = genre_map("movie"); genres_t = genre_map("tv")
        movies = collect(MOVIE_LISTS, "Film")
        tvs = collect(TV_LISTS, "Dizi")

    os.makedirs("film", exist_ok=True); os.makedirs("dizi", exist_ok=True)
    urls, links_m, links_t = [], [], []

    items = ([(m, "movie", genres_m, "film", links_m) for m in movies] +
             [(t, "tv", genres_t, "dizi", links_t) for t in tvs])
    total = len(items)
    for i, (it, kind, genres, folder, links) in enumerate(items, 1):
        title = it.get("title") or it.get("name") or ""
        fname = f"{it['id']}-{slug(title)}.html"
        prov = ({"flatrate": [{"name": "Netflix", "logo": None}], "rent": [], "buy": []}
                if test else get_providers(kind, it["id"]))
        with open(f"{folder}/{fname}", "w", encoding="utf-8") as f:
            f.write(page_html(it, kind, genres, prov))
        urls.append(f"{BASE_URL}/{folder}/{fname}")
        year = (it.get("release_date") or it.get("first_air_date") or "")[:4]
        links.append(f'<a href="{folder}/{fname}">{esc(title)} ({year})</a>')
        if not test:
            time.sleep(0.2)  # TMDB'yi yormamak için
            if i % 50 == 0:
                print(f"  ...{i}/{total} sayfa (sağlayıcı verisiyle)")

    # Arşiv sayfası
    with open("arsiv.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arşiv — Tüm Filmler ve Diziler | FilmArşivi</title>
<meta name="description" content="FilmArşivi'ndeki tüm film ve dizi sayfaları: konular, puanlar ve izleme bilgileri.">
<link rel="canonical" href="{BASE_URL}/arsiv.html">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="bar"><a class="brand" href="index.html">{LOGO} FilmArşivi</a></div></header>
<main><h1>Arşiv</h1>
<p style="color:#9A9AA3;font-size:.85rem;margin:.3rem 0 1rem">Her gece otomatik güncellenir · {len(urls)} yapım</p>
<h2>Filmler ({len(links_m)})</h2><div class="list">{''.join(links_m)}</div>
<h2>Diziler ({len(links_t)})</h2><div class="list">{''.join(links_t)}</div>
</main>
<footer>© FilmArşivi · <a href="index.html">Ana Sayfa</a></footer></body></html>""")

    # Sitemap + robots
    static = [f"{BASE_URL}/", f"{BASE_URL}/blog.html", f"{BASE_URL}/hakkinda.html",
              f"{BASE_URL}/gizlilik.html", f"{BASE_URL}/arsiv.html"]
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in static + urls:
            f.write(f"  <url><loc>{esc(u)}</loc></url>\n")
        f.write("</urlset>\n")
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")

    print(f"BİTTİ: {len(urls)} sayfa + arsiv.html + sitemap.xml + robots.txt")

if __name__ == "__main__":
    main()
