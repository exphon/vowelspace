#!/usr/bin/env python3
"""slide_template_tyoon — 마크다운(.md) → 슬라이드 HTML 한 파일.

    python3 build.py                  # 이 폴더의 slides.md → slides.html
    python3 build.py 발표.md          # 발표.md → 발표.html (md 와 같은 폴더)
    python3 build.py 발표.md --link   # 그림·소리·영상을 HTML 에 넣지 않고 파일을 참조(편집 중 빠른 확인용)
    python3 build.py 발표.md --serve  # 만든 뒤 http://localhost:8000 으로 열기(YouTube 를 슬라이드 안에서 재생할 때)

외부 라이브러리 없이 파이썬 3.9+ 만으로 동작합니다. 작성법은 prompt.md 와 slides.md(예시)를 보세요.
md 맨 위 머리말 주석의 설정(모두 선택):
    title:  브라우저 탭 제목(없으면 첫 장 제목)
    footer: 각 장 왼쪽 아래 문구(없으면 title)
    logo:   로고 그림 경로(기본 img/logo.png, 없으면 이 템플릿 폴더의 img/logo.png, "none"이면 없음).
            첫 장(title)은 제목 위에 크게, 나머지 장은 오른쪽 위에 작게 들어간다.
    output: 만들 HTML 파일 이름(기본 md 이름.html)
수식(LaTeX)은 글 안에서 $…$, 따로 한 줄로는 ::: math 블록에 쓰면 MathJax 가 그린다. MathJax 는 수식이 있는 발표에만 들어가고,
vendor/mathjax/tex-svg-full.js 를 HTML 안에 넣으므로 인터넷 없이도 보인다(--link 이거나 그 파일을 구할 수 없으면 CDN 을 참조).
"""
import base64, html, mimetypes, re, sys
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC = Path(_args[0]).resolve() if _args else TEMPLATE_DIR / "slides.md"
HERE = SRC.parent  # 그림 경로(img/…)는 md 파일이 있는 폴더 기준
EMBED = "--link" not in sys.argv
CONFIG: dict[str, str] = {}

# ── 수식(MathJax) ───────────────────────────────────────
MATHJAX_VERSION = "3.2.2"
MATHJAX_CDN = f"https://cdn.jsdelivr.net/npm/mathjax@{MATHJAX_VERSION}/es5/tex-svg-full.js"
MATHJAX_FILE = TEMPLATE_DIR / "vendor" / "mathjax" / "tex-svg-full.js"
MATH_USED = [False]  # 수식이 하나라도 있으면 MathJax 를 넣는다
# 글 안 수식 $…$: 여는 $ 바로 뒤와 닫는 $ 바로 앞에 빈칸이 없어야 하고, 닫는 $ 뒤에 숫자가 오면 안 된다("$5와 $10"은 수식이 아님. "$x$는"처럼 한글이 붙는 것은 됨). 글자 $ 는 \$ 로 쓴다.
MATH_RE = re.compile(r"(?<![\\$0-9A-Za-z])\$(?!\s)([^$\n]+?)(?<![\s\\])\$(?![\d$])")


def tex_span(src: str) -> str:
    MATH_USED[0] = True
    return '<span class="tex">\\(' + html.escape(src, quote=False) + "\\)</span>"


def math_block(body: list[str]) -> str:
    """::: math 블록: LaTeX 수식을 가운데에 따로 그린다. 빈 줄로 나누면 수식 여러 개."""
    out = []
    for part in re.split(r"\n\s*\n", "\n".join(body).strip()):
        if part.strip():
            MATH_USED[0] = True
            out.append('<div class="tex mathblock">\\[' + html.escape(part.strip(), quote=False) + "\\]</div>")
    return "".join(out)


def mathjax_tag() -> str:
    """MathJax 설정과 본체. 기본은 HTML 안에 넣고(오프라인에서도 보임), --link 이거나 파일을 구할 수 없으면 CDN 을 참조한다."""
    config = ("<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},svg:{fontCache:'global'},"
              "options:{enableMenu:false,ignoreHtmlClass:'slide',processHtmlClass:'tex'},"
              "startup:{ready(){MathJax.startup.defaultReady();MathJax.startup.promise.then(()=>window.mathDone&&mathDone())}}}</script>")
    if EMBED:
        if not MATHJAX_FILE.exists():
            try:  # 템플릿에 MathJax 파일이 없으면 한 번 내려받아 둔다
                import urllib.request
                MATHJAX_FILE.parent.mkdir(parents=True, exist_ok=True)
                MATHJAX_FILE.write_bytes(urllib.request.urlopen(MATHJAX_CDN, timeout=30).read())
                print(f"  MathJax {MATHJAX_VERSION} 를 내려받았습니다: {MATHJAX_FILE}")
            except Exception as e:
                print(f"  ! MathJax 를 내려받지 못해 CDN 을 참조합니다(수식을 보려면 인터넷 필요): {e}")
        if MATHJAX_FILE.exists():
            code = MATHJAX_FILE.read_text(encoding="utf-8").replace("</script", "<\\/script")
            return f"{config}<script>/* MathJax {MATHJAX_VERSION} · Apache License 2.0 · https://www.mathjax.org */\n{code}</script>"
    return f'{config}<script src="{MATHJAX_CDN}"></script>'

# ── 소리·영상·YouTube ───────────────────────────────────
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".flac"}
VIDEO_EXT = {".mp4", ".m4v", ".webm", ".mov", ".ogv"}
MEDIA_MIME = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".wav": "audio/wav", ".ogg": "audio/ogg", ".oga": "audio/ogg",
              ".flac": "audio/flac", ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".ogv": "video/ogg"}
MEDIA_BYTES = [0]  # HTML 에 넣은 소리·영상 크기 합계(경고용)


def youtube_id(src: str):
    """YouTube 주소(watch?v=, youtu.be/, shorts/, embed/, live/)나 11자 id 에서 (id, 시작 초)를 찾는다."""
    m = re.search(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})", src)
    if not m and re.fullmatch(r"[A-Za-z0-9_-]{11}", src):
        return src, 0
    if not m:
        return None
    t = re.search(r"[?&](?:t|start)=(\d+)(?:s)?", src)
    return m.group(1), int(t.group(1)) if t else 0


def media_src(src: str, link: bool) -> str:
    """로컬 소리·영상은 그림처럼 HTML 안에 넣는다(link 이거나 --link 면 파일 경로 그대로)."""
    if link or not EMBED or src.startswith(("http:", "https:", "data:")):
        return src
    p = HERE / src
    if not p.exists():
        print(f"  ! 미디어 없음: {src}")
        return src
    MEDIA_BYTES[0] += p.stat().st_size
    mime = MEDIA_MIME.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def media_block(body: list[str]) -> str:
    """::: media 블록: 첫 줄은 파일 경로나 주소, 다음 줄부터 key: value(caption, start, autoplay, loop, poster, link, height)."""
    lines = [l.strip() for l in body if l.strip()]
    if not lines:
        return ""
    src, opt = lines[0], {}
    for l in lines[1:]:
        if ":" in l:
            k, v = l.split(":", 1)
            opt[k.strip().lower()] = v.strip()
    yes = lambda k: opt.get(k, "").lower() in ("1", "yes", "true", "on", "예")
    cap = f"<figcaption>{inline(opt['caption'])}</figcaption>" if opt.get("caption") else ""
    style = f' style="max-height:{int(opt["height"])}px"' if opt.get("height", "").isdigit() else ""
    auto = " data-autoplay" if yes("autoplay") else ""
    loop = " loop" if yes("loop") else ""
    yt = youtube_id(src)
    if yt:
        vid, start = yt
        start = int(opt.get("start") or start or 0)
        url = f"https://www.youtube.com/watch?v={vid}" + (f"&t={start}s" if start else "")
        return (f'<figure class="media yt" data-yt="{vid}" data-start="{start}"{auto}><div class="yt-box"{style}>'
                f'<img class="yt-thumb" src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="" referrerpolicy="no-referrer">'
                f'<div class="yt-ui"><button type="button" class="yt-play">▶ 여기서 재생</button>'
                f'<a class="yt-open" href="{url}" target="_blank" rel="noopener">YouTube에서 열기 ↗</a>'
                f'<span class="yt-hint">파일로 연 발표에서는 YouTube가 재생을 막을 수 있습니다(오류 153). 그때는 "YouTube에서 열기"나 build.py --serve 를 쓰세요.</span></div>'
                f'</div>{cap}</figure>')
    ext = Path(src.split("?")[0]).suffix.lower()
    s = html.escape(media_src(src, yes("link")), quote=True)
    if ext in AUDIO_EXT:
        return f'<figure class="media audio"{auto}><audio controls preload="metadata"{loop} src="{s}"></audio>{cap}</figure>'
    if ext in VIDEO_EXT:
        poster = f' poster="{img_src(opt["poster"])}"' if opt.get("poster") else ""
        return (f'<figure class="media video"{auto}><video controls playsinline preload="metadata"{loop}{poster}{style} src="{s}"></video>{cap}</figure>')
    print(f"  ! 알 수 없는 미디어 형식: {src}")
    return f'<p><a href="{html.escape(src, quote=True)}" target="_blank" rel="noopener">{html.escape(src)}</a></p>'


