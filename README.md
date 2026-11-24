# AssetRadar

Unity Asset Store, Fab, itch.io의 게임 에셋 할인을 원화로 비교하고, 가격 기록과 역대 최저가를 추적하는 서비스예요.

- **수집**: GitHub Actions가 6시간마다 각 마켓의 세일 페이지를 읽어요.
- **저장**: 가격 기록은 `docs/data/*.json` 파일에 쌓여요. 별도 데이터베이스가 필요 없어요.
- **사이트**: GitHub Pages가 `docs/` 폴더를 그대로 웹사이트로 보여줘요.
- **알림**: 역대 최저가, 새 무료 에셋, 세일 재시작을 RSS(`docs/feed.xml`)와 디스코드로 보내요.

## 폴더 구조

```
collector/            수집기 (Python)
  config.json         마켓별 수집 주소·개수 설정 ← 주소가 바뀌면 여기만 고치면 돼요
  sources/            unity.py · fab.py · itch.py
  store.py            가격 기록 합치기, 최저가 계산, 비정상 수집 차단
  alerts.py           RSS·디스코드 알림
  fx.py               원/달러 환율(유럽중앙은행 기준, 키 불필요)
docs/                 웹사이트 (GitHub Pages)
  index.html
  data/assets.json    전체 상품·가격 기록
  data/meta.json      갱신 시각·환율·마켓별 수집 상태
  data/extras.json    상시 무료 에셋(직접 관리)
  feed.xml            알림 RSS
tests/                테스트 (pytest)
.github/workflows/    collect.yml(예약 수집) · test.yml(테스트)
```

## 처음 설정하기

1. GitHub에서 **새 저장소**를 만들어요. 이름은 `assetradar` 추천, 공개(Public)로 만들면 Actions와 Pages를 무료로 쓸 수 있어요.
2. 이 폴더의 파일을 전부 올려요. 아래 둘 중 편한 방법으로 하면 돼요.
   - 웹: 저장소 첫 화면의 **uploading an existing file**에서 파일·폴더를 끌어다 놓기
   - 터미널: `git remote add origin https://github.com/내아이디/assetradar.git && git push -u origin main`
3. **Settings → Actions → General → Workflow permissions**에서 **Read and write permissions**를 선택해요. 수집 결과를 저장소에 저장하려면 필요해요.
4. **Settings → Pages**에서 Source를 **Deploy from a branch**, Branch를 **main / docs**로 정해요. 몇 분 뒤 `https://내아이디.github.io/assetradar/`에서 사이트가 열려요.
5. **Settings → Secrets and variables → Actions**에서 아래를 넣어요(선택).
   - Variables `ASSETRADAR_SITE`: 위 사이트 주소
   - Variables `ASSETRADAR_UA`: `Mozilla/5.0 (compatible; AssetRadarBot/0.1; +https://github.com/내아이디/assetradar)`
   - Secrets `DISCORD_WEBHOOK_URL`: 디스코드 채널 설정 → 연동 → 웹후크에서 만든 주소(알림을 받을 때만)
6. **Actions → 가격 수집 → Run workflow**로 첫 수집을 직접 돌려봐요.

## 첫 수집 결과 확인하기

수집기는 각 스토어 화면을 실제 브라우저로 열어서 읽어요. 스토어 화면 구조는 실제로 돌려봐야 확인할 수 있어서, **첫 실행에서 일부 마켓이 실패할 수 있어요.** 실패해도 사이트는 이전 데이터를 그대로 보여주게 되어 있어요.

- 실행 기록의 로그에 `[Unity] page 1: 카드 96개, 새 상품 96개`처럼 마켓별로 몇 개를 읽었는지 나와요.
- 수집이 실패하거나 너무 적으면 로그에 경고가 뜨고, 실행 결과 아래 **debug-snapshots**에 그 순간의 페이지 HTML과 스크린샷이 저장돼요.
- 그 파일을 받아서 Claude에게 보여주면 해당 마켓 수집기를 고칠 수 있어요.

## 안전장치

- 각 스토어의 `robots.txt`를 먼저 확인하고, 막힌 주소는 열지 않아요.
- 페이지 사이에 몇 초씩 쉬고, 마켓당 몇 페이지만 읽어요(6시간에 한 번).
- 수집 결과가 0개이거나 직전보다 70% 넘게 줄면 실패로 보고, 기존 데이터를 지우지 않아요.
- "역대 최저가"는 공개 가격 추적 기록이 있는 에셋이거나, AssetRadar가 60일 넘게 추적한 에셋에만 표시해요. 그 전에는 "기록 없음"으로 나와요.

**공개 운영 전에 꼭 확인할 것**: 각 마켓의 이용약관에서 자동 수집을 어떻게 다루는지 확인하세요. 제휴 프로그램(Unity 제휴 등)에 가입하면 제공되는 링크·데이터를 우선 쓰는 게 안전해요. 히어로 일러스트(`docs/hero.jpg`)는 시안에서 가져온 이미지라 사용 권한을 확인해 주세요.

## 로컬에서 실행하기

```bash
pip install -r requirements.txt
python -m playwright install chromium
python -m pytest -q                       # 테스트
python -m collector.run --dry-run         # 파일을 바꾸지 않고 수집만 해보기
python -m collector.run --only itch       # 특정 마켓만
cd docs && python -m http.server 8000     # 사이트 미리보기 http://localhost:8000
```

## 다음 단계

- 개인별 관심 에셋 이메일 알림: 로그인과 데이터베이스(예: Supabase)가 필요해요.
- 마켓 추가: 로블록스 Creator Store, Humble Bundle 번들, Synty·Kenney 직판.
- 제휴 링크: `docs/index.html`의 `AFF={unity:""}`에 제휴 ID를 넣으면 유니티 링크에 자동으로 붙어요.
