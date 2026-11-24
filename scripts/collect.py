#!/usr/bin/env python3
"""인스타 게시물 수집 — Apify REST API.
사용법: collect.py <URL> [폴더명]
폴더명을 새로 입력하면 data/ 아래에 자동 생성된다. (기본값: 미분류)
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
TOKEN = os.environ["APIFY_TOKEN"]
SC_RE = re.compile(r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")
DATA = Path("data")


def shortcode_from(url: str) -> str:
    url = (url or "").strip()
    m = SC_RE.search(url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{5,}", url):
        return url
    raise SystemExit("❌ 인스타 게시물 주소가 아닙니다: " + url)


def clean_folder(name: str) -> str:
    """폴더 이름 정리: 앞뒤 공백 제거, 경로 특수문자 제거, 길이 제한"""
    name = (name or "").strip()
    name = re.sub(r'[\\/:*?"<>|]+', "", name)  # 파일경로로 쓸 수 없는 문자 제거
    name = name or "미분류"
    return name[:30]


def find_existing(sc: str):
    """data/ 전체에서 이미 저장된 게시물 찾기 (폴더 상관없이 중복 방지)"""
    if not DATA.exists():
        return None
    for p in DATA.rglob(f"{sc}.json"):
        return p
    return None


def main():
    if len(sys.argv) < 2:
        raise SystemExit("사용법: collect.py <URL> [폴더명]")
    folder = clean_folder(sys.argv[2] if len(sys.argv) > 2 else "")
    sc = shortcode_from(sys.argv[1])

    existing = find_existing(sc)
    if existing:
        print(f"⏭️ 이미 저장된 게시물: {sc} (폴더: {existing.parent.name})")
        return

    canon = f"https://www.instagram.com/p/{sc}/"
    print(f"⏳ 수집 시작: {sc} → 폴더 [{folder}]")
    api = (f"https://api.apify.com/v2/acts/apify~instagram-scraper/"
           f"run-sync-get-dataset-items?token={TOKEN}&timeout=120")
    body = json.dumps({"directUrls": [canon], "resultsType": "posts",
                       "resultsLimit": 1}).encode()
    req = urllib.request.Request(api, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        items = json.loads(r.read().decode())
    if not items:
        raise SystemExit("❌ 수집 결과 없음 — 삭제·비공개 게시물이거나 주소를 다시 확인하세요")
    raw = items[0]
    # 릴스 판별: type 텍스트 또는 productType(clips) 기준
    is_reel = ("reel" in (raw.get("type") or "").lower()
               or (raw.get("productType") or "") == "clips")
    comments_raw = raw.get("latestComments") or raw.get("comments") or []
    rec = {
        "shortcode": sc,
        "url": canon,
        "user_posted": raw.get("ownerUsername", ""),
        "description": raw.get("caption", ""),
        "likes": raw.get("likesCount", 0),
        "num_comments": raw.get("commentsCount", 0),
        "photos_number": (raw.get("imagesCount")
                          or len(raw.get("childPosts") or [])
                          or len(raw.get("images") or []) or 0),
        "date_posted": raw.get("timestamp", ""),
        "content_type": raw.get("type", "Post"),
        "is_reel": is_reel,
        "is_verified": raw.get("isVerified", False),
        "top_comments": [
            {"text": c.get("text", ""),
             "date": (c.get("ts") or c.get("timestamp") or "")[:10]}
            for c in comments_raw[:12]
            if c.get("text")
        ],
    }
    out_dir = DATA / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    wrap = {
        "saved_at": datetime.now(KST).isoformat(timespec="seconds"),
        "source": "apify",
        "folder": folder,
        "record": rec,
    }
    (out_dir / f"{sc}.json").write_text(
        json.dumps(wrap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ 수집 완료: data/{folder}/{sc}.json  "
          f"(@{rec['user_posted']} · ❤️{rec['likes']:,} · 💬{rec['num_comments']:,})")


if __name__ == "__main__":
    main()
