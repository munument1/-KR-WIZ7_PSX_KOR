# Gold Scenario → PS1 이식 검증 기록

검증일: 2026-09-01

## 원문/ID 대응

사용자가 보유한 DOS `SCENARIO.DBS`, 일본 PS1 `SCENARIJ.DBS`, Drive의 비교 TSV를 서로 대조했다.

- 아이템: 571개
  - 비교 TSV ↔ DOS 바이너리: 불일치 0
  - 비교 TSV ↔ PS1 바이너리: 불일치 0
  - Gold `Scenario` 원문과 DOS 원문의 비접두부 불일치: 0
  - Gold 고정 필드에서 원문 뒤가 잘린 접두부 일치: 56
- 몬스터: 250개 × 4 이름 필드 = 1000필드
  - 비교 TSV ↔ DOS/PS1 바이너리: 불일치 0
  - Gold `Scenario` 원문과 DOS 원문: 1000/1000 정확히 일치

따라서 현재 Gold Scenario 번역은 `record_index`를 PS1 ID로 그대로 사용할 수 있다. 아이템 56건의 원문 차이는 ID 오정렬이 아니라 Gold 쪽 짧은 이름 필드로 인한 정상적인 뒤쪽 잘림이다.

## PS1 길이 검증

- 아이템: 22바이트 필드, NUL 포함 → 최대 21바이트
- 몬스터: 16바이트 필드, NUL 포함 → 최대 15바이트
- 현재 네이티브 한글 코드: 한글 1글자 2바이트, ASCII 1바이트

수동 QA 오버라이드를 적용한 최종 결과:

- 아이템 길이 초과: 0
- 몬스터 길이 초과: 0
- 실제 최대 아이템 이름: ID 396 `우유 =/마그마나시아`, 19바이트
- 실제 최대 몬스터 이름: 15바이트

## 수동 QA 수정

`gold_import_overrides.tsv`에 재현 가능한 형태로 기록했다.

대표 수정:

- monster 201 `EARTH GOLEM` / `EARTH GOLEMS`: `헬라 에이스` → `대지 골렘`
- item 248 `WHITE BEAR`: `흰구슬` 계열 오역 → `고무/흰곰`
- item 564 `FRECKLED/WHITE BALL`: `흰콩` 오역 → `점박이/흰공`
- Gold 원문 필드에서 잘린 `+1`, `+2`, `(U)/(L)` 및 여러 고유명사 뒷부분 복원

## 공용 코드표/빌드 검증

GitHub Actions `Validate Korean MSGHDR` run 33503286715 성공.

- MSG 한글: 1110자
- Scenario를 포함한 추가 자산 한글: 486자
- Scenario 때문에 새로 필요해진 문자: 23자
- 최종 공용 네이티브 한글 매핑: 1133자
- FONT.MMT 슬롯 범위: 915..2047
- Huffman roundtrip failures: 0
- `MISCJ.HDR`: 1024바이트
- `MSGJ.HDR`: 11300바이트
- `MSGJ.DBS`: 222394바이트

CI가 생성한 동일 공용 매핑을 사용해 보유한 원본 `SCENARIJ.DBS`에 실제 패치를 적용했다.

- 패치된 이름 필드: 1568
- 허용된 이름 필드 밖 변경: 0바이트
- 출력 크기: 368320바이트 (원본과 동일)

`PSX.EXE`도 보유 원본의 기대 바이트를 확인한 뒤 DBCS 16글자 줄바꿈 패치가 정상 적용됨을 검증했다.

## 재현

Gold 시트의 `Scenario` 탭을 TSV/CSV로 내보내거나 전체 XLSX를 준비하고, 사용자가 보유한 DOS/PS1 원본에서 만든 비교 TSV를 입력한다.

```bash
python korean/tools/import_gold_scenario_translations.py \
  --gold-scenario /path/to/Wizardry7_Gold.xlsx \
  --items-source-work /path/to/Wizardry7_PSX_items_source_work.tsv \
  --monsters-source-work /path/to/Wizardry7_PSX_monsters_source_work.tsv \
  --overrides korean/scenario/gold_import_overrides.tsv \
  --out-items korean/scenario/items.ko.tsv \
  --out-monsters korean/scenario/monsters.ko.tsv
```

비교 TSV와 원본 게임 바이너리는 저작권 파일/파생 원문 자료이므로 저장소에 포함하지 않는다.
