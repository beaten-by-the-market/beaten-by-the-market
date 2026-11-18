"""README.md의 '최근 글' 목록을 네이버 블로그 글 데이터로 갱신합니다.

데이터는 블로그 레포(beaten-by-the-market.github.io)가 매시간 RSS로 쌓는
_data/naver_posts.json을 그대로 씁니다. RSS에서 빠진 예전 글도 목록에 남습니다.

사용법:
    python scripts/update_readme.py                 # 원격 JSON으로 갱신
    python scripts/update_readme.py --source FILE   # 로컬 JSON으로 갱신(테스트용)

종료 코드는 성공 시 0, 데이터 오류 시 1입니다. 변경 여부는 출력의 changed=로 알립니다.
Python 표준 라이브러리만 사용합니다.
"""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

SOURCE_URL = ("https://raw.githubusercontent.com/beaten-by-the-market/"
              "beaten-by-the-market.github.io/master/_data/naver_posts.json")
README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- NAVER-POSTS:START -->"
END = "<!-- NAVER-POSTS:END -->"
VISIBLE = 10  # 펼쳐서 보여 줄 최신 글 수. 나머지는 접어 둡니다.
POST_URL = re.compile(r"https://m\.blog\.naver\.com/beatenbythemarket/\d+")
MAX_BYTES = 5_000_000


def load(source):
    if source:
        return json.loads(Path(source).read_text(encoding="utf-8"))
    request = Request(SOURCE_URL, headers={"User-Agent": "beaten-by-the-market profile README"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read(MAX_BYTES))


def escape(text):
    # 제목 속 마크다운 특수문자가 링크나 서식으로 해석되지 않게 합니다.
    return re.sub(r"([\\`*_\[\]<>|])", r"\\\1", " ".join(text.split()))


def validate(posts):
    if not isinstance(posts, list) or not posts:
        raise ValueError("post list is empty or not a list")
    for post in posts:
        if not isinstance(post, dict) or not isinstance(post.get("title"), str) or not post["title"].strip():
            raise ValueError(f"invalid post: {post!r}")
        if not isinstance(post.get("url"), str) or not POST_URL.fullmatch(post["url"]):
            raise ValueError(f"unexpected post URL: {post.get('url')!r}")


def line(post):
    date = (post.get("date") or "")[:10] or "날짜 없음"
    text = f"- {date} · [{escape(post['title'])}]({post['url']})"
    if post.get("category"):
        text += f" <sub>{escape(post['category'])}</sub>"
    return text


def render(posts):
    posts = sorted(posts, key=lambda p: (p.get("date") or "", p["url"]), reverse=True)
    lines = [line(p) for p in posts[:VISIBLE]]
    rest = posts[VISIBLE:]
    if rest:
        # <summary> 뒤 빈 줄이 있어야 GitHub이 안쪽 목록을 마크다운으로 렌더링합니다.
        lines += ["", f"<details><summary>이전 글 {len(rest)}편 더 보기</summary>", ""]
        lines += [line(p) for p in rest]
        lines += ["", "</details>"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", help="원격 대신 읽을 로컬 JSON 파일")
    args = parser.parse_args()

    posts = load(args.source)
    validate(posts)

    readme = README.read_text(encoding="utf-8")
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) > readme.index(END):
        print("Error: README markers are missing or out of order", file=sys.stderr)
        return 1
    head, rest = readme.split(START)
    _, tail = rest.split(END)
    updated = f"{head}{START}\n{render(posts)}\n{END}{tail}"

    changed = updated != readme
    if changed:
        README.write_text(updated, encoding="utf-8", newline="\n")
    print(f"posts={len(posts)} changed={str(changed).lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
