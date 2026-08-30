# 해외 주식 데일리 브리핑

매일 아침 미국 증시 마감 데이터와 해외 뉴스를 모아 한국어 리포트를 만드는 프로그램입니다.
HTML · 마크다운 파일로 저장하고, 원하면 텔레그램으로도 보냅니다.

```
report/latest.html          ← 항상 최신 리포트 (브라우저 시작페이지용 고정 경로)
report/brief-2026-08-30.html
report/brief-2026-08-30.md
```

> **PC를 꺼도 매일 받고 싶다면 → [SETUP-CLOUD.md](SETUP-CLOUD.md)**
> GitHub의 무료 서버가 대신 돌리게 하고, 텔레그램 푸시 + 웹 주소로 받습니다.
> 아래 내용은 이 PC에서 직접 돌릴 때의 설명입니다.

---

## 1. 설치

```bash
pip install -r requirements.txt
```

## 2. API 키 설정

`.env.example` 을 `.env` 로 복사하고 값을 채웁니다.

| 키 | 필요성 | 발급처 |
|---|---|---|
| `ANTHROPIC_API_KEY` | 한국어 뉴스 번역·시장 총평에 필요 | console.anthropic.com |
| `FINNHUB_API_KEY` | 선택 (yfinance 실패 시 대체) | finnhub.io/register |
| `ALPHAVANTAGE_API_KEY` | 선택 (두 번째 대체) | alphavantage.co |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | 선택 (텔레그램 전송) | 텔레그램 @BotFather |

키가 없어도 프로그램은 돌아갑니다. `ANTHROPIC_API_KEY` 가 없으면 **뉴스가 영문 원문 그대로** 나오고
시장 총평 섹션이 빠집니다. 나머지 시세·섹터·상승하락 데이터는 정상입니다.

`.env` 는 `.gitignore` 에 들어 있습니다. 절대 공유하거나 커밋하지 마세요.

## 3. 실행

```bash
python run.py --open
```

| 옵션 | 설명 |
|---|---|
| `--open` | 만든 뒤 브라우저로 열기 |
| `--no-ai` | Claude 요약 없이 데이터만 (빠르고 무료) |
| `--no-movers` | 상승/하락 상위 스캔 생략 |
| `--no-news` | 뉴스 수집 생략 |
| `--telegram` | 텔레그램으로도 전송 |
| `-v` | 디버그 로그 |

전체 실행에 약 10초 (+ AI 요약 20~40초) 걸립니다.

## 4. 매일 자동 실행

미국 증시는 한국시간 새벽 5~6시에 마감합니다. 기본값은 아침 7시입니다.

```powershell
.\setup-schedule.ps1
```

```powershell
.\setup-schedule.ps1 -Time "06:40"   # 시간 변경
.\setup-schedule.ps1 -Remove         # 등록 해제
Start-ScheduledTask -TaskName StockDailyBrief   # 지금 한 번 테스트
```

실행 로그는 `report/run.log` 에 쌓입니다.

## 5. 브라우저 시작페이지로 띄우기

Chrome → 우측 상단 ⋮ → **설정 → 시작 그룹 → 특정 페이지 열기 → 새 페이지 추가**

```
file:///D:/claud/stock-brief/report/latest.html
```

`latest.html` 은 매번 같은 경로에 덮어쓰므로, 아침에 크롬을 켜면 그날 브리핑이 바로 뜹니다.
(새 탭 페이지는 크롬 정책상 바꿀 수 없어 **시작 그룹**을 씁니다. 홈 버튼에 같은 주소를 넣어두면
언제든 한 번의 클릭으로 다시 볼 수 있습니다.)

---

## 설정 바꾸기 — `config.yaml`

**관심 종목 추가**

```yaml
watchlist:
  - { symbol: "AAPL", name: "애플" }
  - { symbol: "SMCI", name: "슈퍼마이크로" }   # 이렇게 한 줄 추가
```

**AI 요약 비용 조절**

```yaml
ai:
  model: claude-opus-5
  effort: medium      # low → 싸고 빠름, high/xhigh/max → 꼼꼼하지만 비쌈
```

**뉴스 필터** — `exclude_patterns` 는 제목에 매칭되는 정규식입니다.
개인 재무상담 칼럼이나 금리 광고처럼 시장과 무관한 기사를 걸러냅니다. 정규식에
백슬래시를 쓸 일이 생기면 YAML 홑따옴표(`'...'`)를 쓰세요.

**상승/하락 스캔 대상** — `briefing/data/universe.py` 의 대형주 120종목 리스트를 편집합니다.

---

## 리포트에 들어가는 것

