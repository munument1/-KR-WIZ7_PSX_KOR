# Wizardry VII PS1 한국어화

**Wizardry VII: Crusaders of the Dark Savant** 일본 PS1판
`Wizardry VII - Guardia no Houju (Japan)`을 한국어로 플레이하기 위한 ROM 해킹/현지화 프로젝트입니다.

이 프로젝트의 실제 제작 베이스는 **Gertius의 PS1 영문화 패치 `WIZ7_PSX_ENG V1.0`**입니다.
DOS판이나 Wizardry Gold 실행 파일/UI 자산을 PS1판에 섞지 않습니다. Gold/DOS 데이터는 번역문 재활용과 대조 자료로만 사용합니다.

```text
검증된 일본 PS1판 BIN/CHD
→ Gertius WIZ7_PSX_ENG V1.0 적용
→ 검증된 PS1 영문판 파일시스템
→ 한국어 MSG/FONT/EXE/SCENARIO 오버레이
→ PS1 고정폭 UI 영문 안정화
→ 한국어 타이틀 부제
→ 최종 BIN/CUE/CHD 또는 일본판 기준 xdelta
```

> **현재 상태:** 개발/실기 테스트 단계  
> 2026-09-02 기준 영문 PS1 패치를 완전 베이스로 한 v7 전체 디스크 재빌드와 xdelta/CHD 라운드트립 검증을 완료했습니다.  
> 실제 플레이에서 남은 PS1 전용 UI/이벤트 문제를 계속 확인하고 있습니다.

---

## 현재 구현된 범위

- `MSGJ.DBS / MSGJ.HDR / MISCJ.HDR` 한국어 재인코딩
- PS1 Huffman 재인코딩 및 라운드트립 검증
- `FONT.MMT` 구조 분석 및 Galmuri11 한국어 글리프 패킹
- PS1 네이티브 DBCS 코드 자동 할당
- `PSX.EXE` 한글 DBCS 줄바꿈 런타임 패치
- `SCENARIJ.DBS` 아이템 571개 이름 이식
- `SCENARIJ.DBS` 몬스터 250개 × 4 이름 필드 이식
- MSG / FONT / SCENARIO 공용 문자 매핑
- Gertius PS1 영문화판의 `PCFILE.`, `SCENARIO.HDR`, `TALK.SCR`, 영상/오프닝 자산 보존
- 캐릭터 생성/정보창의 1바이트 고정폭 UI를 PS1 영문 문자열로 안정화
- 영문판 MSG 파일 크기/LBA 배치 보존
- `TITL.MMT`의 일본어 부제 `ガーディアの宝珠`를 `가디아의 보주`로 교체
- CHD/BIN/CUE 전체 재빌드 및 배포용 xdelta 생성
- GitHub Actions 자동 검증

## 영문 PS1 베이스

Gertius V1.0이 일본판 파일시스템에서 수정하는 파일은 정확히 12개입니다.

```text
CDS/D/MISCJ.HDR
CDS/D/MSGJ.DBS
CDS/D/MSGJ.HDR
CDS/D/PCFILE.
CDS/D/SCENARIJ.DBS
CDS/D/SCENARIO.HDR
CDS/D/TALK.SCR
CDS/M/BOOK.STR
CDS/M/OPEN.STR
CDS/M/OPEN.TXT
CDS/S1/AD.XA
PSX.EXE
```

v7은 이 영문판을 먼저 만든 뒤 한국어 파일만 덮습니다. 따라서 PS1 전용 메뉴/영상/기본 캐릭터/스크립트는 영문판 수정본을 그대로 유지합니다.

상세 감사 기록:

- [`docs/PSX_ENGLISH_BASE_AUDIT_2026-09-02.md`](docs/PSX_ENGLISH_BASE_AUDIT_2026-09-02.md)

---

## 공용 한글 코드표 / 폰트

메시지, 폰트, 아이템/몬스터 이름은 하나의 공용 문자 매핑을 사용합니다.

- 네이티브 한글 매핑: **1,133자**
- 사용 렌더러 글리프 범위: **915..2047**
- 실제 `FONT.MMT` 물리 슬롯: **렌더러 글리프 - 4**
- 물리 비트플레인 순서: **0,1,2,3**
- Galmuri11 배치: **x=1, y=0**
- 메시지 Huffman 라운드트립 실패: **0**
- PS1 네이티브 메시지 255바이트 초과: **0**

