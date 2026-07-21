# -*- coding: utf-8 -*-
"""모래에서 칩까지 — 스모크 하네스
사용: python smoke.py  (프로젝트 루트에서, PYTHONUTF8=1 권장)
검사 영역: HTML 구조 · KO/EN 동등성(코드 구조 동일) · 가시 한글 0 · ACCHEX↔CSS 동기 ·
          SW 프리캐시 무결성 · 위젯 수식 재계산 · 퀴즈 정답 무결성 · i18n/SEO 배선 · 자산 존재
"""
import json, math, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
results = []  # (ok, name, detail)

def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))

def read(fn):
    with open(os.path.join(ROOT, fn), encoding="utf-8") as f:
        return f.read()

KO = read("index.html")
EN = read("en.html")

# ---------------- 1) HTML 파싱: id 수집·중복·텍스트 ----------------
class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.dup, self.stack, self.texts, self.attrs = [], [], [], [], []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            if d["id"] in self.ids: self.dup.append(d["id"])
            self.ids.append(d["id"])
        for k, v in attrs:
            if v:  # 모든 속성값 수집 — 한글 검사에서 화이트리스트 외 전부 잡는다
                self.attrs.append((tag, k, v))
        if tag in ("script", "style"): self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.stack: self.stack.pop()
    def handle_data(self, data):
        if not self.stack and data.strip(): self.texts.append(data)

sko, sen = Scan(), Scan()
sko.feed(KO); sen.feed(EN)
check("KO id 중복 없음", not sko.dup, str(sko.dup[:5]))
check("EN id 중복 없음", not sen.dup, str(sen.dup[:5]))
check("KO/EN id 집합 동일", set(sko.ids) == set(sen.ids),
      f"KO만: {set(sko.ids)-set(sen.ids)} / EN만: {set(sen.ids)-set(sko.ids)}")

REQUIRED_IDS = [
    "s0","s1","s2","s3","s4","s5","s6","s7","s8","s9","s10","s11",
    "bg","veil","topbar","rail","minimap",
    "lamps","naR","k1R","naO","k1O","cdO","cdNote","dofO",
    "yModel","dieR","d0R","waferMap","nDie","nGood","nBad","yPct","wcR","cpd","yFormula",
    "mosCanvas","vgR","vgO","mosState","mosNote",
    "mooreCv","mooreNote","qStem","qOpts","qFb","qScore",
    "scLamps","scCv","scSize","scNote",
    "hbmGen","pinR","pinO","stkR","stkO","bwO","bwNote",
    "mpLamps","mpTgt","mpTgtO","mpCv","mpN","mpTech","mpCost","mpUse",
    "rlChips","rlStepR","rlStepO","rlCv","rlLoops","rlLayers","rlSteps","rlPeriod","rlNote","rlSub",
]
for i in REQUIRED_IDS:
    check(f"필수 id: {i}", i in sko.ids and i in sen.ids)

# ---------------- 2) EN 가시 한글 0 ----------------
hangul = re.compile(r"[가-힣]")
bad_texts = [t.strip()[:40] for t in sen.texts if hangul.search(t)]
check("EN 본문 텍스트 한글 0", not bad_texts, str(bad_texts[:3]))
ATTR_ALLOW = {"Language / 언어"}  # 언어 토글 라벨은 의도적 병기
FONT_ATTR = re.compile(r"맑은 고딕")  # 폰트 스택 병기는 허용
bad_attrs = [(t, k, v[:40]) for t, k, v in sen.attrs
             if hangul.search(v) and v not in ATTR_ALLOW and not FONT_ATTR.search(v)]
check("EN 속성 한글 0(토글·폰트명 제외)", not bad_attrs, str(bad_attrs[:3]))

# JS가 DOM에 주입하는 문자열도 한글 0이어야 한다 (토스트·위젯 note 등)
def scripts_of(text):
    return re.findall(r"<script(?![^>]*application/ld\+json)[^>]*>(.*?)</script>", text, re.S)

