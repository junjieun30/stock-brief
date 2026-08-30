# 클라우드로 옮기기 — PC를 꺼도 매일 아침 브리핑 받기

지금은 이 PC가 켜져 있어야만 브리핑이 만들어집니다. GitHub의 무료 서버가 대신 돌리게 하면
컴퓨터를 꺼두거나 여행 중이어도 매일 아침 리포트가 도착합니다.

**결과물 두 가지**
- 텔레그램으로 아침에 푸시 알림
- 어느 기기에서든 볼 수 있는 웹 주소 (`https://junjieun30.github.io/stock-brief/`)

**비용** — 전부 무료입니다. 공개 저장소의 GitHub Actions는 실행 시간 제한이 없습니다.
유일한 유료 항목은 Claude API 사용료인데, 하루 1회 요약이면 월 1~2달러 수준입니다.

전체 30~40분 걸립니다. 순서대로 따라오세요.

---

## 1단계 — GitHub 계정 ✅ 완료

계정 `junjieun30` 확인했습니다. 이 문서의 모든 주소는 이 아이디로 맞춰져 있습니다.

- 저장소: https://github.com/junjieun30/stock-brief
- 웹페이지: https://junjieun30.github.io/stock-brief/

## 2단계 — 텔레그램 봇 만들기 (3분)

1. 텔레그램 앱에서 검색창에 **@BotFather** 입력 → 파란 체크가 붙은 계정 선택
2. `/newbot` 전송
3. 봇 이름 입력 (아무거나, 예: `내 주식 브리핑`)
4. 봇 아이디 입력 — **반드시 `bot` 으로 끝나야 합니다** (예: `junji_stock_brief_bot`)
5. BotFather가 이런 토큰을 줍니다 → **복사해서 메모장에 붙여두세요**

   ```
   8123456789:AAH7x_QwErTyUiOpAsDfGhJkLzXcVbNm123
   ```

6. **방금 만든 봇과 대화를 시작합니다.** BotFather가 준 `t.me/...` 링크를 눌러 봇에 들어간 뒤
   `/start` 를 보내세요. **이 단계를 건너뛰면 봇이 나에게 메시지를 보낼 수 없습니다.**
7. 브라우저 주소창에 아래를 입력 (`<토큰>` 자리에 5번 토큰을 그대로 붙여넣기)

   ```
   https://api.telegram.org/bot<토큰>/getUpdates
   ```

8. 화면에 나오는 `"chat":{"id":123456789` 에서 **숫자 부분이 CHAT_ID** 입니다. 이것도 메모해 두세요.

> `"result":[]` 처럼 비어 있으면 6번(봇에게 `/start` 보내기)을 안 한 것입니다.

## 3단계 — Claude API 키 발급 (5분)

1. https://console.anthropic.com 접속 → GitHub 계정이나 이메일로 가입
2. 왼쪽 메뉴 **API Keys** → **Create Key**
3. `sk-ant-...` 로 시작하는 키를 **복사해서 메모** (창을 닫으면 다시 볼 수 없습니다)
4. **Billing** 메뉴에서 결제수단 등록 후 최소 금액($5) 충전
   - 하루 1회 요약 기준 월 1~2달러 정도입니다.

> 이 키를 건너뛰어도 프로그램은 돌아갑니다. 다만 뉴스가 영문 그대로 나오고 시장 총평이 빠집니다.

## 4단계 — 코드 올리기

**4-1. 저장소 생성 ✅ 완료** — https://github.com/junjieun30/stock-brief (현재 비어 있음)

**4-2. 코드 올리기**

아래를 실행합니다. remote 는 이미 걸어뒀습니다.

```powershell
cd D:\claud\stock-brief; git push -u origin main
```

> **명령어는 PowerShell 문법입니다.** 이 PC의 터미널은 Windows PowerShell 5.1 이라
> 리눅스식 `&&` 를 쓰면 `'&&' 토큰은 이 버전에서 올바른 문 구분 기호가 아닙니다` 오류가 납니다.
> 명령을 이어 붙일 때는 세미콜론 `;` 을 씁니다.

