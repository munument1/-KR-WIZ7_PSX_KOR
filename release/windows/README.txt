Wizardry VII PS1 한국어 자동 패처
================================

지원 입력
- Wizardry VII - Guardia no Houju (Japan).chd
- 같은 게임의 raw .bin

사용법
1. 원본 CHD 또는 BIN 파일을 "패치하기.bat" 위로 끌어다 놓습니다.
   또는 "패치하기.bat"을 더블클릭하고 파일 선택창에서 원본을 고릅니다.
2. 자동으로 원본을 검증하고 한국어 패치를 적용합니다.

출력
- CHD 입력: 원본과 같은 폴더에 Wizardry7_PSX_KOR.chd 생성
- BIN 입력: 원본과 같은 폴더에 Wizardry7_PSX_KOR.bin / Wizardry7_PSX_KOR.cue 생성

DuckStation
- CHD 입력: Wizardry7_PSX_KOR.chd를 바로 실행
- BIN 입력: Wizardry7_PSX_KOR.cue를 실행

검증 원본 raw BIN MD5
188d3ee5a2a2242a719f290ea595e5ec

검증 한국어 BIN MD5
656bdf3fb384efbd5733da6d68c3fa99

동작 방식
- BIN: xdelta3로 직접 패치
- CHD: 임시 BIN/CUE 추출 → xdelta3 적용 → 한국어 CHD 재생성 → chdman verify

원본 게임 데이터는 배포 패키지에 포함하지 않습니다.
CHD 입력은 임시 raw BIN을 만들기 때문에 작업 중 충분한 디스크 여유 공간이 필요합니다.