def string_literals(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"":
            q, j = c, i + 1
            buf = []
            while j < n and src[j] != q:
                if src[j] == "\\": buf.append(src[j:j+2]); j += 2
                else: buf.append(src[j]); j += 1
            out.append("".join(buf)); i = j + 1
        elif src.startswith("//", i):
            while i < n and src[i] != "\n": i += 1
        elif src.startswith("/*", i):
            j = src.find("*/", i); i = n if j < 0 else j + 2
        else:
            i += 1
    return out

en_js_korean = [s[:40] for blk in scripts_of(EN) for s in string_literals(blk)
                if hangul.search(s) and "맑은 고딕" not in s]
check("EN JS 문자열 리터럴 한글 0", not en_js_korean, str(en_js_korean[:3]))

# ---------------- 3) KO/EN 코드 구조 동일성 ----------------
def strip_code(src):
    """문자열 리터럴·주석 제거 → 코드 골격만"""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"":
            q = c; i += 1
            while i < n and src[i] != q:
                i += 2 if src[i] == "\\" else 1
            i += 1; out.append("$S")
        elif src.startswith("//", i):
            while i < n and src[i] != "\n": i += 1
        elif src.startswith("/*", i):
            j = src.find("*/", i); i = n if j < 0 else j + 2
        else:
            out.append(c); i += 1
    sk = re.sub(r"\s+", "", "".join(out))
    # 문자열 연결 순서 불감화: 번역이 '접두사'+N ↔ N+'접미사'로 재배열해도 골격 동일 취급
    prev = None
    while prev != sk:
        prev = sk
        sk = sk.replace("$S+", "").replace("+$S", "")
    return sk

ks, es = scripts_of(KO), scripts_of(EN)
check("스크립트 블록 수 동일", len(ks) == len(es), f"{len(ks)} vs {len(es)}")
for idx, (a, b) in enumerate(zip(ks, es)):
    check(f"JS 코드 골격 동일 #{idx}", strip_code(a) == strip_code(b),
          "문자열 외 코드가 다름 — KO/EN 동기 위반")

css_ko = re.search(r"<style>(.*?)</style>", KO, re.S).group(1)
css_en = re.search(r"<style>(.*?)</style>", EN, re.S).group(1)
check("CSS 완전 동일", css_ko == css_en)

# ---------------- 4) ACCHEX ↔ CSS --acc 동기 ----------------
for name, text in (("KO", KO), ("EN", EN)):
    acchex = re.search(r"const ACCHEX = \[([^\]]+)\]", text).group(1)
    js_cols = re.findall(r"'(#[0-9a-fA-F]{6})'", acchex)
    css_cols = {int(m.group(1)): m.group(2) for m in
                re.finditer(r'data-stage="(\d+)"\]\{--acc:(#[0-9a-fA-F]{6})\}', text)}
    ok = len(js_cols) == 12 and all(js_cols[i] == css_cols.get(i) for i in range(1, 11)) \
         and js_cols[0] == "#38e1ff" and js_cols[11] == "#b18cff"
    check(f"{name} ACCHEX↔CSS 12색 동기", ok, f"js={js_cols} css={css_cols}")

# ---------------- 5) SW 프리캐시 무결성 ----------------
SW = read("sw.js")
check("SW 캐시 버전 형식", re.search(r"const CACHE = 's2c-v\d+'", SW))
pre = re.findall(r"'\./([^']*)'", re.search(r"PRECACHE = \[(.*?)\]", SW, re.S).group(1))
pre_files = [p for p in pre if p]  # '' == './' 루트
for p in pre_files:
    check(f"프리캐시 파일 존재: {p}", os.path.exists(os.path.join(ROOT, p)))
deploy_assets = {f for f in os.listdir(ROOT)
                 if re.search(r"\.(html|png|js|webmanifest)$", f)
                 and f not in ("index.html", "sw.js")}
missing = deploy_assets - set(pre_files)
check("배포 자산 전부 프리캐시에 포함", not missing, f"누락: {missing}")

# ---------------- 6) 위젯 수식 재계산 + 수식 문자열 앵커 ----------------
# 상수 앵커 (출현 횟수까지 고정 — 한 행만 오손돼도 검출)
for name, text in (("KO", KO), ("EN", EN)):
    for anchor, cnt in [("const VTH = 45", 1), ("min:38}", 1), ("min:13}", 1), ("min:8}", 1),
                        ("masks:40", 1), ("masks:90", 1), ("masks:35", 1), ("masks:30", 1),
                        ("2.08e11", 1), ("C1=1e12", 1), ("l:13.5", 2),
                        ("2048, 8.0", 1), ("1024, 9.2", 1), ("const AVG_H = 2.0", 1)]:
        check(f"{name} 상수 앵커 ×{cnt}: {anchor}", text.count(anchor) == cnt,
              f"실제 {text.count(anchor)}회")
    # 위젯 수식 축자 앵커 — 양 파일에 동일하게 든 수식 회귀도 잡는다
    for formula in ["const cd = k1()*s.l/na()",
                    "const dof = 0.5*s.l/(na()*na())",
                    "f:ad=>Math.exp(-ad)",
                    "Math.pow((1-Math.exp(-ad))/ad, 2)",
                    "Math.pow(1+ad/3, -3)",
                    "const per = s[1]*pin/8",
                    "Math.ceil(minHp/tgt)",
                    "const totalSteps = c.masks * spl",
                    "const periodDays = totalSteps * AVG_H / 24",
                    "const k = kLin*kLin",
                    "Math.exp(-A*D0)"]:
        check(f"{name} 수식 앵커: {formula[:34]}", formula in text)
    # 리소 위젯 기본값 앵커 (CD 15.9nm·DOF 76nm 재계산의 전제)
    for dv in ['id="naR" min="0" max="100" value="60"', 'id="k1R" min="25" max="80" value="35"']:
        check(f"{name} 기본값 앵커: {dv[:24]}", dv in text)

cd = 0.35 * 13.5 / 0.298
check("레일리 CD(EUV 기본) ≈ 15.9nm", abs(cd - 15.86) < 0.05, f"{cd:.2f}")
dof = 0.5 * 13.5 / 0.298**2
check("DOF(EUV 기본) ≈ 76nm", abs(dof - 76.0) < 0.5, f"{dof:.1f}")
ad = 4.84 * 0.10
p_, m_, nb = math.exp(-ad), ((1 - math.exp(-ad)) / ad) ** 2, (1 + ad / 3) ** -3
check("수율 3모델 순서 푸아송<머피<음이항", p_ < m_ < nb, f"{p_:.3f} {m_:.3f} {nb:.3f}")
check("HBM4 8스택 = 16.38TB/s", abs(2048 * 8 / 8 * 8 / 1000 - 16.384) < 0.001)
mp = [(38, 19, 2), (38, 10, 4), (38, 8, 5), (13, 8, 2), (8, 6, 2)]
for mn, tgt, n in mp:
    check(f"멀티패터닝 ceil({mn}/{tgt})={n}", math.ceil(mn / tgt) == n)
check("루프 카운터 90×10 → 2.5개월", abs(90 * 10 * 2.0 / 24 / 30 - 2.5) < 0.01)

# ---------------- 7) 퀴즈 정답 무결성 (정답 판정 = 문자열 비교) ----------------
for name, text in (("KO", KO), ("EN", EN)):
    names_m = re.search(r"const NAMES = \[([^\]]+)\]", text)
    q_block = re.search(r"const Q = \[(.*?)\n  \];", text, re.S)
    names = set(re.findall(r"'([^']+)'", names_m.group(1)))
    answers = set(re.findall(r"a:'([^']+)'", q_block.group(1)))
    check(f"{name} 퀴즈 정답 ⊆ 보기 이름", answers <= names, f"불일치: {answers - names}")

# ---------------- 8) i18n·SEO 배선 ----------------
ALTS = ['hreflang="ko" href="https://stkeo.github.io/sand-to-chip/"',
        'hreflang="en" href="https://stkeo.github.io/sand-to-chip/en.html"',
        'hreflang="x-default" href="https://stkeo.github.io/sand-to-chip/"']
for a in ALTS:
    check(f"KO hreflang: {a[:30]}", a in KO)
    check(f"EN hreflang: {a[:30]}", a in EN)
check("KO canonical=루트", 'rel="canonical" href="https://stkeo.github.io/sand-to-chip/"' in KO)
check("EN canonical=en.html", 'rel="canonical" href="https://stkeo.github.io/sand-to-chip/en.html"' in EN)
check("KO og:locale=ko_KR", 'property="og:locale" content="ko_KR"' in KO)
check("EN og:locale=en_US", 'property="og:locale" content="en_US"' in EN)
check("KO og:image=og.png", "sand-to-chip/og.png" in KO and "og-en.png" not in KO)
check("EN og:image=og-en.png", "sand-to-chip/og-en.png" in EN)
check('KO <html lang="ko">', '<html lang="ko">' in KO)
check('EN <html lang="en">', '<html lang="en">' in EN)
for name, text, lang in (("KO", KO, "ko"), ("EN", EN, "en")):
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1))
    check(f"{name} JSON-LD 파싱+inLanguage={lang}", ld.get("inLanguage") == lang)