# ── 인라인 ─────────────────────────────────────────────
def img_src(src: str) -> str:
    if not EMBED or src.startswith(("http:", "https:", "data:")):
        return src
    p = HERE / src
    if not p.exists() and (TEMPLATE_DIR / src).exists():  # 작업 폴더에 없으면 템플릿 폴더의 그림(로고 등)
        p = TEMPLATE_DIR / src
    if not p.exists():
        print(f"  ! 그림 없음: {src}")
        return src
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()

def inline(t: str) -> str:
    codes: list[str] = []
    def keep(m):
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"
    t = re.sub(r"`([^`]+)`", keep, t)
    def keep_math(m):
        codes.append(tex_span(m.group(1)))
        return f"\x00{len(codes) - 1}\x00"
    t = MATH_RE.sub(keep_math, t).replace("\\$", "$")
    t = html.escape(t, quote=False)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", lambda m: f'<img src="{img_src(m.group(2))}" alt="{m.group(1)}" class="zoomable">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<em>\1</em>", t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], t)
    return t

# ── 블록 ───────────────────────────────────────────────
LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")

def render_list(lines: list[str]) -> str:
    items = []  # (indent, ordered, text)
    for l in lines:
        m = LIST_RE.match(l)
        if m:
            items.append([len(m.group(1)), m.group(2)[0].isdigit(), m.group(3), m.group(2)])
        elif items:
            items[-1][2] += " " + l.strip()
    out, stack = [], []  # stack of (indent, tag)
    for ind, ordered, text, mark in items:
        tag = "ol" if ordered else "ul"
        while stack and ind < stack[-1][0]:
            out.append(f"</li></{stack.pop()[1]}>")
        if not stack or ind > stack[-1][0]:
            start = f' start="{mark[:-1]}"' if ordered and mark[:-1] != "1" else ""
            out.append(f"<{tag}{start}>")
            stack.append((ind, tag))
        else:
            out.append("</li>")
        cls = ""
        cb = re.match(r"\[( |x)\]\s+(.*)", text)
        if cb:
            cls, text = ' class="check"', ("☑ " if cb.group(1) == "x" else "☐ ") + cb.group(2)
        out.append(f"<li{cls}>{inline(text)}")
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)

def render_table(lines: list[str]) -> str:
    bar = lambda l: MATH_RE.sub(lambda m: m.group(0).replace("|", "\x01"), l)  # 수식 안의 | 는 칸을 나누지 않는다
    rows = [[c.strip().replace("\x01", "|") for c in bar(l).strip().strip("|").split("|")] for l in lines]
    head, body = rows[0], [r for r in rows[2:]]
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'

def take_container(lines, i):
    """lines[i] 는 '::: 이름'. (이름, 내용 줄들, 다음 위치)"""
    name, depth, j = lines[i].strip()[3:].strip(), 1, i + 1
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith(":::") and s != ":::":
            depth += 1
        elif s == ":::":
            depth -= 1
            if depth == 0:
                return name, lines[i + 1 : j], j + 1
        j += 1
    return name, lines[i + 1 :], j

def container(name, body):
    if name == "cards":
        cards, cur = [], None
        for l in body:
            if l.startswith("### "):
                cur = [l]
                cards.append(cur)
            elif cur is not None:
                cur.append(l)
        n = len(cards)
        return f'<div class="cards n{n}">' + "".join(f'<div class="card">{blocks(c)}</div>' for c in cards) + "</div>"
    if name == "cols":
        parts, cur = [], []
        for l in body:
            if l.strip() == "+++":
                parts.append(cur)
                cur = []
            else:
                cur.append(l)
        parts.append(cur)
        return '<div class="cols">' + "".join(f'<div class="col">{blocks(p)}</div>' for p in parts) + "</div>"
    if name == "flow":
        items = [LIST_RE.match(l).group(3) for l in body if LIST_RE.match(l)]
        arrow = '<div class="arrow">→</div>'
        return '<div class="flow">' + arrow.join(f'<div class="step">{inline(t)}</div>' for t in items) + "</div>"
    if name == "html":  # 그대로 넣는 HTML(도식 등). src="img/…" 그림은 다른 그림처럼 HTML 안에 넣는다.
        return re.sub(r'src="(img/[^"]+)"', lambda m: f'src="{img_src(m.group(1))}"', "\n".join(body))
    if name == "media":  # 소리·영상·YouTube
        return media_block(body)
    if name == "math":  # LaTeX 수식(MathJax)
        return math_block(body)
    if name == "cmd":  # 명령어 상자: 줄 그대로, # 뒤는 회색 설명
        def one(l):
            m = re.match(r"^(.*?)(\s*#.*)?$", l)
            code, cmt = html.escape(m.group(1)), m.group(2)
            return code + (f'<span class="c">{html.escape(cmt)}</span>' if cmt else "")
        return '<div class="cmd">' + "\n".join(one(l) for l in body) + "</div>"
    if name == "note":
        return f'<div class="note">{blocks(body)}</div>'
    return f'<div class="{html.escape(name)}">{blocks(body)}</div>'

def blocks(lines: list[str]) -> str:
    out, i = [], 0
    while i < len(lines):
        l, s = lines[i], lines[i].strip()
        if not s:
            i += 1
        elif s.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre>" + html.escape("\n".join(lines[i + 1 : j])) + "</pre>")
            i = j + 1
        elif s.startswith(":::"):
            name, body, i = take_container(lines, i)
            out.append(container(name, body))
        elif m := re.match(r"^(#{1,4})\s+(.*)", s):
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            i += 1
        elif s.startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            out.append(render_table(lines[i:j]))
            i = j
        elif LIST_RE.match(l):
            j = i + 1
            while j < len(lines) and lines[j].strip() and (LIST_RE.match(lines[j]) or lines[j].startswith((" ", "\t"))):
                j += 1
            out.append(render_list(lines[i:j]))
            i = j
        elif s.startswith(">"):
            j = i
            while j < len(lines) and lines[j].strip().startswith(">"):
                j += 1
            out.append("<blockquote>" + "".join(f"<p>{inline(x.strip()[1:].strip())}</p>" for x in lines[i:j]) + "</blockquote>")
            i = j
        elif re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", s):
            out.append(f'<figure>{inline(s)}</figure>')
            i += 1
        else:
            j = i
            while j < len(lines) and lines[j].strip() and not re.match(r"^(#|\||>|:::|```|!\[|\s*([-*]|\d+\.)\s)", lines[j].strip()):
                j += 1
            j = max(j, i + 1)
            out.append("<p>" + inline(" ".join(x.strip() for x in lines[i:j])) + "</p>")
            i = j
    return "".join(out)

# ── 슬라이드 ───────────────────────────────────────────
def parse(md: str):
    if m := re.match(r"\A\s*<!--(.*?)-->", md, flags=re.S):  # 파일 머리말(설정 + 작성 메모)
        for line in m.group(1).splitlines():
            if c := re.match(r"^\s*(title|footer|logo|output)\s*:\s*(.+?)\s*$", line):
                CONFIG[c.group(1)] = c.group(2)
        md = md[m.end():]
    slides = []
    for raw in re.split(r"(?m)^---\s*$", md):
        lines = raw.strip("\n").splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            continue
        opts = {}
        if m := re.fullmatch(r"<!--(.*)-->", lines[0].strip()):
            for kv in m.group(1).split("|"):
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    opts[k.strip()] = v.strip()
            lines = lines[1:]
        notes, body, i = "", [], 0
        while i < len(lines):
            if lines[i].strip() == "::: notes":
                _, nl, i = take_container(lines, i)
                notes = blocks(nl)
            else:
                body.append(lines[i])
                i += 1
        slides.append((opts, body, notes))
    return slides

