Wizardry VII PS1 한국어 자동 패처 v6
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

v6 핵심 변경점
- FONT.MMT 실제 저장 슬롯 = 렌더러 글리프 - 4 규칙 반영
- FONT.MMT 비트플레인 순서를 원래 0,1,2,3으로 복구
- Galmuri11을 1픽셀 왼쪽으로 배치해 모든 ㅏ가 ㅣ처럼 보이던 현상 수정
- Gertius WIZ7_PSX_ENG V1.0 디스크 배치를 기준으로 유지
- 한국어 MSGJ.DBS/HDR을 영문판 파일 크기까지 안전 패딩해 이후 파일 LBA가 이동하지 않도록 수정
- PCFILE.을 영문판과 동일한 LBA 742에 유지
- 캐릭터 생성/정보창의 고정폭 1바이트 UI는 우선 영어 ASCII 폴백
  (종족/직업/성별, LVL/RNK/EXP, 능력치 라벨, 직업 등급명)
- 한국어 본문/메뉴/아이템/몬스터는 유지

검증 원본 raw BIN MD5
188d3ee5a2a2242a719f290ea595e5ec

검증 한국어 v6 BIN MD5
38045b4a8629343c32b090f4f837ba7e

검증 한국어 v6 BIN SHA-256
a531ca24bb0d70ed7989dfe72a9fb571706176a36165fd392fb07a649db3c342

동작 방식
- BIN: xdelta3로 직접 패치
- CHD: 임시 BIN/CUE 추출 → xdelta3 적용 → 한국어 CHD 재생성 → chdman verify

원본 게임 데이터는 배포 패키지에 포함하지 않습니다.
CHD 입력은 임시 raw BIN을 만들기 때문에 작업 중 충분한 디스크 여유 공간이 필요합니다.
현재 실제 플레이 테스트 중인 개발 빌드입니다.