check("KO 토글 활성=KO", re.search(r'href="\./" hreflang="ko" lang="ko" class="on"', KO))
check("EN 토글 활성=EN", re.search(r'href="\./en\.html" hreflang="en" lang="en" class="on"', EN))
for name, text in (("KO", KO), ("EN", EN)):
    check(f"{name} SW 등록 존재", "serviceWorker.register('./sw.js')" in text)
    check(f"{name} manifest 링크", 'rel="manifest" href="./manifest.webmanifest"' in text)

# ---------------- 9) 자산·주변 파일 ----------------
mf = json.loads(read("manifest.webmanifest"))
check("manifest 파싱+아이콘 2종", len(mf.get("icons", [])) == 2)
for ic in mf.get("icons", []):
    check(f"manifest 아이콘 존재: {ic['src']}", os.path.exists(os.path.join(ROOT, ic["src"])))
check("three.min.js 존재·정상 크기", os.path.getsize(os.path.join(ROOT, "three.min.js")) > 500_000)
p404 = read("404.html")
check("404: KO/EN 홈 링크", 'href="./"' in p404 and 'href="./en.html"' in p404)
for i in range(12):
    check(f"레일 앵커 대상 존재: #s{i}", f'id="s{i}"' in KO and f'id="s{i}"' in EN)
check("itch 크로스링크(양 파일)", KO.count("stkeo.itch.io/cleanroom-tycoon") >= 2
      and EN.count("stkeo.itch.io/cleanroom-tycoon") >= 2)

# ---------------- 리포트 ----------------
fails = [(n, d) for ok, n, d in results if not ok]
print(f"스모크 {len(results)}개 — 통과 {len(results) - len(fails)} / 실패 {len(fails)}")
for n, d in fails:
    print(f"  FAIL {n}  {d}")
sys.exit(1 if fails else 0)