def logo_src() -> str:
    """머리말 logo: 의 그림 주소(HTML 에 넣을 형태). 없거나 none 이면 빈 문자열."""
    logo = CONFIG.get("logo", "img/logo.png")
    if logo.lower() == "none":
        return ""
    if logo.startswith(("http", "data:")) or (HERE / logo).exists() or (TEMPLATE_DIR / logo).exists():
        return img_src(logo)
    return ""

def render_slide(n, total, opts, body, notes):
    layout = opts.get("layout", "default")
    title, rest = "", body
    for k, l in enumerate(body):
        if l.startswith("# "):
            title, rest = inline(l[2:].strip()), body[:k] + body[k + 1 :]
            break
    content = blocks(rest)
    img = opts.get("image")
    cap = inline(opts.get("caption", ""))
    if layout == "title":
        logo_img = f'<img class="logo" src="{CONFIG["_logo"]}" alt="">' if CONFIG.get("_logo") else ""
        inner = f'<div class="title-wrap">{logo_img}<h1>{title}</h1>{content}</div>'
    elif layout == "section":
        num = re.match(r"(\d+)", re.sub("<[^>]+>", "", title))
        inner = f'<div class="section-wrap"><div class="sec-num">{num.group(1) if num else ""}</div><h1>{re.sub(r"^\d+\s*·\s*", "", title)}</h1>{content}</div>'
    elif layout == "quote":
        inner = f'<div class="quote-wrap">{content}</div>'
    elif layout == "split":
        wide = " wide" if opts.get("wide") else ""
        fig = f'<figure class="shot"><img src="{img_src(img)}" alt="" class="zoomable">{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'
        inner = f'<h1>{title}</h1><div class="split{wide}"><div class="text">{content}</div>{fig}</div>'
    elif layout == "image":
        inner = f'<h1>{title}</h1><figure class="hero"><img src="{img_src(img)}" alt="" class="zoomable"></figure>{f"<p class=caption>{cap}</p>" if cap else ""}{content}'
    else:
        inner = (f"<h1>{title}</h1>" if title else "") + content
    fn = opts.get("footnote")
    fnote = f'<div class="fnote">{inline(fn)}</div>' if fn else ""
    foot = "" if layout in ("title", "section") else f'{fnote}<div class="foot"><span>{html.escape(CONFIG.get("footer") or CONFIG.get("title") or "")}</span><span>{n} / {total}</span></div>'
    # 로고: 첫 장(title)은 제목 위의 큰 그림 그대로. 나머지 장은 오른쪽 위의 작은 상자가 CSS 변수(--logo)를 배경으로 쓴다(그림은 한 번만 넣음).
    logo_tag = '<div class="logo" aria-hidden="true"></div>' if CONFIG.get("_logo") and layout != "title" else ""
    return (f'<section class="slide l-{layout}" data-n="{n}">{logo_tag}<div class="body">{inner}</div>{foot}'
            f'<aside class="notes">{notes}</aside></section>')