| 섹션 | 내용 |
|---|---|
| 급등락 알림 | 관심 종목이 ±5%(설정 가능)를 넘으면 맨 위에 표시 |
| 시장 총평 | Claude가 쓰는 한국어 요약 + 오늘의 관전 포인트 |
| 주요 지수 | S&P 500, 나스닥, 다우, 러셀 2000, VIX |
| 글로벌 증시 | 유로스톡스50·독일·영국·프랑스·스위스·네덜란드·스웨덴·캐나다·일본·호주·한국·홍콩·중국 |
| G10 통화 | 유로·파운드·엔·스위스프랑·캐나다달러·호주달러·뉴질랜드달러·크로나·크로네 + 유로/원, 엔/원 |
| 매크로 | 10년물 금리(bp), 달러인덱스, 원/달러, WTI, 금, 비트코인 |
| 섹터별 등락 | GICS 11섹터 ETF를 막대로 |
| 관심 종목 | 종가·등락·52주 위치·고점 대비·거래량 |
| 상승·하락 상위 | 대형주 120종목 스캔 |
| 앞으로 예정된 일정 | FOMC(연준 공식), 고용보고서, 관심종목 실적 발표일 |
| 주요 뉴스 | RSS 5개 피드 → 한국어 번역 |
| 내 관심 종목 소식 | 종목별 뉴스 → 한국어 번역 |
| 오늘의 공부 | 주식 용어 1개 + 투자 심리 1개 (매일 순환) |
| 내일의 기술 | 미래 기술 25편을 책처럼 하루 한 챕터씩 (AI·로봇·바이오·에너지·우주·사회) |

**일정 섹션에 대해** — 예측이 아니라 이미 공표된 일정만 다룹니다. FOMC 회의일은 연준 공식
캘린더에서 직접 읽어옵니다. CPI 발표일 등 BLS 지표는 사이트가 봇 접근을 막아(403) 자동
수집이 안 되므로, 필요하면 `config.yaml` 의 `calendar.events` 에 직접 적으세요.

**학습 카드** — 용어 30개, 투자 심리 20개가 날짜에 따라 하루 한 장씩 돌아갑니다.
`briefing/data/glossary.py` 에서 내용을 편집·추가할 수 있습니다.

**내일의 기술** — 미래학자들이 말한 '지금 들어오고 있는 기술'을 책 한 챕터처럼 하루 한 편씩
읽습니다. 6부 25편: 계산하는 기계(AI·에이전트·반도체·전력·양자) / 움직이는 기계(휴머노이드·
자율주행·물류) / 몸과 생명(GLP-1·유전자 편집·노화·BCI·신약·합성생물학) / 에너지와 물질
(학습곡선·원자력·배터리·기후 적응) / 공간과 연결(우주·공간컴퓨팅·번역) / 돈과 사회(토큰화·
인구·양자내성 암호·기술과 거품). `briefing/data/futures.py`.

각 편은 **본문 → 미래학자들의 시선 → 다르게 보는 시각 → 어디에서 관찰되는가** 구조입니다.
낙관론만 싣지 않고 반론을 함께 두며, 종목 언급 없이 산업 수준까지만 서술합니다.

전체 25편을 한 페이지에서 훑어보려면:

```bash
python _preview_book.py
```

## AI 화면 미리보기 (무료)

API 키 없이 AI 요약이 켜진 화면이 어떻게 나오는지 보려면:

```bash
python _demo_ai.py
```

`report/demo-ai.html` 에 가짜 요약을 넣은 리포트가 생성됩니다. 실제 API 호출은 하지 않습니다.

## 구조

```
run.py                        진입점 · 수집 → 렌더 → 저장 순서를 조율
config.yaml                   종목·피드·AI 설정
briefing/
  config.py                   config.yaml + .env 로딩
  models.py                   Quote · NewsItem · Brief
  sources/market.py           시세 (yfinance → Finnhub → AlphaVantage 순 fallback)
  sources/news.py             RSS 수집 · 중복제거 · 노이즈 필터 · 소스 균형 · 종목별 뉴스
  sources/calendar.py         FOMC(연준 공식) · 고용보고서 · 실적 발표일
  summarize.py                Claude 한국어 번역 및 시장 총평
  render/html.py              HTML 렌더 (+ templates/report.html.j2)
  render/markdown.py          마크다운 렌더
  deliver/telegram.py         텔레그램 전송
  data/universe.py            상승/하락 스캔 유니버스
  data/glossary.py            주식 용어 30개 · 투자 심리 20개
  data/futures.py             내일의 기술 25편 (6부 구성, 반론 포함)
```

**데이터 fallback** — 시세는 yfinance 를 먼저 쓰고, 실패한 심볼만 Finnhub → Alpha Vantage 로
다시 시도합니다. 지수(`^GSPC`)·선물(`CL=F`)·환율(`KRW=X`)은 무료 API가 다루지 못하므로
fallback 대상에서 제외됩니다. 어떤 소스에서도 못 받은 항목은 리포트 하단 "수집 경고"에 표시됩니다.

**금리 표기** — 미국 10년물은 등락률(%)이 아니라 변동폭(bp)으로 표시합니다.
`config.yaml` 의 `change_mode: bp` 로 제어합니다.

---

## 주의

이 프로그램이 만드는 리포트는 공개 시세·뉴스 데이터를 자동 정리한 **참고 자료**입니다.
투자 자문이나 매매 권유가 아니며, AI 요약에는 오류가 있을 수 있습니다.
Claude 프롬프트는 매수/매도 추천과 목표가 제시를 하지 않도록 제약되어 있습니다.
데이터에는 지연·누락이 있을 수 있으니 중요한 판단 전에는 원문과 정식 시세를 확인하세요.