실행하면 **GitHub 로그인 창**이 뜹니다 — "Sign in with your browser" 를 눌러 로그인한 뒤
**Authorize** 하세요. 창이 다른 창 뒤에 숨을 수 있으니 작업표시줄도 확인하세요.
(창이 안 뜨고 비밀번호를 물으면, 비밀번호 대신
[Personal Access Token](https://github.com/settings/tokens) 을 만들어 붙여넣어야 합니다.)

성공하면 `Writing objects: 100%` 와 `branch 'main' set up to track 'origin/main'` 이 보입니다.

## 5단계 — 비밀 키 등록 (5분)

**절대 키를 코드 파일에 직접 적지 마세요.** GitHub의 금고에 넣습니다.

1. 저장소 페이지 → 상단 **Settings** 탭
2. 왼쪽 메뉴 **Secrets and variables** → **Actions**
3. **New repository secret** 을 눌러 아래를 하나씩 추가합니다

   | Name (그대로 입력) | Secret (내가 메모해둔 값) |
   |---|---|
   | `ANTHROPIC_API_KEY` | `sk-ant-...` |
   | `TELEGRAM_BOT_TOKEN` | `8123456789:AAH7x...` |
   | `TELEGRAM_CHAT_ID` | `123456789` |

   선택 사항 (시세 조회 실패 시 대비용, 없어도 됩니다):

   | Name | 발급처 |
   |---|---|
   | `FINNHUB_API_KEY` | https://finnhub.io/register |
   | `ALPHAVANTAGE_API_KEY` | https://www.alphavantage.co/support/#api-key |

## 6단계 — 웹페이지 켜기 (2분)

1. 저장소 → **Settings** → 왼쪽 메뉴 **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / 폴더: **/docs** 선택 → **Save**
4. 1~2분 뒤 페이지 상단에 주소가 뜹니다

   ```
   https://junjieun30.github.io/stock-brief/
   ```

이 주소를 휴대폰 홈 화면에 추가하거나, 크롬 시작페이지로 지정하세요.

## 7단계 — 지금 바로 테스트 (2분)

스케줄을 기다리지 말고 바로 돌려봅니다.

1. 저장소 → 상단 **Actions** 탭
2. 왼쪽에서 **데일리 브리핑** 클릭
3. 오른쪽 **Run workflow** 버튼 → 초록색 **Run workflow** 다시 클릭
4. 1~2분 뒤 실행 항목을 클릭하면 진행 상황이 보입니다

**확인할 것**
- 텔레그램에 브리핑 메시지가 도착했는지
- 웹 주소에 접속했을 때 오늘 리포트가 뜨는지
- 뉴스 제목이 한국어인지 (영문이면 `ANTHROPIC_API_KEY` 등록을 확인하세요)

---

## 자동 실행 시각

**한국시간 화~토 아침 7시** 에 자동으로 돕니다. 미국장 월~금 마감분을 다음날 아침에 받는 구조입니다.

GitHub의 스케줄러는 서버가 붐빌 때 **10~30분 늦게** 뜰 수 있습니다. 정확한 정시 도착이
보장되지는 않습니다.

**시각을 바꾸려면** `.github/workflows/daily-brief.yml` 의 이 줄을 고칩니다.

```yaml
- cron: "0 22 * * 1-5"
```

시각은 **UTC 기준**이라 한국시간에서 9시간을 빼야 합니다.

| 원하는 한국시간 | cron 값 |
|---|---|
| 화~토 오전 6시 | `0 21 * * 1-5` |
| 화~토 오전 7시 | `0 22 * * 1-5` (현재) |
| 화~토 오전 8시 | `0 23 * * 1-5` |
| 매일 오전 7시 | `0 22 * * *` |

고친 뒤 `git add .; git commit -m "시각 변경"; git push` 하면 적용됩니다.

## 설정 바꾸기

관심 종목을 추가하려면 `config.yaml` 을 고치고 push 하면 됩니다.
GitHub 웹에서 파일을 직접 편집해도 됩니다 — 저장소에서 `config.yaml` 클릭 → 연필 아이콘 →
수정 후 **Commit changes**.

```yaml
watchlist:
  - { symbol: "AAPL", name: "애플" }
  - { symbol: "SMCI", name: "슈퍼마이크로" }   # 이렇게 한 줄 추가
```

## 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| 텔레그램이 안 옴 | 2단계 6번(봇에게 `/start`)을 했는지, `TELEGRAM_CHAT_ID` 가 숫자만인지 |
| 뉴스가 영문임 | `ANTHROPIC_API_KEY` Secret 이름의 오타, Anthropic 콘솔의 잔액 |
| 웹페이지 404 | 6단계에서 폴더를 `/docs` 로 골랐는지, 1회 이상 실행이 성공했는지 |
| 실행이 빨간 X | Actions 탭 → 실패한 실행 클릭 → 빨간 단계를 펼쳐 로그 확인 |
| 아침에 안 돌았음 | Actions 탭에 실행 기록이 있는지. 없으면 저장소가 60일 이상 방치돼 스케줄이 꺼진 것 — 안내 메일의 링크로 다시 켜면 됩니다 |

## 로컬 PC에서도 계속 쓰기

클라우드로 옮겨도 로컬 실행은 그대로 됩니다. 원할 때 즉시 최신 브리핑을 보고 싶으면:

```bash
cd D:\claud\stock-brief; python run.py --open
```

로컬은 `report/` 에, 클라우드는 `docs/` 에 저장되어 서로 간섭하지 않습니다.