CSS = r"""
:root{--navy:#14306b;--blue:#2563c9;--violet:#6d4bd1;--teal:#0f8a7e;--ink:#1b2333;--muted:#5b6475;--line:#dfe3ec;--bg:#f6f7fb;--card:#fff;--soft:#eef3fc;--fs:1}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#1d2230;font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",-apple-system,sans-serif;color:var(--ink)}
#stage{position:absolute;left:50%;top:50%;width:1280px;height:720px;transform-origin:center center}
.slide{position:absolute;inset:0;background:var(--bg);overflow:hidden;display:none;flex-direction:column}
.slide.active{display:flex}
.slide::before{content:"";position:absolute;left:0;top:0;width:100%;height:6px;background:linear-gradient(90deg,var(--blue),var(--violet),var(--teal))}
.body{flex:1;padding:44px 64px 16px;display:flex;flex-direction:column;min-height:0;font-size:calc(28px*var(--fs));line-height:1.55}
.foot{display:flex;justify-content:space-between;padding:0 64px 16px;font-size:13px;color:#8a92a3}
.fnote{margin:0 64px 6px;padding-top:6px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}
.fnote a{color:var(--blue)}
h1{font-size:calc(46px*var(--fs));line-height:1.25;margin:0 0 18px;color:var(--navy);letter-spacing:-.02em}
h2{font-size:calc(24px*var(--fs));margin:-8px 0 18px;color:var(--muted);font-weight:600}
h3{font-size:calc(26px*var(--fs));margin:0 0 8px;color:var(--navy)}
p{margin:0 0 12px}ul,ol{margin:0 0 12px;padding-left:1.3em}li{margin:4px 0}li::marker{color:var(--blue)}
li.check{list-style:none;margin-left:-1.2em}
.mathblock{margin:.25em 0 .6em;text-align:center}.mathblock mjx-container{margin:0!important}
mjx-container{color:var(--ink)}li>.mathblock{margin:.2em 0 .35em}
strong{color:var(--navy)}em{color:#364056}
a{color:var(--blue)}
code{font-family:ui-monospace,Menlo,monospace;background:#e8edf7;border-radius:5px;padding:1px 6px;font-size:.88em}
pre{background:#14203b;color:#e7ecf7;border-radius:12px;padding:16px 20px;font-size:calc(20px*var(--fs));line-height:1.6;white-space:pre-wrap;margin:0 0 12px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:calc(23px*var(--fs));margin:0 0 14px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{background:var(--soft);color:var(--navy);text-align:left;font-weight:700;padding:11px 16px;border-bottom:1px solid var(--line)}
td{padding:10px 16px;border-bottom:1px solid #edf0f5;vertical-align:top}tr:last-child td{border-bottom:0}
blockquote{margin:0;padding:0}
.note{background:linear-gradient(90deg,#eaf1ff,#f4efff);border-left:5px solid var(--blue);border-radius:10px;padding:16px 22px;margin-top:auto;font-size:calc(23px*var(--fs))}
.note p:last-child,.note ul:last-child{margin-bottom:0}
.cards{display:grid;gap:18px;margin:0 0 18px}.cards.n2,.cards.n4{grid-template-columns:repeat(2,1fr)}.cards.n3,.cards.n6,.cards.n5{grid-template-columns:repeat(3,1fr)}.cards.n7,.cards.n8{grid-template-columns:repeat(4,1fr)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:0 2px 10px rgba(20,48,107,.05);font-size:calc(22px*var(--fs))}
.card h3{font-size:calc(25px*var(--fs))}.card ul{padding-left:1.1em}.card p:last-child,.card ul:last-child{margin-bottom:0}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:28px;min-height:0;margin-bottom:12px}
.col{min-width:0}.col h3{margin-top:4px}
.col img,figure img{max-width:100%;border-radius:10px;border:1px solid var(--line);box-shadow:0 6px 24px rgba(20,48,107,.12);background:#fff}
.col img{max-height:360px;object-fit:contain;object-position:left top;display:block;margin-bottom:10px}
figure{margin:0}
.flow{display:flex;align-items:stretch;gap:8px;margin:4px 0 22px}
.flow .step{flex:1;background:var(--card);border:1px solid var(--line);border-top:4px solid var(--blue);border-radius:12px;padding:14px;font-size:calc(20px*var(--fs));text-align:center;display:flex;align-items:center;justify-content:center;font-weight:600;color:var(--navy)}
.flow .step:nth-child(4n+3){border-top-color:var(--violet)}.flow .step:nth-child(4n+5){border-top-color:var(--teal)}
.flow .arrow{align-self:center;color:var(--blue);font-size:24px;font-weight:700}
.split{display:grid;grid-template-columns:5fr 6fr;gap:32px;flex:1;min-height:0}.split.wide{grid-template-columns:4fr 7fr}
.split .text{min-width:0;display:flex;flex-direction:column}
.shot{min-height:0;display:flex;flex-direction:column;align-items:center;justify-content:flex-start}
.shot img{max-height:560px;object-fit:contain}
.hero{flex:1;min-height:0;display:flex;justify-content:center}.hero img{max-height:100%;object-fit:contain}
.caption{text-align:center;color:var(--muted);font-size:19px;margin:10px 0 0}
figcaption{color:var(--muted);font-size:15px;margin-top:8px}
.l-title{background:radial-gradient(900px 500px at 15% 10%,#dfe9ff 0,transparent 60%),radial-gradient(800px 500px at 90% 90%,#ece3ff 0,transparent 60%),#fbfcff}
.title-wrap{margin:auto 0;padding-left:20px}.title-wrap .logo{height:96px;margin-bottom:28px}
/* 로고: 첫 장(title)은 제목 위에 크게(96px). 나머지 장은 오른쪽 위에, 제목 글자와 같은 크기(46px)로 제목 줄 가운데 높이에 맞춘다.
   제목 줄은 위 여백 44px + 줄 높이 46×1.25=57.5px 이므로 로고 위치는 44 + (57.5−46)/2. 글자가 줄어들면(--fs) 함께 줄어든다. */
.slide>.logo{position:absolute;top:calc(44px + 5.75px*var(--fs));right:64px;width:calc(46px*var(--fs));height:calc(46px*var(--fs));background:var(--logo) center/contain no-repeat;z-index:1;pointer-events:none}
.slide:not(.l-title):not(.l-section) .body>h1{padding-right:calc(62px*var(--fs))}
.presenter{margin-top:30px;padding:14px 20px;border-left:4px solid var(--blue);background:rgba(37,99,201,.06);border-radius:0 10px 10px 0;display:inline-block;font-size:calc(22px*var(--fs));line-height:1.55;color:var(--ink)}
.presenter p{margin:0}.presenter p+p{margin-top:2px}.presenter strong{color:var(--navy);font-size:1.12em}.presenter a{color:var(--blue)}
.l-title h1{font-size:66px;background:linear-gradient(90deg,var(--navy),var(--blue) 55%,var(--violet));-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:14px}
.l-title h2{font-size:31px;color:#3c4760;margin:0 0 44px}.l-title p{color:var(--muted);font-size:23px}
.l-section{background:linear-gradient(135deg,#14306b 0,#2a4fa3 55%,#5b45c4 100%);color:#fff}
.l-section::before{display:none}
.section-wrap{margin:auto 0;padding-left:40px}.sec-num{font-size:150px;font-weight:800;line-height:1;opacity:.25;margin-bottom:-20px}
.l-section h1{color:#fff;font-size:56px}.l-section h2{color:#cdd8ff;font-size:26px;margin:0}
.l-quote .body{justify-content:center;align-items:center;text-align:center}
.quote-wrap blockquote p{font-size:34px;line-height:1.55;color:var(--navy);font-weight:600;max-width:1000px;margin:0 auto 10px}
.quote-wrap blockquote strong{color:var(--violet)}.quote-wrap>p{margin-top:40px;color:var(--muted);font-size:22px}
.notes{display:none}
/* 도식: Cloudflare Tunnel */
.tun{display:flex;align-items:center;gap:0;margin:6px 0 18px}
.tun-node{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;text-align:center;box-shadow:0 4px 16px rgba(20,48,107,.08);font-size:calc(19px*var(--fs));line-height:1.4;flex:0 0 auto}
.tun-node .ico{font-size:40px;line-height:1;margin-bottom:6px}
.tun-node b{display:block;color:var(--navy);font-size:calc(22px*var(--fs));margin-bottom:4px}
.tun-node span{color:var(--muted);font-size:calc(16px*var(--fs))}
.tun-node.user{width:190px}.tun-node.cf{width:230px;border:2px solid #f38020;background:#fff8f1}.tun-node.cf b{color:#c45a00}
.tun-node.mac{width:270px;border:2px solid var(--blue);background:#f3f7ff}
.tun-node .inner{margin-top:8px;border-radius:10px;padding:7px 8px;font-size:calc(16.5px*var(--fs));font-weight:600;background:#fff;border:1px solid var(--line);color:var(--navy)}
.tun-node .inner.cfd{border-color:#f38020;color:#c45a00}.tun-node .inner.db{background:#eef3fc}
.tun-link{flex:1;display:flex;flex-direction:column;gap:14px;padding:0 10px;min-width:150px}
.tun-arrow{position:relative;text-align:center;font-size:calc(15.5px*var(--fs));color:var(--muted);padding-bottom:9px;line-height:1.35}
.tun-arrow b{color:var(--navy)}
.tun-arrow::before{content:"";position:absolute;left:4px;right:4px;bottom:0;height:3px;background:var(--blue);border-radius:2px}
.tun-arrow.out::before{background:repeating-linear-gradient(90deg,#f38020 0 10px,transparent 10px 16px)}
.tun-arrow::after{content:"";position:absolute;bottom:-6px;border:7.5px solid transparent}
.tun-arrow.r::after{right:-6px;border-left:12px solid var(--blue)}
.tun-arrow.l::after{left:-6px;border-right:12px solid #f38020}
.tun-cap{display:flex;justify-content:space-between;gap:16px;font-size:calc(17px*var(--fs));color:var(--muted)}
/* 웹앱 설치 그림: 휴대폰 틀(실제 화면) + 브라우저 메뉴 그림 */
.phones{display:flex;gap:30px;justify-content:center;align-items:flex-start;margin-top:4px}
.phone-wrap{display:flex;flex-direction:column;align-items:center;gap:8px;width:250px}
.phones.sm{gap:18px}.phones.sm .phone-wrap{width:196px}.phones.sm .phone{width:176px;height:381px;border-width:6px;border-radius:24px}
.phone{position:relative;width:196px;height:424px;border:7px solid #1b2333;border-radius:28px;overflow:hidden;background:#fff;box-shadow:0 10px 28px rgba(20,48,107,.18)}
.phone img.screen{display:block;width:100%;height:100%;object-fit:cover;object-position:top}
.phone .dim{position:absolute;inset:0;background:rgba(0,0,0,.35)}
.phone-cap{font-size:calc(17px*var(--fs));line-height:1.4;text-align:center;color:var(--ink)}
.phone-cap b{color:var(--navy)}
.stepno{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:var(--blue);color:#fff;font-weight:700;font-size:15px;margin-right:4px}
.mock-tag{font-size:13px;color:var(--muted);text-align:center;margin-top:6px}
.sbar{position:absolute;left:0;right:0;bottom:0;height:42px;background:rgba(248,248,250,.97);border-top:1px solid #d8dbe3;display:flex;justify-content:space-around;align-items:center;font-size:17px;color:#2563c9}
.sbar .hl,.cbar .hl,.pc-bar .hl{outline:3px solid #f38020;outline-offset:3px;border-radius:6px}
.sheet{position:absolute;left:6px;right:6px;bottom:6px;background:#f2f3f7;border-radius:14px;padding:8px 0;font-size:13px;box-shadow:0 -4px 16px rgba(0,0,0,.2)}
.sheet .row{display:flex;justify-content:space-between;padding:7px 14px;border-bottom:1px solid #e1e3ea;color:#1b2333}
.sheet .row:last-child{border-bottom:0}
.sheet .row.hl{background:#fff3e8;outline:3px solid #f38020;outline-offset:-3px;font-weight:700}
.home-screen{position:absolute;inset:0;background:linear-gradient(160deg,#5b7fd6,#8a6fd1 60%,#d58fb6);padding:36px 14px;display:grid;grid-template-columns:repeat(4,1fr);gap:16px 8px;align-content:start}
.home-screen .app{display:flex;flex-direction:column;align-items:center;gap:4px;font-size:10px;color:#fff}
.home-screen .app i{display:block;width:36px;height:36px;border-radius:9px;background:rgba(255,255,255,.35)}
.home-screen .app img{width:36px;height:36px;border-radius:9px;background:#fff;box-shadow:0 0 0 3px #f38020}
.home-screen .app.ours{font-weight:700}
.cbar{position:absolute;left:0;right:0;top:0;height:38px;background:#f1f3f4;border-bottom:1px solid #d8dbe3;display:flex;align-items:center;gap:6px;padding:0 8px;font-size:11px;color:#444}
.cbar .url{flex:1;background:#fff;border-radius:14px;padding:4px 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cbar .dots{font-size:18px;line-height:1;padding:0 4px}
.cmenu{position:absolute;right:6px;top:40px;width:150px;background:#fff;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.25);font-size:12px;padding:4px 0}
.cmenu div{padding:7px 12px;color:#1b2333}
.cmenu div.hl{background:#fff3e8;outline:3px solid #f38020;outline-offset:-3px;font-weight:700}
.pc{width:470px;border:1px solid #c9ced8;border-radius:10px;overflow:hidden;background:#fff;box-shadow:0 10px 28px rgba(20,48,107,.15)}
.pc-bar{display:flex;align-items:center;gap:8px;background:#e9ecf1;padding:8px 10px;font-size:13px;color:#444}
.pc-bar .dots3{letter-spacing:2px;color:#c9ced8}
.pc-bar .url{flex:1;background:#fff;border-radius:14px;padding:4px 10px}
.pc-bar .inst{font-size:16px;padding:0 3px}
.pc-body{position:relative;height:250px;background:#f6f6f4}
.pc-body img{width:100%;height:100%;object-fit:cover;object-position:top;opacity:.55}
.pc-dialog{position:absolute;right:12px;top:10px;width:230px;background:#fff;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.25);padding:12px 14px;font-size:13px;color:#1b2333}
.pc-dialog .ttl{font-weight:700;margin-bottom:8px}
.pc-dialog .app{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.pc-dialog .app img{width:28px;height:28px;opacity:1}
.pc-dialog .btns{display:flex;justify-content:flex-end;gap:8px}
.pc-dialog .btns span{padding:4px 10px;border-radius:6px;border:1px solid #c9ced8}
.pc-dialog .btns span.ok{background:#2563c9;color:#fff;border-color:#2563c9;outline:3px solid #f38020;outline-offset:2px}
.cmd{background:#14203b;color:#e7ecf7;border-radius:10px;padding:10px 16px;font-family:ui-monospace,Menlo,monospace;font-size:calc(18px*var(--fs));margin:4px 0 12px;white-space:pre-wrap}
.cmd .c{color:#8fa3c8}
/* 조작 UI */
#bar{position:fixed;left:0;bottom:0;height:4px;background:linear-gradient(90deg,var(--blue),var(--violet));transition:width .25s;z-index:5}
#ui{position:fixed;right:14px;bottom:30px;display:flex;gap:6px;z-index:6;opacity:0;transition:opacity .2s}#ui:hover{opacity:1}
#ui button{background:#fff;border:0;border-radius:8px;padding:6px 11px;font:14px inherit;cursor:pointer;color:var(--navy)}
#notes{position:fixed;left:0;right:0;bottom:0;max-height:32vh;overflow:auto;background:#fffdf3;border-top:3px solid #e8c95a;padding:14px 22px;font-size:16px;line-height:1.6;display:none;z-index:7}
body.show-notes #notes{display:block}
.media{margin:4px 0 14px;display:flex;flex-direction:column;align-items:center}
.media figcaption{text-align:center}
.media.audio{align-items:stretch}.media audio{width:100%;max-width:760px;align-self:center}
.media video{max-width:100%;max-height:430px;border-radius:12px;background:#000;box-shadow:0 6px 24px rgba(20,48,107,.15)}
.yt-box{position:relative;width:100%;max-width:760px;aspect-ratio:16/9;max-height:430px;border-radius:12px;overflow:hidden;background:#0b0f1a;box-shadow:0 6px 24px rgba(20,48,107,.15)}
.yt-box iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.yt-thumb{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.75}
.yt-ui{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,rgba(0,0,0,.55))}
.yt-play{font:700 20px inherit;background:#e62117;color:#fff;border:0;border-radius:999px;padding:12px 26px;cursor:pointer;box-shadow:0 6px 18px rgba(0,0,0,.35)}
.yt-open{font-size:15px;color:#fff;background:rgba(0,0,0,.45);padding:5px 12px;border-radius:999px;text-decoration:none}
.yt-hint{display:none;font-size:13px;color:#e8ecf5;max-width:80%;text-align:center}.file-mode .yt-hint{display:block}
.cols .media video,.cols .yt-box{max-height:300px}
/* 여는 방식에 따라 보이는 글: only-file 은 파일로 열었을 때만, only-web 은 웹 주소(http)로 열었을 때만 */
.only-file,.file-mode .only-web{display:none}.file-mode .only-file{display:block}
.openmode{border-radius:10px;padding:12px 16px;margin:0 0 14px;font-size:calc(20px*var(--fs));line-height:1.45;border-left:5px solid var(--teal);background:#e9f6f4}
.openmode.only-file{border-left-color:#f38020;background:#fff3e8}
/* 판서: 펜·형광펜 */
canvas.ink{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:4}
canvas.ink.hl{mix-blend-mode:multiply;z-index:3}
body.inking canvas.ink.pen{pointer-events:auto;cursor:crosshair;touch-action:none}
body.inking.tool-eraser canvas.ink.pen{cursor:cell}
#inkbar{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);display:none;gap:6px;align-items:center;background:rgba(20,30,50,.92);padding:7px 10px;border-radius:14px;z-index:8;color:#fff;font:13px "Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.3)}
body.inking #inkbar{display:flex}
#inkbar button{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:9px;padding:5px 10px;font:inherit;cursor:pointer}
#inkbar button.on{background:#fff;color:#14306b;font-weight:700}
#inkbar .sep{width:1px;height:22px;background:rgba(255,255,255,.25);margin:0 2px}
#inkbar .sw{width:22px;height:22px;border-radius:50%;padding:0;border:2px solid rgba(255,255,255,.35)}
#inkbar .sw.on{border:3px solid #fff;box-shadow:0 0 0 2px #2563c9}
#check{position:fixed;left:14px;top:14px;max-width:560px;max-height:80vh;overflow:auto;background:#fff;border:2px solid #e8c95a;border-radius:10px;padding:12px 16px;font-size:14px;z-index:8}#check table{font-size:13px;margin:8px 0}#check td,#check th{padding:4px 8px}
/* 한눈에 보기(O): 모든 장을 작게 늘어놓는다. 장은 제 크기(1280×720)로 그린 뒤 줄여 보여 주고,
   줄어든 만큼 여백을 당겨 격자에 맞춘다. */
body.overview #stage{left:0;top:0;right:0;bottom:0;width:auto;height:auto;transform:none!important;overflow:auto;display:flex;flex-wrap:wrap;align-content:flex-start;gap:var(--ovg);padding:52px var(--ovg) 40px}
body.overview .slide{position:relative;inset:auto;display:flex;flex:none;width:1280px;height:720px;transform:scale(var(--ov));transform-origin:0 0;margin:0 calc(-1280px*(1 - var(--ov))) calc(-720px*(1 - var(--ov))) 0;cursor:pointer;border-radius:calc(8px/var(--ov));outline:calc(3px/var(--ov)) solid transparent;outline-offset:calc(2px/var(--ov))}
body.overview .slide *{pointer-events:none}
body.overview .slide:hover{outline-color:rgba(255,255,255,.6)}
body.overview .slide.active{outline-color:#f38020}
body.overview .slide::after{content:attr(data-n);position:absolute;right:calc(10px/var(--ov));bottom:calc(10px/var(--ov));z-index:2;padding:calc(2px/var(--ov)) calc(9px/var(--ov));border-radius:calc(999px/var(--ov));background:rgba(20,30,50,.88);color:#fff;font-size:calc(13px/var(--ov));font-weight:700;line-height:1.5}
body.overview #ui,body.overview #bar,body.overview #inkbar,body.overview #notes,body.overview #help{display:none!important}
#ovhint{display:none;position:fixed;left:50%;top:12px;transform:translateX(-50%);background:rgba(20,30,50,.92);color:#fff;border-radius:8px;padding:6px 14px;font-size:13px;z-index:8;white-space:nowrap}
body.overview #ovhint{display:block}
#zoom{position:fixed;inset:0;background:rgba(10,14,25,.88);display:none;align-items:center;justify-content:center;z-index:9;cursor:zoom-out}
#zoom img{max-width:96vw;max-height:94vh;border-radius:8px}#zoom.on{display:flex}
img.zoomable{cursor:zoom-in}
/* 도움말(A): 기능과 키·단추 표 */
#keys{position:fixed;inset:0;background:rgba(10,14,25,.6);display:none;align-items:center;justify-content:center;z-index:10;padding:16px}
#keys.on{display:flex}
#keys .box{background:#fff;border-radius:14px;padding:18px 24px 14px;width:min(980px,100%);max-height:94vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.45);font-size:14px;line-height:1.45;color:var(--ink)}
#keys h3{font-size:20px;margin:0 0 10px;display:flex;justify-content:space-between;align-items:center}
#keys h4{font-size:14px;margin:0 0 6px;color:var(--blue)}
#keys .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:14px 24px}
#keys table{font-size:13.5px;margin:0;border-radius:10px}#keys th,#keys td{padding:5px 10px}#keys td:first-child{font-weight:600;color:var(--navy);white-space:nowrap}
#keys kbd{display:inline-block;min-width:22px;text-align:center;font:600 12px ui-monospace,Menlo,monospace;background:#f1f4fa;border:1px solid #c9d1e0;border-bottom-width:2px;border-radius:5px;padding:1px 6px;color:var(--navy)}
#keys p{margin:10px 0 0;font-size:12.5px;color:var(--muted)}
#keys-x{background:#eef3fc;border:0;border-radius:8px;padding:4px 10px;font:14px inherit;cursor:pointer;color:var(--navy)}
#help{position:fixed;left:50%;top:14px;transform:translateX(-50%);background:rgba(20,30,50,.85);color:#fff;border-radius:8px;padding:6px 14px;font-size:13px;z-index:6;transition:opacity .6s;white-space:nowrap;max-width:96vw;overflow:hidden;text-overflow:ellipsis}#help.off{opacity:0;pointer-events:none}
@media print{
  @page{size:1280px 720px;margin:0}
  html,body{background:#fff}#stage{position:static;transform:none!important;width:1280px;height:auto}
  .slide{position:relative;display:flex!important;width:1280px;height:720px;page-break-after:always;break-after:page}
  #ui,#bar,#notes,#help,#zoom,#inkbar,#ovhint,#keys{display:none!important}
  .yt-ui button,.yt-hint{display:none!important}
}
"""

