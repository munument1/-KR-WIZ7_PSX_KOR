# Korean MSGHDR build tools

## `build_msghdr_overlay.py`

PS1 영어 `MSGHDR_indexText.txt`를 기준으로 `korean/MSGHDR_indexText.ko.txt`와 `korean/segments/*.ko.txt`를 검사하고 병합한다.

### 검증만 실행

저장소 루트에서:

```bash
python korean/tools/build_msghdr_overlay.py --validate-only
```

검증 결과는 기본적으로 다음 파일에 기록된다.

```text
korean/build/MSGHDR_validation_report.txt
```

### 병합 파일 생성

```bash
python korean/tools/build_msghdr_overlay.py
```

검증 오류가 없으면 다음 파일을 만든다.

```text
korean/build/MSGHDR_indexText.ko.merged.txt
```

병합 규칙:

- 레코드 순서와 `*` 플래그는 PS1 영어 원본을 따른다.
- 한국어 오버레이가 있는 ID만 한국어 텍스트로 교체한다.
- 오버레이가 없는 ID는 PS1 영어 원문을 유지한다.
- 번역 원고의 `<0xNN>` 표기는 병합 파일에서 실제 C0 제어 문자로 복원한다.
- 여러 한국어 파일에 같은 ID가 중복되면 오류로 중단한다.
- PS1 원본에 없는 ID를 한국어 파일이 정의하면 오류로 중단한다.

### 차단 오류

다음은 게임 진행이나 메뉴 선택을 깨뜨릴 가능성이 있으므로 병합을 중단한다.

- 제어 바이트 순서가 PS1 원본과 다름
- `=F...`, `=S...`, `=P...`, `=L...`, `=I...`, `=G...`, `=E...`, `=951,` 같은 이벤트/참조 토큰 순서가 다름
- 중복 메시지 ID
- PS1 원본에 존재하지 않는 오버레이 ID

### 경고

`@`, `!`, `#!`, `^`, `$`, `%`, `#` 같은 표시/치환 기호가 원본과 달라지면 경고를 낸다. 기본 실행에서는 경고만으로 실패하지 않는다.

경고까지 실패로 처리하려면:

```bash
python korean/tools/build_msghdr_overlay.py --validate-only --strict-warnings
```

초기 번역 데이터에는 Gold판에서 가져온 표시 기호 차이가 남아 있을 수 있으므로, 먼저 일반 검증의 차단 오류를 모두 해결한 뒤 `--strict-warnings`를 사용하는 것을 권장한다.

## `build_korean_psx_disc.py`

사용자가 보유한 일본판 PS1 디스크 이미지에서 한국어 테스트/배포용 BIN/CUE를 재빌드하는 통합 도구다. 원본 게임 파일은 저장소에 포함하거나 업로드하지 않는다.

자동 처리 순서:

1. CHD 입력이면 `chdman extractcd`로 BIN/CUE 복원
2. 복원된 BIN의 MD5/CRC32 검증
3. `dumpsxiso`로 전체 디스크와 재빌드 XML 추출
4. 현재 한국어 번역 병합 및 네이티브 Huffman `MISCJ.HDR`, `MSGJ.HDR`, `MSGJ.DBS` 생성
5. 원본 `FONT.MMT`에 현재 한글 문자 세트를 삽입
6. 폰트와 MSG의 문자→2바이트 코드/슬롯 매핑이 완전히 같은지 재검증
7. `PSX.EXE`에 DBCS 대응 16글자 줄바꿈 루틴 적용
8. 추출 트리의 5개 파일을 교체
9. `mkpsxiso`로 새 BIN/CUE 생성
10. 요청 시 `chdman createcd`로 CHD도 생성

기본 지원 원본 raw BIN:

```text
MD5   188d3ee5a2a2242a719f290ea595e5ec
CRC32 bab5dd73
```

다른 덤프는 기본적으로 거부한다. 연구 목적으로만 `--allow-unverified-source`를 사용할 수 있다.

필요 도구:

- Python 3.11 이상 권장
- `dumpsxiso`와 `mkpsxiso` (`mkpsxiso` 패키지)
- CHD 입력 또는 CHD 출력 시 `chdman`
- Galmuri11 BDF. `--bdf`로 로컬 파일을 지정하지 않으면 기존 폰트 도구가 공식 Galmuri11 BDF 다운로드를 시도한다.

도구들이 PATH에 등록되어 있다면 CHD에서 BIN/CUE를 만드는 예:

```bash
python korean/tools/build_korean_psx_disc.py "Wizardry VII - Guardia no Houju (Japan).chd" \
  --output-bin build/Wizardry7_PSX_KOR.bin \
  --output-chd build/Wizardry7_PSX_KOR.chd
```

Windows에서 실행 파일들을 한 폴더에 두었다면:

```powershell
python korean/tools/build_korean_psx_disc.py "D:\Games\Wizardry VII - Guardia no Houju (Japan).chd" `
  --tool-dir "D:\Tools\psx" `
  --output-bin "build\Wizardry7_PSX_KOR.bin" `
  --output-chd "build\Wizardry7_PSX_KOR.chd"
```

BIN 또는 CUE를 직접 입력할 수도 있다.

```bash
python korean/tools/build_korean_psx_disc.py original.cue
python korean/tools/build_korean_psx_disc.py original.bin
```

작업 폴더는 기본적으로 `build/psx-korean-disc-work`에 남겨 디버깅에 사용할 수 있다. 같은 작업 폴더를 의도적으로 재사용하려면 `--reuse-work-dir`를 지정한다.

빌드 완료 후 `build/Wizardry7_PSX_KOR_BUILD_REPORT.txt`에 원본 검증값, 교체된 핵심 파일의 전후 SHA-256, 최종 BIN 해시가 기록된다.

## GitHub Actions

`.github/workflows/validate-korean-msghdr.yml`이 `korean/**` 또는 `MSGHDR_indexText.txt` 변경 시 기본 검증을 자동 실행한다.

현재 CI는 다음을 함께 검사한다.

- 번역 오버레이와 PS1 이벤트/제어 토큰 구조
- 네이티브 2바이트 MSGJ Huffman 왕복
- 한글 코드/폰트 슬롯 범위와 중복
- DBCS 대응 16글자 런타임 줄바꿈
- PSX.EXE 패처 단위 테스트
- CHD/BIN/CUE 재빌드 오케스트레이터의 해시 게이트, CUE 파싱, 파일 탐색·교체, 코드표 parity 단위 테스트

실제 디스크 재빌드와 에뮬레이터 화면 확인은 저작권이 있는 원본 이미지가 필요한 로컬 QA 단계로 남긴다.
