Wizardry VII PS1 한국어 자동 패처 v3
====================================

지원 입력
- Wizardry VII - Guardia no Houju (Japan).chd
- 같은 게임의 raw .bin

사용법
1. ZIP을 완전히 압축 해제합니다.
2. 원본 CHD 또는 BIN 파일을 PATCH.bat 위로 끌어다 놓습니다.
   또는 PATCH.bat을 더블클릭하고 파일 선택창에서 원본을 고릅니다.
3. 자동으로 원본을 검증하고 한국어 패치를 적용합니다.

출력
- CHD 입력: 원본과 같은 폴더에 Wizardry7_PSX_KOR.chd 생성
- BIN 입력: 원본과 같은 폴더에 Wizardry7_PSX_KOR.bin / Wizardry7_PSX_KOR.cue 생성

DuckStation
- CHD 입력: Wizardry7_PSX_KOR.chd를 바로 실행
- BIN 입력: Wizardry7_PSX_KOR.cue를 실행

v3 변경점
- 실제 PS1 출력에서 확인된 FONT.MMT 논리 비트플레인 순서 수정
  (0/2번 논리 글리프가 서로 바뀌어 보이던 한글 깨짐 수정)
- Gertius WIZ7_PSX_ENG V1.0 전체 변경을 베이스로 통합
- 아직 한국어화하지 않은 PS1 전용 일본어 메뉴/영상/관련 자산은 영문화판 자산 유지
- 영문판 SCENARIJ.DBS 이벤트/스크립트 수정을 보존하면서 아이템/몬스터 이름만 한국어로 병합

검증 원본 raw BIN MD5
188d3ee5a2a2242a719f290ea595e5ec

검증 한국어 v3 BIN MD5
7b94f5ccb6cfcbd0c87a856d8c60056a

검증 한국어 v3 BIN SHA-256
80781023cae9e3c96d72f4d090995931f1f8df0f87bb40ff2eaf200827eb38f9

동작 방식
- BIN: xdelta3로 직접 패치
- CHD: 임시 BIN/CUE 추출 → xdelta3 적용 → 한국어 CHD 재생성 → chdman verify

원본 게임 데이터는 배포 패키지에 포함하지 않습니다.
CHD 입력은 임시 raw BIN을 만들기 때문에 작업 중 충분한 디스크 여유 공간이 필요합니다.
현재 실제 플레이 테스트 중인 개발 빌드입니다.