초기 테스트에서 확인된 주요 폰트 오류도 빌드 규칙에 반영했습니다.

- 렌더러 글리프를 물리 슬롯에 그대로 쓰던 4슬롯 오프셋 오류 수정
- 잘못 추정했던 0/2 비트플레인 교환 폐기
- Galmuri11 오른쪽 끝이 잘려 모든 `ㅏ`가 `ㅣ`처럼 보이던 문제 수정

자세한 구조:

- [`Wiz7_Patching_Utilities/KoreanFontTools/RENDERER_CODEPAGE.md`](Wiz7_Patching_Utilities/KoreanFontTools/RENDERER_CODEPAGE.md)

---

## 지원 원본

현재 검증 기준은 일본 PS1판입니다.

### raw BIN

- MD5: `188d3ee5a2a2242a719f290ea595e5ec`
- CRC32: `bab5dd73`

### 기준 CHD

- MD5: `87234265e920cf6a2e4d5426d39f6561`
- SHA-256: `a1d45439c8e38e9a9c106c7735d725f79a22596497ce0690442a8e33c1ecf4b0`

CHD 컨테이너 해시는 압축 방식에 따라 달라질 수 있으므로 최종 판정은 CHD에서 복원한 raw BIN의 MD5/CRC32로 합니다.

### Gertius PS1 영문패치 V1.0 적용 결과

- MD5: `7fb464147ab7144facae337226c91aa5`
- SHA-256: `6d61aaccf5a21853077f96b66e5fea4a2859611d89b5a93358e79d2f504c1683`

이 저장소에는 원본 게임 BIN/CHD 또는 추출된 게임 파일을 포함하지 않습니다.

---

## v7 테스트 빌드

최종 v7 raw BIN:

- MD5: `381cf7ff7509f35b5fbc423791ed689d`
- SHA-256: `7dc0fb63ccd4565542e07c134881d54c4faa84c7145b73c67d6d5708f5d67df1`

v7 xdelta:

- SHA-256: `b421320fa47264b185be5e8fb95417d639e656cd0a52750f4cbeb61edd0f896a`

검증 완료 항목:

1. 일본판 원본 BIN → v7 xdelta → v7 BIN 바이트 단위 동일
2. v7 BIN → CHD → BIN 바이트 단위 동일
3. `chdman verify` raw/overall SHA1 성공
4. PS1 영문패치 파일시스템 대비 정확히 7개 의도한 파일만 변경
5. 나머지 Gertius 영문 PS1 자산은 바이트 단위 동일

영문 PS1판 대비 v7 변경 파일:

```text
CDS/D/MISCJ.HDR
CDS/D/MSGJ.DBS
CDS/D/MSGJ.HDR
CDS/D/SCENARIJ.DBS
CDS/T/FONT.MMT
CDS/T/TITL.MMT
PSX.EXE
```

---

## 캐릭터 생성/정보창 고정폭 UI

PS1판의 일부 캐릭터 정보 UI는 2바이트 DBCS 문자열을 안전하게 처리하지 못합니다. 이 경로에 한글을 직접 넣으면 단어 누락이나 화면 하단으로 깨진 글자가 흘러나오는 현상이 발생했습니다.

현재는 안정성을 위해 아래 범위를 **Gertius PS1 영문판 ASCII 문자열**로 되돌립니다.

- 100..110: 종족
- 120..134: 직업
- 140..141: 성별
- 160..162: 패드/버튼 안내
- 200..219: LVL/RNK/EXP/능력치/상태 라벨
- 800..937: 직업 등급명

이 부분은 추후 해당 렌더링 루틴을 DBCS 안전하게 패치한 뒤 한국어화할 수 있습니다.

또한 한국어 MSG 파일은 영문판과 동일한 파일 크기로 안전 패딩해 후속 파일 LBA를 유지합니다. 이 때문에 `PCFILE.`을 포함한 PS1 영문판 데이터 배치가 이동하지 않습니다.

---

## 개발 빌드

현재 권장 생산 빌더는 다음 파일입니다.

```text
korean/tools/build_korean_psx_disc_english_base.py
```

필요 도구:

- Python 3
- `xdelta3`
- `dumpsxiso`
- `mkpsxiso`
- `chdman` — CHD 입력/출력 사용 시
- Gertius `WIZ7_PSX_ENG V1.0`의 `Wiz7_patch.xdelta`

예:

```bash
python korean/tools/build_korean_psx_disc_english_base.py \
  "/path/to/Wizardry VII - Guardia no Houju (Japan).chd" \
  --upstream-english-xdelta "/path/to/Wiz7_patch.xdelta" \
  --output-bin build/Wizardry7_PSX_KOR.bin \
  --output-cue build/Wizardry7_PSX_KOR.cue \
  --output-chd build/Wizardry7_PSX_KOR.chd \
  --output-xdelta build/Wizardry7_PSX_KOR.xdelta
```

빌드 순서:

```text
일본 PS1 원본 검증
→ Gertius PS1 영문 xdelta 적용
→ 영문 BIN 해시 검증
→ 영문 PS1 파일시스템 추출
→ 한국어 메시지 + 공용 코드표 생성
→ 한국어 FONT.MMT 생성
→ 영문 PSX.EXE에 한국어 런타임 패치 병합
→ 영문 SCENARIJ.DBS에 한국어 아이템/몬스터 이름 병합
→ 고정폭 UI 영문 안정화
→ MSG 크기/LBA를 영문판과 동일하게 유지
→ TITL.MMT 부제를 "가디아의 보주"로 교체
→ BIN/CUE/CHD 재빌드
→ 일본판 원본 기준 최종 xdelta 생성 및 라운드트립 검증
```

CI 도구 체인:

```text
.github/workflows/build-psx-toolchain.yml
.github/workflows/build-windows-patcher-tools.yml
```

---

## Scenario 번역

Gold판에서 작업된 Scenario **번역문**을 PS1 구조에 맞춰 이식했습니다. Gold판 바이너리/UI를 사용한 것이 아닙니다.

- 아이템: 571 ID
- 몬스터: 250 ID × 4 이름 필드
- DOS ↔ PS1 ID 대응 불일치: 0
- PS1 고정 필드 길이 초과: 0

데이터:

```text
korean/scenario/items.ko.tsv
korean/scenario/monsters.ko.tsv
korean/scenario/gold_import_overrides.tsv
```

검증 기록:

- [`korean/scenario/IMPORT_AUDIT.md`](korean/scenario/IMPORT_AUDIT.md)

---

## 남은 실제 플레이 QA

바이너리/파일시스템 검증은 통과했지만 에뮬레이터 실기 테스트는 계속 필요합니다. 특히 다음 항목을 우선 확인합니다.

- 기본 캐릭터 이름이 영문 PS1판처럼 표시되는지
- 캐릭터 정보창 하단의 깨진 글자 스트림이 사라졌는지
- 고정폭 UI의 종족/직업/능력치 라벨이 영어로 안정적으로 나오는지
- 타이틀 화면 부제가 `가디아의 보주`로 표시되는지
- 초반 이벤트/NPC/초상화가 영문 PS1판과 동일하게 진행되는지
- 한국어 본문/아이템/몬스터/전투 메시지
- 저장/불러오기 및 장시간 진행 안정성

문제가 확인되면 재현 위치와 스크린샷을 GitHub Issue에 남겨 주세요.

---

## 저장소 구조

```text
korean/
  scenario/        아이템/몬스터 한국어 이름 및 검증 기록
  tools/           메시지/디스크/EXE/영문베이스 빌드 도구
Wiz7_Patching_Utilities/
  KoreanFontTools/ PS1 폰트/Scenario 패치 도구
release/windows/   CHD/BIN 자동 패처 스크립트
.github/workflows/ 자동 검증 및 PS1 도구 체인
```

---

## 원 프로젝트 / 감사

이 프로젝트는 Gertius의 PS1 영문화 프로젝트와 기존 역공학 자산을 기반으로 합니다.

- Upstream: <https://github.com/gertius1/WIZ7_PSX_ENG>
- Cosmic Forge 및 기존 Wizardry 분석 도구 제작자들
- `mkpsxiso / dumpsxiso` 프로젝트 기여자들
- MAME `chdman` 개발자들
- Galmuri 프로젝트

Gertius가 구축한 PS1판 구조 분석과 영문화 작업이 이 한국어판의 실제 기반입니다.