JS = r"""
// ── 소리·영상·YouTube ──
const FILE_MODE=location.protocol==='file:';if(FILE_MODE)document.documentElement.classList.add('file-mode');
function ytLoad(fig,auto){const box=fig.querySelector('.yt-box');if(box.querySelector('iframe'))return box.querySelector('iframe');
  const id=fig.dataset.yt,st=+fig.dataset.start||0,f=document.createElement('iframe');
  const origin=location.protocol.startsWith('http')?'&origin='+encodeURIComponent(location.origin):'';
  f.src=`https://www.youtube.com/embed/${id}?enablejsapi=1&rel=0&playsinline=1${st?'&start='+st:''}${auto?'&autoplay=1':''}${origin}`;
  f.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';f.allowFullscreen=true;f.referrerPolicy='strict-origin-when-cross-origin';f.title='YouTube';
  box.innerHTML='';box.appendChild(f);return f}
const ytCmd=(f,func)=>{try{f.contentWindow.postMessage(JSON.stringify({event:'command',func,args:[]}),'*')}catch(e){}};
function mediaLeave(s){s.querySelectorAll('audio,video').forEach(m=>m.pause());s.querySelectorAll('.yt iframe').forEach(f=>ytCmd(f,'pauseVideo'))}
function mediaEnter(s){s.querySelectorAll('.media[data-autoplay]').forEach(fig=>{const m=fig.querySelector('audio,video');
    if(m){m.currentTime=0;m.play().catch(()=>{})}else if(fig.classList.contains('yt')&&!FILE_MODE)ytLoad(fig,true)});
  // 웹 주소로 열었으면 YouTube 플레이어를 미리 띄워 둔다(파일로 열었으면 버튼을 눌러야 시도)
  if(!FILE_MODE)s.querySelectorAll('.yt:not([data-autoplay])').forEach(fig=>ytLoad(fig,false))}
function mediaToggle(s){const m=s.querySelector('audio,video');if(m){m.paused?m.play().catch(()=>{}):m.pause();return}
  const fig=s.querySelector('.yt');if(!fig)return;const f=fig.querySelector('iframe');if(!f){ytLoad(fig,true);fig.dataset.playing='1';return}
  ytCmd(f,fig.dataset.playing==='1'?'pauseVideo':'playVideo');fig.dataset.playing=fig.dataset.playing==='1'?'0':'1'}
document.addEventListener('click',e=>{const b=e.target.closest('.yt-play');if(b){const fig=b.closest('.yt');ytLoad(fig,true);fig.dataset.playing='1'}});
// ── 판서: 펜·형광펜·지우개 (장마다 따로 기억, 슬라이드 좌표 1280×720 로 저장해 화면 크기가 바뀌어도 제자리) ──
const INK={on:false,tool:'pen',ci:{pen:0,hl:0},cur:null,data:new Map()};
const INK_COLORS={pen:['#e5484d','#2563c9','#0f8a7e','#1b2333'],hl:['#ffd400','#7ee787','#ff8fc7','#7cc4ff']};
const INK_W={pen:4,hl:28},INK_R=2;  // 굵기(슬라이드 px), 캔버스 해상도 배율
function inkOf(s){if(!INK.data.has(s))INK.data.set(s,{strokes:[],hist:[]});return INK.data.get(s)}
function inkCanvases(s){let pen=s.querySelector('canvas.ink.pen');if(pen)return[s.querySelector('canvas.ink.hl'),pen];
  const mk=cls=>{const c=document.createElement('canvas');c.className='ink '+cls;c.width=1280*INK_R;c.height=720*INK_R;s.appendChild(c);return c};
  const hl=mk('hl');pen=mk('pen');inkBind(pen,s);inkDraw(s);return[hl,pen]}
function inkStroke(g,st){const p=st.pts;g.save();g.lineCap='round';g.lineJoin='round';g.strokeStyle=st.color;g.lineWidth=st.w;
  if(st.tool==='hl')g.globalAlpha=.42;g.beginPath();g.moveTo(p[0][0],p[0][1]);
  if(p.length<3)g.lineTo(p[p.length-1][0]+.01,p[p.length-1][1]);
  else{for(let i=1;i<p.length-1;i++)g.quadraticCurveTo(p[i][0],p[i][1],(p[i][0]+p[i+1][0])/2,(p[i][1]+p[i+1][1])/2);g.lineTo(p[p.length-1][0],p[p.length-1][1])}
  g.stroke();g.restore()}
function inkDraw(s){const [hl,pen]=[s.querySelector('canvas.ink.hl'),s.querySelector('canvas.ink.pen')];if(!pen)return;
  for(const c of[hl,pen]){const g=c.getContext('2d');g.setTransform(INK_R,0,0,INK_R,0,0);g.clearRect(0,0,1280,720)}
  for(const st of inkOf(s).strokes)inkStroke((st.tool==='hl'?hl:pen).getContext('2d'),st)}
function inkPt(e,c){const r=c.getBoundingClientRect();return[(e.clientX-r.left)*1280/r.width,(e.clientY-r.top)*720/r.height]}
function inkSave(s){const d=inkOf(s);d.hist.push(d.strokes.slice());if(d.hist.length>100)d.hist.shift()}
function inkErase(s,[x,y]){const d=inkOf(s),r=16;const keep=d.strokes.filter(st=>!st.pts.some(([a,b])=>(a-x)**2+(b-y)**2<(r+st.w/2)**2));
  if(keep.length!==d.strokes.length){d.strokes=keep;inkDraw(s)}}
function inkBind(c,s){
  c.addEventListener('pointerdown',e=>{if(!INK.on)return;e.preventDefault();c.setPointerCapture(e.pointerId);inkSave(s);const pt=inkPt(e,c);
    if(INK.tool==='eraser'){INK.cur={erase:true};inkErase(s,pt);return}
    const st={tool:INK.tool,color:INK_COLORS[INK.tool][INK.ci[INK.tool]],w:INK_W[INK.tool]*(e.pointerType==='pen'&&e.pressure?0.6+e.pressure*0.8:1),pts:[pt]};
    inkOf(s).strokes.push(st);INK.cur=st;inkDraw(s)});
  c.addEventListener('pointermove',e=>{const st=INK.cur;if(!st)return;const pt=inkPt(e,c);if(st.erase){inkErase(s,pt);return}
    const l=st.pts[st.pts.length-1];if((l[0]-pt[0])**2+(l[1]-pt[1])**2<2.25)return;st.pts.push(pt);inkDraw(s)});
  const end=()=>{INK.cur=null};c.addEventListener('pointerup',end);c.addEventListener('pointercancel',end)}
function inkSet(on,tool){INK.on=on;if(tool)INK.tool=tool;document.body.classList.toggle('inking',on);
  document.body.classList.toggle('tool-eraser',INK.tool==='eraser');if(on)inkCanvases(slides[cur]);inkBar()}
function inkUndo(){const s=slides[cur],d=inkOf(s);if(!d.hist.length)return;d.strokes=d.hist.pop();inkDraw(s)}
function inkClear(){const s=slides[cur],d=inkOf(s);if(!d.strokes.length)return;inkSave(s);d.strokes=[];inkDraw(s)}
function inkBar(){const b=document.getElementById('inkbar');if(!b)return;
  b.querySelectorAll('[data-tool]').forEach(x=>x.classList.toggle('on',x.dataset.tool===INK.tool));
  const sw=b.querySelector('.sws'),pal=INK.tool==='eraser'?[]:INK_COLORS[INK.tool];
  sw.innerHTML=pal.map((c,i)=>`<button class="sw${i===INK.ci[INK.tool]?' on':''}" data-ci="${i}" title="${i+1}" style="background:${c}"></button>`).join('')}
const slides=[...document.querySelectorAll('.slide')],stage=document.getElementById('stage'),bar=document.getElementById('bar'),notes=document.getElementById('notes');
let cur=0;
slides.forEach((s,i)=>{s.dataset.n=i+1});
// 한눈에 보기(O): 모든 장을 작게 늘어놓고, 눌러서 그 장으로 간다. Esc 는 보던 장으로 돌아간다.
const OV={on:false,from:0,cols:4};
function ovLayout(){const g=16,w=innerWidth;OV.cols=w<700?2:w<1100?3:w<1800?4:5;
  document.body.style.setProperty('--ov',((w-g*(OV.cols+1)-1)/(OV.cols*1280)).toFixed(4));document.body.style.setProperty('--ovg',g+'px')}
function ovSet(on,go){if(on===OV.on)return;OV.on=on;
  if(on){inkSet(false);zoomOff();mediaLeave(slides[cur]);OV.from=cur;ovLayout();document.body.classList.add('overview');slides.forEach(shrink);slides[cur].scrollIntoView({block:'center'})}
  else{document.body.classList.remove('overview');stage.scrollTop=0;fit();show(go===undefined?OV.from:go)}}
function ovMove(i){i=Math.max(0,Math.min(slides.length-1,i));slides[cur].classList.remove('active');cur=i;slides[cur].classList.add('active');slides[cur].scrollIntoView({block:'nearest'})}
function fit(){const s=Math.min(innerWidth/1280,innerHeight/720);stage.style.transform=`translate(-50%,-50%) scale(${s})`}
// 내용이 넘치면 글자를 줄여 슬라이드 안에 맞춘다
function shrink(sl){const b=sl.querySelector('.body');let f=1;const set=v=>{b.style.setProperty('--fs',v);sl.style.setProperty('--fs',v)};set(f);
  const over=()=>b.scrollHeight>b.clientHeight+2||[...b.querySelectorAll('.cols,.split,.cards')].some(e=>e.scrollHeight>e.clientHeight+2);
  while(over()&&f>0.62){f-=0.04;set(f.toFixed(2))}}
function show(i){i=Math.max(0,Math.min(slides.length-1,i));const prev=slides[cur];mediaLeave(prev);prev.classList.remove('active');cur=i;const s=slides[cur];s.classList.add('active');shrink(s);if(prev!==s||!show.done)mediaEnter(s);show.done=1;if(INK.on)inkCanvases(s);INK.cur=null;
  bar.style.width=((cur+1)/slides.length*100)+'%';notes.innerHTML='<b>발표자 노트 ('+(cur+1)+')</b>'+(s.querySelector('.notes').innerHTML||'<p>(없음)</p>');
  history.replaceState(null,'','#'+(cur+1))}
addEventListener('keydown',e=>{
  // 글자 키는 자판의 자리(e.code)로 읽는다. 한글 입력 상태(ㅇ)·대문자(D)·소문자(d) 모두 같은 키로 알아듣게 하기 위함.
  const k=/^Key[A-Z]$/.test(e.code||'')?e.code[3].toLowerCase():e.key;
  // 판서: D 펜, H 형광펜, E 지우개, C 이 장 지우기, Z(또는 ⌘/Ctrl+Z) 되돌리기, 1~4 색, Esc 끄기
  if((e.metaKey||e.ctrlKey)&&(k==='z'||k==='Z')){e.preventDefault();inkUndo();return}
  if(e.metaKey||e.ctrlKey||e.altKey)return;
  // 도움말: A 로 열고 닫는다(Esc 로도 닫힘). 열린 동안에는 다른 키를 받지 않는다.
  if(keysBox.classList.contains('on')){if(k==='Escape'||k==='a'){e.preventDefault();keysSet(false)}return}
  if(k==='a'){keysSet(true);return}
  // 한눈에 보기: O 로 열고 닫는다. 열린 동안에는 화살표로 고르고 Enter 로 그 장을 연다.
  if(OV.on){if(k==='Escape'||k==='o'){ovSet(false);return}
    if(k==='Enter'||k===' '){e.preventDefault();ovSet(false,cur);return}
    const step={ArrowRight:1,ArrowLeft:-1,ArrowDown:OV.cols,ArrowUp:-OV.cols,Home:-1e9,End:1e9}[k];
    if(step!==undefined){e.preventDefault();ovMove(cur+step)}return}
  if(k==='o'){ovSet(true);return}
  if(k==='d'||k==='D'){inkSet(!(INK.on&&INK.tool==='pen'),'pen');return}
  if(k==='h'||k==='H'){inkSet(!(INK.on&&INK.tool==='hl'),'hl');return}
  if(k==='e'||k==='E'){inkSet(!(INK.on&&INK.tool==='eraser'),'eraser');return}
  if(INK.on){if(k==='Escape'){inkSet(false);return}if(k==='c'||k==='C'){inkClear();return}if(k==='z'||k==='Z'){inkUndo();return}
    if(/^[1-4]$/.test(k)&&INK.tool!=='eraser'){INK.ci[INK.tool]=+k-1;inkBar();return}}
  // 소리·영상 조작부에 포커스가 있으면 스페이스·Enter·좌우 키는 그 플레이어가 쓴다
  if(e.target.closest&&e.target.closest('audio,video')&&[' ','Enter','ArrowLeft','ArrowRight'].includes(k))return;
  if(k==='p'||k==='P'){mediaToggle(slides[cur]);return}
  if(document.getElementById('zoom').classList.contains('on')){if(k==='Escape')zoomOff();return}
  if(['ArrowRight','PageDown',' ','Enter'].includes(k)){e.preventDefault();show(cur+1)}
  else if(['ArrowLeft','PageUp','Backspace'].includes(k)){e.preventDefault();show(cur-1)}
  else if(k==='Home')show(0);else if(k==='End')show(slides.length-1);
  else if(k==='f'||k==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}
  else if(k==='n'||k==='N')document.body.classList.toggle('show-notes');
  else if(k==='g'||k==='G'){const n=parseInt(prompt('이동할 슬라이드 번호'));if(n)show(n-1)}});
document.getElementById('prev').onclick=()=>show(cur-1);document.getElementById('next').onclick=()=>show(cur+1);
document.getElementById('nt').onclick=()=>document.body.classList.toggle('show-notes');
document.getElementById('ov').onclick=e=>{e.stopPropagation();ovSet(!OV.on)};
document.getElementById('fs').onclick=()=>document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();
const keysBox=document.getElementById('keys');function keysSet(on){keysBox.classList.toggle('on',on)}
keysBox.addEventListener('click',e=>{e.stopPropagation();if(!e.target.closest('.box')||e.target.closest('#keys-x'))keysSet(false)});
document.getElementById('kh').onclick=e=>{e.stopPropagation();keysSet(true)};
const zoom=document.getElementById('zoom');function zoomOff(){zoom.classList.remove('on')}
document.addEventListener('click',e=>{if(OV.on){const sl=e.target.closest('.slide');if(sl)ovSet(false,slides.indexOf(sl));return}
  const im=e.target.closest('img.zoomable');if(im){zoom.querySelector('img').src=im.src;zoom.classList.add('on')}else if(e.target.closest('#zoom'))zoomOff()});
let tx=null;addEventListener('touchstart',e=>{tx=(INK.on||OV.on)?null:e.touches[0].clientX});addEventListener('touchend',e=>{if(tx===null)return;const d=e.changedTouches[0].clientX-tx;if(Math.abs(d)>50)show(cur+(d<0?1:-1));tx=null});
document.getElementById('inkbar').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  if(b.dataset.tool)inkSet(true,b.dataset.tool);else if(b.dataset.ci){INK.ci[INK.tool]=+b.dataset.ci;inkBar()}
  else if(b.id==='ink-undo')inkUndo();else if(b.id==='ink-clear')inkClear();else if(b.id==='ink-off')inkSet(false)});
document.getElementById('inkbtn').onclick=()=>inkSet(!INK.on,INK.on?null:'pen');inkBar();
addEventListener('resize',()=>{fit();if(OV.on)ovLayout()});addEventListener('beforeprint',()=>{if(OV.on)ovSet(false);slides.forEach(shrink)});
fit();slides.forEach(s=>s.classList.remove('active'));slides[0].classList.add('active');
const h=parseInt(location.hash.slice(1));show(h?h-1:0);
// 점검: 주소 끝에 ?check 를 붙여 열면, 내용이 넘쳐 글자가 줄어든 장(80% 미만)과 다 넣지 못한 장을 표로 보여 준다.
function runCheck(){const rows=[];slides.forEach((s,i)=>{s.classList.add('active');shrink(s);const b=s.querySelector('.body');const f=parseFloat(b.style.getPropertyValue('--fs'))||1;const over=b.scrollHeight>b.clientHeight+2;if(f<0.8||over)rows.push(`<tr><td>${i+1}</td><td>${(s.querySelector('h1')||{}).textContent||''}</td><td>${Math.round(f*100)}%</td><td>${over?'넘침':''}</td></tr>`);s.classList.remove('active')});slides[cur].classList.add('active');
  const d=document.createElement('div');d.id='check';d.innerHTML=`<b>점검 결과</b> (전체 ${slides.length}장) `+(rows.length?`<table><tr><th>장</th><th>제목</th><th>글자 크기</th><th></th></tr>${rows.join('')}</table><p>내용을 줄이거나 두 장으로 나누세요.</p>`:'<p>모든 장이 기본 글자 크기의 80% 이상으로 들어갑니다.</p>');document.body.appendChild(d);window.__check=rows.length}
// 수식(MathJax)이 다 그려진 뒤에 글자 크기를 다시 맞추고, 점검도 그 뒤에 한다.
function mathDone(){if(OV.on)slides.forEach(shrink);else shrink(slides[cur]);if(location.search.includes('check'))runCheck()}
if(location.search.includes('check')&&!document.querySelector('.tex'))runCheck();
setTimeout(()=>document.getElementById('help').classList.add('off'),5000);
"""

