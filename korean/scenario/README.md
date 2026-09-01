# PS1 `SCENARIJ.DBS` 이름 한국어화

이 폴더는 PS1판 `SCENARIJ.DBS` 안의 고정 길이 아이템/몬스터 이름 번역만 관리한다.
원본 바이너리는 저장소에 넣지 않는다.

## 검증된 레이아웃

지원하는 일본판 `SCENARIJ.DBS` 크기: **368,320 bytes**

- 아이템: 571개
  - 시작 `0x380`
  - 레코드 간격 `0x48`
  - 이름 필드 `+0x00`, 22바이트(NUL 포함)
  - 따라서 실제 인코딩 가능한 최대 길이 21바이트
- 몬스터: 250개
  - 시작 `0x37038`
  - 레코드 간격 `0xE8`
  - 이름 블록 `+0x08`
  - 16바이트 필드 4개(NUL 포함)
  - 각 필드 실제 인코딩 가능한 최대 길이 15바이트

한글은 현재 PS1 네이티브 DBCS에서 글자당 2바이트이므로 순수 한글 기준으로 아이템은 최대 10글자, 몬스터 각 이름은 최대 7글자다. ASCII가 섞이면 실제 바이트 길이로 다시 계산한다.

## 번역 파일

### `items.ko.tsv`

```text
id	ko_name
0	고장난 물건
1	단검
```

빈 `ko_name`은 원본 일본어 이름을 그대로 둔다.

### `monsters.ko.tsv`

```text
id	ko_specific_singular	ko_specific_plural	ko_generic_singular	ko_generic_plural
0	...	...	...	...
```

빈 필드는 해당 원본 일본어 필드를 그대로 둔다.

## 원문 비교용 템플릿 만들기

사용자가 보유한 DOS `SCENARIO.DBS`와 일본 PS1 `SCENARIJ.DBS`가 있으면 다음 명령으로 영문/일문 비교용 TSV를 만들 수 있다.

```bash
python Wiz7_Patching_Utilities/KoreanFontTools/scenario_name_patcher.py dump \
  --psx /path/to/SCENARIJ.DBS \
  --dos /path/to/SCENARIO.DBS \
  --out-dir build/scenario-name-templates
```

이 명령이 만드는 템플릿은 작업 참고용이다. 원본 게임에서 추출한 전체 문자열 목록을 그대로 저장소에 추가하지 않는다.

## 코드표 공유 규칙

SCENARIJ 번역에서 새로운 한글이 하나라도 추가되면 MSG 전용 코드표를 그대로 쓰면 안 된다.
`MSGJ`, `FONT.MMT`, `SCENARIJ.DBS`가 **모두 같은 전체 한글 인벤토리**로 코드표를 다시 생성해야 한다.

`korean/tools/build_native_korean_msghdr_shared.py`는 `--extra-charset`로 이 폴더의 TSV를 받아 MSG와 SCENARIO의 한글을 합친 뒤 공용 코드표를 만든다. 폰트 빌드도 같은 TSV를 입력으로 받아야 한다.

`scenario_name_patcher.py`는 코드표를 스스로 만들지 않고 이렇게 생성된 공용 TSV만 소비한다. 이 구조로 문자→2바이트 코드→FONT.MMT 슬롯의 불일치를 막는다.
