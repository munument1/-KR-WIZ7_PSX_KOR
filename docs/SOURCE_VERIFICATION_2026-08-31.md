# Wizardry VII PSX 원본 검증 / 초기 추출 기록

Date: 2026-08-31
Branch: `korean-localization`

## 1. 입력 원본

사용자가 보유한 `Wizardry VII - Guardia no Houju (Japan).chd`를 기준으로 분석했다.

CHD 파일 해시:

- MD5: `87234265e920cf6a2e4d5426d39f6561`
- SHA-256: `a1d45439c8e38e9a9c106c7735d725f79a22596497ce0690442a8e33c1ecf4b0`

CHD v5 헤더:

- compressor 0: `cdlz`
- compressor 1: `cdzl`
- compressor 2: `cdfl`
- logical bytes: `337735872`
- hunk bytes: `19584`
- unit bytes: `2448`
- raw SHA-1: `0f713fbc5fa5c021fcf1d6c58a129ae5784007cc`
- combined SHA-1: `854e1666f0970f41f9b568c45de1ef93a43d4b42`

CD metadata:

```text
TRACK:1 TYPE:MODE2_RAW SUBTYPE:NONE FRAMES:137964 PREGAP:0 PGTYPE:MODE1 PGSUB:NONE POSTGAP:0
```

즉 1트랙 `MODE2_RAW` PS1 CD다.

## 2. CHD 압축 맵 확인

CHD v5 compressed map을 디코드한 결과:

- 전체 hunk: `17246`
- `cdlz`: `11439`
- `cdzl`: `5807`
- self/parent/무압축 hunk 없음
- 실제 압축 데이터의 마지막 위치가 CHD map 시작 위치와 정확히 일치함

파일 구조상 불일치나 절단 흔적을 확인하지 못했다.

## 3. BIN/CUE 복원 결과

CHD의 2448-byte CD frame에서 subcode를 제외한 2352-byte raw sector를 복원했다.
CDLZ/CDZL의 ECC 제거 최적화도 되돌려 원래 raw sector의 sync/ECC를 재생성했다.

복원 BIN:

- size: `324491328` bytes
- MD5: `188d3ee5a2a2242a719f290ea595e5ec`
- CRC32: `bab5dd73`

이는 원본 `WIZ7_PSX_ENG` README에 기록된 지원 원본과 **정확히 일치**한다.

```text
Expected by upstream English patch
MD5:   188d3ee5a2a2242a719f290ea595e5ec
CRC32: bab5dd73
```

따라서 이 CHD는 영어패치가 대상으로 삼은 일본판 원본과 동일한 디스크 내용을 보존하고 있다고 판단할 수 있다.

CUE 구조:

```cue
FILE "Wizardry VII - Guardia no Houju (Japan).bin" BINARY
  TRACK 01 MODE2/2352
    INDEX 01 00:00:00
```

## 4. ISO9660 파일 시스템 추출

복원된 MODE2/2352 트랙의 Form1 user-data 영역을 읽어 ISO9660 디렉터리 트리를 추출했다.
총 373개 파일/디렉터리 엔트리를 확인했다.

한국어화에 중요한 파일:

```text
PSX.EXE                         763904 bytes
CDS/D/ZENKAKU.TBL                 404 bytes
CDS/D/MISCJ.HDR                  1024 bytes
CDS/D/MSGJ.DBS                 211968 bytes
CDS/D/MSGJ.HDR                  11774 bytes
CDS/D/TALK.SCR                   8043 bytes
CDS/D/SCENARIJ.DBS             368320 bytes
CDS/D/SCENARIO.HDR                844 bytes
CDS/M/OPEN.TXT                   3715 bytes
CDS/M/OFONT.MMT                  7204 bytes
CDS/T/FONT.MMT                  50724 bytes
```

원본 파일 자체는 저작권 데이터이므로 Git 저장소에 커밋하지 않는다.

## 5. 폰트 관련 신규 확인

`ZENKAKU.TBL` 외에 실제 글리프 그래픽으로 보이는 두 파일을 확인했다.

### `CDS/T/FONT.MMT`

- file size: `50724`
- MMT header 뒤 pixel payload: `50688` bytes
- header 내 dimensions: `256 x 99` 16-bit words
- PS1 4bpp로 해석할 경우 실제 texture 폭은 `1024 x 99` pixels
- 일본어, 영문, 기호 글리프가 실제 아틀라스로 확인됨

### `CDS/M/OFONT.MMT`

- file size: `7204`
- pixel payload: `7168` bytes
- header 내 dimensions: `256 x 14` 16-bit words
- PS1 4bpp로 해석할 경우 `1024 x 14` pixels
- 별도 일본어 글리프 행으로 확인됨

따라서 일본어 문자가 PS1 BIOS 폰트에만 의존하는 구조는 아니며, 게임 데이터에 포함된 글리프 아틀라스를 수정하는 방향의 POC가 가능해 보인다.

특히 1024-pixel 폭은 8-pixel 폭 글리프 기준 128칸과 정확히 맞아떨어진다. `FONT.MMT` 높이 99는 14-pixel 높이 글리프 약 7행과 대응하므로, 우선 `8x14` 셀 구조를 가설로 두고 문자 코드와 실제 슬롯 대응을 추적한다.

## 6. 다음 조사 순서

1. `ZENKAKU.TBL`의 16-bit 값과 `FONT.MMT` 슬롯의 정확한 대응 관계 확인.
2. `PSX.EXE`의 `FUN_ASCIItoZENKAKU` (`0x8006CB80`) 후단 렌더링 경로 추적.
3. 사용 빈도가 낮은 일본어 글리프 슬롯 하나를 `한` 테스트 글리프로 교체.
4. 테스트 문자열/화면에서 해당 슬롯을 호출하여 DuckStation에서 표시 확인.
5. 성공하면 한국어 전용 문자표와 폰트 아틀라스 생성 방식 설계.

## 7. 배포/저작권 원칙

- CHD/BIN/CUE 및 원본 추출 파일은 GitHub에 포함하지 않는다.
- GitHub에는 분석 기록, 변환 도구, 자체 제작 한국어 폰트 데이터, 번역 데이터, 차이 패치만 저장한다.
- 최종 배포 시 지원 원본 BIN 체크섬은 위 MD5/CRC32를 기준으로 한다.
