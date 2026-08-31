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

## GitHub Actions

`.github/workflows/validate-korean-msghdr.yml`이 `korean/**` 또는 `MSGHDR_indexText.txt` 변경 시 기본 검증을 자동 실행한다.

현재 단계에서 이 검증은 **번역 품질 검사**가 아니라 **PS1 메시지 구조와 이벤트 토큰 보존 검사**다. 실제 게임 화면의 줄바꿈, 폭, 한글 폰트, Huffman 재압축 결과는 별도 QA가 필요하다.
