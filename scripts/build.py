#!/usr/bin/env python3
"""data/ 아래 모든 JSON → 저장소 루트의 index.html (폴더 필터 임베드 뷰어).
GitHub Pages가 "main / (root)"에서 바로 서빙할 수 있도록 루트에 생성.
폴더 = data/<폴더명>/<숏코드>.json 구조. Python 표준 라이브러리만 사용.
"""
import html
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
DATA = Path("data")
DEFAULT_FOLDER = "미분류"


def esc(s):
    return html.escape(str(s if s is not None else ""))


def fmt_date(iso):
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%Y-%m-%d")
    except Exception:
        return (iso or "")[:10]


def embed(r):
    sc = r.get("shortcode", "")
    is_reel = r.get("is_reel") or "reel" in (r.get("content_type") or "").lower()
    base = "reel" if is_reel else "p"
    return f"https://www.instagram.com/{base}/{sc}/embed/captioned"


def card(p):
    r = p["record"]
    folder = p["folder"]
    user = r.get("user_posted", "unknown")
    post_url = r.get("url") or f"https://www.instagram.com/p/{r.get('shortcode')}/"
    v = " <span style='color:#0095f6'>✔</span>" if r.get("is_verified") else ""
    h = 700 if (r.get("is_reel") or "reel" in (r.get("content_type") or "").lower()) else 620
    cap = ""
    if (r.get("description") or "").strip():
        cap = ("<details><summary>원문 캡션 보기</summary><div class='cap'>"
               + esc(r["description"]) + "</div></details>")
    cm = ""
    if r.get("top_comments"):
        rows = "".join(
            f"<li>{esc(c['text'])} <span class='d'>{esc(c['date'])}</span></li>"
            for c in r["top_comments"] if c.get("text"))
        if rows:
            cm = (f"<details><summary>댓글 {len(r['top_comments'])}개</summary>"
                  f"<ul class='cmts'>{rows}</ul></details>")
    return f"""<article class="card" data-folder="{esc(folder)}">
<div class="chead"><a href="https://www.instagram.com/{esc(user)}/" target="_blank">@{esc(user)}</a>{v}
<span class="badge">{esc(r.get('content_type',''))}</span>
<span class="folder-tag">📁 {esc(folder)}</span>
<span class="dt">{esc(fmt_date(r.get('date_posted')))}</span>
<span class="saved">저장 {esc(p.get('saved_at','')[:10])}</span></div>
<iframe src="{esc(embed(r))}" width="100%" height="{h}" frameborder="0" scrolling="yes" loading="lazy" allowfullscreen></iframe>
{cap}{cm}
<div class="ft"><span>❤️ {r.get('likes',0):,} · 💬 {r.get('num_comments',0):,}</span>
<a class="btn" href="{esc(post_url)}" target="_blank">인스타에서 보기 ↗</a></div>
</article>"""