KEYS_HTML = '<div id="keys"><div class="box"><h3>기능과 키 · 단추 <button id="keys-x" title="닫기 (Esc)">✕</button></h3><div class="grid"><div><h4>이동 · 보기</h4><table><tr><th>기능</th><th>키</th><th>단추·마우스</th></tr><tr><td>넘기기</td><td><kbd>←</kbd> <kbd>→</kbd> · <kbd>Space</kbd> <kbd>Enter</kbd> · <kbd>PageUp</kbd> <kbd>PageDown</kbd></td><td>◀ ▶ 단추 · 화면 밀기(터치)</td></tr><tr><td>처음 / 끝 장</td><td><kbd>Home</kbd> / <kbd>End</kbd></td><td></td></tr><tr><td>번호로 이동</td><td><kbd>G</kbd></td><td></td></tr><tr><td>한눈에 보기</td><td><kbd>O</kbd></td><td>▦ 한눈에 단추</td></tr><tr><td>└ 장 고르기 · 열기</td><td><kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd> · <kbd>Enter</kbd></td><td>장을 누르기</td></tr><tr><td>└ 닫기(보던 장으로)</td><td><kbd>Esc</kbd> 또는 <kbd>O</kbd></td><td></td></tr><tr><td>전체 화면</td><td><kbd>F</kbd></td><td>전체 단추</td></tr><tr><td>발표자 노트</td><td><kbd>N</kbd></td><td>노트 단추</td></tr><tr><td>소리·영상 재생/멈춤</td><td><kbd>P</kbd></td><td>플레이어 단추</td></tr><tr><td>그림 확대</td><td></td><td>그림 누르기 · <kbd>Esc</kbd>로 닫기</td></tr></table></div><div><h4>판서 · 도움말</h4><table><tr><th>기능</th><th>키</th><th>단추·마우스</th></tr><tr><td>펜</td><td><kbd>D</kbd></td><td>✏️ 펜 단추</td></tr><tr><td>형광펜</td><td><kbd>H</kbd></td><td>🖍 형광펜 단추</td></tr><tr><td>지우개(선 통째로)</td><td><kbd>E</kbd></td><td>🧽 지우개 단추</td></tr><tr><td>색 고르기</td><td><kbd>1</kbd> ~ <kbd>4</kbd></td><td>색 동그라미</td></tr><tr><td>되돌리기</td><td><kbd>Z</kbd> 또는 <kbd>⌘/Ctrl</kbd>+<kbd>Z</kbd></td><td>↶ 되돌리기 단추</td></tr><tr><td>이 장 판서 지우기</td><td><kbd>C</kbd></td><td>이 장 지우기 단추</td></tr><tr><td>판서 끄기</td><td><kbd>Esc</kbd> (같은 키 다시)</td><td>✕ 단추</td></tr><tr><td>이 도움말</td><td><kbd>A</kbd></td><td>？ 도움말 단추</td></tr><tr><td>도움말 닫기</td><td><kbd>Esc</kbd> 또는 <kbd>A</kbd></td><td>바깥 누르기</td></tr></table></div></div><p>단추는 화면 오른쪽 아래에 마우스를 올리면 나옵니다 · 글자 키는 한/영·대소문자와 상관없이 동작합니다 · 판서는 새로고침하면 지워집니다</p></div></div>'

