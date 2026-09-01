# Wizardry VII PS1 한국어화

**Wizardry VII: Crusaders of the Dark Savant** 일본 PS1판
`Wizardry VII - Guardia no Houju (Japan)`을 한국어로 플레이하기 위한 ROM 해킹/현지화 프로젝트입니다.

이 저장소는 [gertius1/WIZ7_PSX_ENG](https://github.com/gertius1/WIZ7_PSX_ENG)를 기반으로 하며,
PS1판의 메시지 포맷, 폰트, 실행 파일 렌더러와 `SCENARIJ.DBS` 구조를 분석하여
한국어 네이티브 2바이트 문자 코드를 사용하는 방향으로 확장하고 있습니다.

> **현재 상태:** 개발/실기 테스트 단계  
> 2026-09-01 기준 실제 원본 CHD → 한국어 BIN/CUE/CHD 전체 재빌드와 바이너리 무결성 검증을 완료했습니다.  
> 다음 단계는 DuckStation 등 실제 실행 환경에서 플레이 테스트를 진행하는 것입니다.

---

## 현재 구현된 범위

- `MSGJ.DBS / MSGJ.HDR / MISCJ.HDR` 한국어 재인코딩
- PS1 Huffman 재인코딩 및 라운드트립 검증
- `FONT.MMT` 구조 분석 및 한국어 글리프 패킹
- Galmuri BDF에서 필요한 글리프 자동 추출
- PS1 네이티브 DBCS 코드 자동 할당
- `PSX.EXE` 한글 DBCS 렌더링/줄바꿈 런타임 패치
- `SCENARIJ.DBS` 아이템 571개 이름 이식
- `SCENARIJ.DBS` 몬스터 250개 × 4 이름 필드 이식
- MSG / FONT / SCENARIO 공용 문자 매핑
- CHD/BIN/CUE → 추출 → 한국어 파일 교체 → BIN/CUE/CHD 재빌드 파이프라인
- GitHub Actions 자동 검증
- 배포용 xdelta 생성/라운드트립 검증

## 공용 한글 코드표

현재 빌드는 메시지, 폰트, 아이템/몬스터 이름이 서로 다른 코드표를 쓰지 않습니다.

- 최종 네이티브 한글 매핑: **1,133자**
- `FONT.MMT` 사용 슬롯: **915..2047**
- 메시지 Huffman 라운드트립 실패: **0**
- PS1 네이티브 메시지 255바이트 초과: **0**

번역을 추가하여 새 한글 문자가 필요해지면 빌드 과정에서 공용 문자셋과 폰트가 함께 다시 생성됩니다.
사용자가 폰트 파일을 수동으로 분해하거나 글리프를 직접 넣을 필요는 없습니다.

---

## 지원 원본

현재 검증 기준은 일본 PS1판입니다.

### raw BIN

- MD5: `188d3ee5a2a2242a719f290ea595e5ec`
- CRC32: `bab5dd73`

### 기준 CHD

- MD5: `87234265e920cf6a2e4d5426d39f6561`
- SHA-256: `a1d45439c8e38e9a9c106c7735d725f79a22596497ce0690442a8e33c1ecf4b0`

CHD 컨테이너 해시는 변환 도구/압축 방식에 따라 달라질 수 있으므로,
최종 판정은 CHD에서 복원한 raw BIN의 MD5/CRC32를 기준으로 합니다.

이 저장소에는 원본 게임 BIN/CHD 또는 추출된 저작권 게임 파일을 포함하지 않습니다.

---

## 테스트용 xdelta 적용 방식

정식 릴리스에서는 전체 게임 이미지를 배포하지 않고 **xdelta 패치** 방식으로 제공할 예정입니다.

원본 raw BIN을 준비한 뒤 일반적인 xdelta3 사용법은 다음과 같습니다.

```bash
xdelta3 -d -s source.bin Wizardry7_PSX_KOR.xdelta Wizardry7_PSX_KOR.bin
```

2026-09-01 내부 검증 테스트 빌드의 한국어 BIN은 다음 결과를 냈습니다.

- MD5: `656bdf3fb384efbd5733da6d68c3fa99`
- SHA-256: `9867c85b48514c1ba61c3e47b19ad09b8a8179d79cf7807a2b9fb676d4649d6d`
- 크기: `324503088` bytes
- 섹터: `137969`
- 트랙: `MODE2/2352`, 1 track

상세 검증 기록:

- [`docs/PSX_FULL_DISC_BUILD_VERIFICATION_2026-09-01.md`](docs/PSX_FULL_DISC_BUILD_VERIFICATION_2026-09-01.md)

---

## 개발 빌드: CHD/BIN에서 직접 한국어판 만들기

전체 개발 빌드는 사용자 보유 원본 이미지에서 직접 한국어 BIN/CUE를 생성합니다.

핵심 스크립트:

```text
korean/tools/build_korean_psx_disc_full.py
```

필요 도구:

- Python 3
- `chdman` — CHD 입력/출력 사용 시
- `dumpsxiso`
- `mkpsxiso`

예:

```bash
python korean/tools/build_korean_psx_disc_full.py \
  "/path/to/Wizardry VII - Guardia no Houju (Japan).chd" \
  --output-bin build/Wizardry7_PSX_KOR.bin \
  --output-cue build/Wizardry7_PSX_KOR.cue \
  --output-chd build/Wizardry7_PSX_KOR.chd
```

빌더는 다음 작업을 자동으로 수행합니다.

```text
CHD/BIN/CUE
→ 원본 검증
→ 전체 PS1 파일시스템 추출
→ 번역 메시지 병합
→ 공용 DBCS 문자표 생성
→ MSGJ/MISCJ 재빌드
→ Galmuri 글리프 추출 및 FONT.MMT 패치
→ PSX.EXE 패치
→ SCENARIJ.DBS 아이템/몬스터 이름 패치
→ BIN/CUE 재빌드
→ 선택적으로 CHD 생성
```

Galmuri BDF를 사용자가 따로 준비하지 않은 경우 폰트 빌드 도구가 필요한 소스를 자동으로 처리합니다.

CI에서 사용하는 PS1 디스크 도구 체인은 다음 워크플로로 재현할 수 있습니다.

```text
.github/workflows/build-psx-toolchain.yml
```

---

## Scenario 번역

Gold판에서 작업된 Scenario 번역을 PS1판에 이식했습니다.

- 아이템: 571 ID
- 몬스터: 250 ID × 4 이름 필드
- DOS ↔ PS1 ID 대응 불일치: 0
- PS1 고정 필드 길이 초과: 0

재현용 도구:

```text
korean/tools/import_gold_scenario_translations.py
```

최종 데이터:

```text
korean/scenario/items.ko.tsv
korean/scenario/monsters.ko.tsv
korean/scenario/gold_import_overrides.tsv
```

검증 기록:

- [`korean/scenario/IMPORT_AUDIT.md`](korean/scenario/IMPORT_AUDIT.md)

---

## 실제 전체 디스크 검증 결과

2026-09-01에 실제 기준 CHD로 다음을 확인했습니다.

1. CHD에서 복원한 BIN이 기준 MD5/CRC32와 정확히 일치
2. 무수정 `dumpsxiso → mkpsxiso` 재빌드가 원본 BIN과 **바이트 단위 100% 동일**
3. 한국어판에서 의도한 6개 디스크 파일만 변경
4. 재추출한 나머지 게임 파일 내용은 모두 원본과 동일
5. 한국어 BIN → CHD → BIN 왕복 결과가 바이트 단위 동일
6. 원본 BIN → xdelta → 한국어 BIN 결과가 바이트 단위 동일

변경되는 디스크 파일:

```text
PSX.EXE
CDS/D/MISCJ.HDR
CDS/D/MSGJ.HDR
CDS/D/MSGJ.DBS
CDS/D/SCENARIJ.DBS
CDS/T/FONT.MMT
```

---

## 남은 테스트

바이너리 구조 검증은 완료했지만 실제 게임 플레이 테스트는 계속 필요합니다.

우선 확인할 항목:

- 게임 부팅 및 새 게임 시작
- 초반 던전/이벤트 진행
- NPC 대사 및 선택지
- 아이템/몬스터 이름
- 전투 메시지
- 줄바꿈과 텍스트 박스 넘침
- 메뉴/UI에서의 한글 표시
- 저장/불러오기
- 장시간 진행 시 안정성

문제가 확인되면 재현 위치와 화면을 GitHub Issue에 남겨 주세요.

---

## 저장소 구조

```text
korean/
  scenario/        아이템/몬스터 한국어 이름 및 검증 기록
  tools/           메시지/디스크/EXE 빌드 도구
Wiz7_Patching_Utilities/
  KoreanFontTools/ PS1 폰트/Scenario 패치 도구
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

원 프로젝트가 구축한 PS1판 구조 분석과 영문화 작업이 없었다면 이 한국어화 작업도 훨씬 어려웠을 것입니다.