def main():
    posts = []
    for f in sorted(DATA.rglob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            rec = d.get("record", d)
            rec.setdefault("shortcode", f.stem)
            folder = (d.get("folder")
                      or (f.parent.name if f.parent.name != "data" else DEFAULT_FOLDER)
                      or DEFAULT_FOLDER)
            posts.append({"saved_at": d.get("saved_at", ""),
                          "folder": folder, "record": rec})
        except Exception as e:
            print(f"⚠️ {f.name} 파싱 실패: {e}")
    posts.sort(key=lambda x: x["saved_at"], reverse=True)

    # 폴더 목록 + 개수 (개수 많은 순 → 이름 순)
    counts = {}
    for p in posts:
        counts[p["folder"]] = counts.get(p["folder"], 0) + 1
    folder_names = sorted(counts, key=lambda n: (-counts[n], n))

    chips = [f'<button class="chip active" data-f="__all__">전체 {len(posts)}</button>']
    chips += [f'<button class="chip" data-f="{esc(n)}">📁 {esc(n)} {counts[n]}</button>'
              for n in folder_names]
    chips_html = "\n".join(chips)
    cards = "\n".join(card(p) for p in posts) or \
        "<div class='empty'>아직 저장된 게시물이 없습니다.<br>Actions에서 Run workflow로 첫 게시물을 저장해 보세요!</div>"

    page = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow"><title>인스타 아카이브</title><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0c0d0e;color:#f3f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;padding:32px 16px}}
.wrap{{max-width:720px;margin:0 auto}}
.pagehd{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #2a2b2e;padding-bottom:16px;margin-bottom:16px}}
h1{{font-size:24px;font-weight:800}}.count{{color:#9ba1a6;font-size:14px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px}}
.chip{{background:#18191b;border:1px solid #2a2b2e;color:#c9ccd1;border-radius:18px;padding:6px 14px;font-size:13px;font-weight:600;cursor:pointer}}
.chip:hover{{border-color:#3b3d42;color:#fff}}
.chip.active{{background:linear-gradient(135deg,#e1306c,#f77737);border-color:transparent;color:#fff}}
.card{{background:#18191b;border:1px solid #2a2b2e;border-radius:12px;padding:20px;margin-bottom:20px}}
.card:hover{{border-color:#3b3d42}}
.chead{{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:14px}}
.card a{{color:#f3f5f7;font-weight:700;text-decoration:none}}
.card a:hover{{text-decoration:underline}}
.badge,.folder-tag{{background:#26272b;color:#9ba1a6;border-radius:10px;padding:1px 9px;font-size:11.5px}}
.dt,.saved,.d{{color:#9ba1a6;font-size:12px}}.saved{{margin-left:auto}}
iframe{{display:block;background:#fff;border-radius:6px;max-width:540px;margin:0 auto 12px}}
details{{border-top:1px solid #2a2b2e;padding-top:10px;margin-bottom:10px;font-size:13.5px}}
summary{{cursor:pointer;color:#9ba1a6;font-size:12.5px}}summary:hover{{color:#fff}}
.cap{{white-space:pre-wrap;color:#d8dade;margin-top:8px}}
.cmts{{margin:8px 0 0 18px}}.cmts li{{margin-bottom:4px;color:#d8dade}}
.ft{{display:flex;justify-content:space-between;align-items:center;color:#9ba1a6;font-size:13px;gap:10px}}
.btn{{color:#fff!important;background:linear-gradient(135deg,#e1306c,#f77737);border-radius:9px;padding:7px 14px;font-size:13px;text-decoration:none}}
.empty{{text-align:center;color:#9ba1a6;padding:60px 0}}
.foot{{margin-top:36px;text-align:center;color:#6b7076;font-size:11.5px;border-top:1px solid #2a2b2e;padding-top:14px}}
@media(max-width:600px){{.ft{{flex-direction:column;align-items:flex-start;gap:8px}}.saved{{margin-left:0}}}}
</style></head><body><div class="wrap">
<div class="pagehd"><h1>◎ 인스타 아카이브</h1><span class="count">{len(posts)}개 저장</span></div>
<div class="chips" id="chips">
{chips_html}
</div>
{cards}
<div class="foot">임베드는 인스타 원본 실시간 표시 — 원본 삭제 시 해당 카드는 빈 화면<br>Generated with Claude · noindex</div>
</div>
<script>
var chips = document.querySelectorAll('.chip');
var cards = document.querySelectorAll('.card');
chips.forEach(function(ch){{
  ch.addEventListener('click', function(){{
    chips.forEach(function(c){{c.classList.remove('active')}});
    ch.classList.add('active');
    var f = ch.getAttribute('data-f');
    cards.forEach(function(card){{
      card.style.display = (f === '__all__' || card.getAttribute('data-folder') === f) ? '' : 'none';
    }});
    window.scrollTo({{top:0, behavior:'smooth'}});
  }});
}});
</script>
</body></html>"""

    (Path("index.html")).write_text(page, encoding="utf-8")
    (Path("robots.txt")).write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    Path(".nojekyll").touch()
    summary = ", ".join(f"{n}:{counts[n]}" for n in folder_names) or "없음"
    print(f"✅ index.html 생성 — 총 {len(posts)}개 (폴더: {summary})")


if __name__ == "__main__":
    main()