def main():
    if not SRC.exists():
        sys.exit(f"md 파일이 없습니다: {SRC}")
    slides = parse(SRC.read_text(encoding="utf-8"))
    first = next((re.sub(r"^#\s+", "", l) for _, body, _ in slides for l in body if l.startswith("# ")), SRC.stem)
    page_title = CONFIG.get("title") or re.sub(r"[*`]", "", first)
    OUT = HERE / CONFIG.get("output", SRC.stem + ".html")
    total = len(slides)
    CONFIG["_logo"] = logo_src()
    logo_css = f':root{{--logo:url("{CONFIG["_logo"]}")}}' if CONFIG["_logo"] else ""
    body = "".join(render_slide(i + 1, total, *s) for i, s in enumerate(slides))
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(page_title)}</title><style>{logo_css}{CSS}</style></head><body>
<div id="stage">{body}</div><div id="bar"></div><div id="notes"></div>
<div id="ui"><button id="prev" title="이전 (←)">◀</button><button id="next" title="다음 (→)">▶</button><button id="nt" title="발표자 노트 (N)">노트</button><button id="ov" title="모든 장 한눈에 보기 (O)">▦ 한눈에</button><button id="fs" title="전체 화면 (F)">전체</button><button id="inkbtn" title="펜 (D) · 형광펜 (H)">✏️ 펜</button><button id="kh" title="기능과 키 도움말 (A)">？ 도움말</button></div>
<div id="inkbar"><button data-tool="pen" title="펜 (D)">✏️ 펜</button><button data-tool="hl" title="형광펜 (H)">🖍 형광펜</button><button data-tool="eraser" title="지우개 (E)">🧽 지우개</button><span class="sep"></span><span class="sws"></span><span class="sep"></span><button id="ink-undo" title="되돌리기 (Z)">↶ 되돌리기</button><button id="ink-clear" title="이 장 지우기 (C)">이 장 지우기</button><button id="ink-off" title="끄기 (Esc)">✕</button></div>
<div id="help">A 도움말 · ← → 넘기기 · O 한눈에 보기 · F 전체 화면 · N 노트 · G 번호로 이동 · P 재생/멈춤 · D 펜 · H 형광펜 · 그림 클릭 확대</div>
<div id="ovhint">장을 누르면 그 장으로 갑니다 · ← → ↑ ↓ 고르기 · Enter 열기 · Esc 또는 O 닫기</div>
{KEYS_HTML}<div id="zoom"><img alt=""></div><script>{JS}</script>{mathjax_tag() if MATH_USED[0] else ""}</body></html>"""
    OUT.write_text(page, encoding="utf-8")
    if MEDIA_BYTES[0] > 50e6:
        print(f"  ! HTML 에 넣은 소리·영상이 {MEDIA_BYTES[0]/1e6:.0f}MB 입니다. 파일이 무거우면 큰 영상에 'link: 1'을 주고 media/ 폴더를 함께 공유하세요.")
    print(f"{OUT}: 슬라이드 {total}장, {OUT.stat().st_size/1e6:.1f}MB" + (" (그림 포함)" if EMBED else " (그림은 img/ 참조)"))

def serve(out: Path):
    """만든 HTML 을 http://localhost 로 연다(YouTube 가 슬라이드 안에서 재생되도록). Ctrl+C 로 끝."""
    import functools, http.server, socketserver, webbrowser
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out.parent))
    for port in range(8000, 8020):
        try:
            httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    else:
        sys.exit("빈 포트를 찾지 못했습니다(8000~8019).")
    from urllib.parse import quote
    url = f"http://localhost:{port}/{quote(out.name)}"
    print(f"발표 열기: {url}   (끝내려면 Ctrl+C)")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
    if "--serve" in sys.argv:
        serve(HERE / CONFIG.get("output", SRC.stem + ".html"))
