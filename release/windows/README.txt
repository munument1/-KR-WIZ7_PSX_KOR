Wizardry VII PS1 한국어 자동 패처 v7
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

v7 빌드 기준
- 일본 PS1판 원본에 Gertius WIZ7_PSX_ENG V1.0을 먼저 적용한 결과를 실제 베이스로 사용합니다.
- DOS판/Gold판 실행 파일이나 UI 자산을 베이스로 사용하지 않습니다.
- 영문 PS1 패치가 수정한 PCFILE., SCENARIO.HDR, TALK.SCR, OPEN.STR, BOOK.STR, OPEN.TXT, AD.XA는 그대로 보존합니다.
- 그 위에 한국어 MSG/FONT/SCENARIO/EXE 오버레이를 적용합니다.

v7 핵심 변경점
- FONT.MMT 실제 저장 슬롯 = 렌더러 글리프 - 4 규칙 반영
- FONT.MMT 물리 비트플레인 순서는 0,1,2,3
- Galmuri11 x 배치를 1픽셀로 수정해 ㅏ가 ㅣ처럼 보이던 현상 해결
- 캐릭터 생성/정보창의 고정폭 UI는 DBCS 안정화를 위해 PS1 영문패치의 ASCII 문자열 사용
  (종족/직업/성별, LVL/RNK/EXP, 능력치 라벨, 직업 등급명 등)
- MSGJ.HDR/MSGJ.DBS는 PS1 영문패치 파일 크기에 맞춰 패딩해 후속 파일 LBA를 보존
- PCFILE.과 PS1 전용 영문 메뉴/미디어 자산을 영문패치와 동일하게 유지
- TITL.MMT에 남아 있던 일본어 부제 "ガーディアの宝珠"를 "가디아의 보주"로 교체
- 한국어 본문/메뉴/아이템/몬스터 번역 유지

검증 원본 raw BIN
MD5    188d3ee5a2a2242a719f290ea595e5ec
CRC32  bab5dd73

검증 PS1 영문패치 V1.0 BIN
MD5    7fb464147ab7144facae337226c91aa5
SHA256 6d61aaccf5a21853077f96b66e5fea4a2859611d89b5a93358e79d2f504c1683

검증 한국어 v7 BIN
MD5    381cf7ff7509f35b5fbc423791ed689d
SHA256 7dc0fb63ccd4565542e07c134881d54c4faa84c7145b73c67d6d5708f5d67df1

v7 xdelta SHA256
b421320fa47264b185be5e8fb95417d639e656cd0a52750f4cbeb61edd0f896a

검증
- 일본판 원본 BIN → v7 xdelta → v7 BIN 바이트 일치
- v7 BIN → CHD → BIN 바이트 일치
- chdman verify 성공
- PS1 영문패치 파일시스템 대비 의도한 7개 파일만 변경
  MISCJ.HDR / MSGJ.DBS / MSGJ.HDR / SCENARIJ.DBS / FONT.MMT / TITL.MMT / PSX.EXE

현재 실제 플레이 테스트 중인 개발 빌드입니다.
우선 확인할 항목:
- 기본 캐릭터 이름이 영어로 표시되는지
- 캐릭터 정보창 하단 깨진 글자가 사라졌는지
- 고정폭 UI가 영어로 안정적으로 표시되는지
- 타이틀 부제가 "가디아의 보주"로 표시되는지

원본 게임 데이터는 배포 패키지에 포함하지 않습니다.
CHD 입력은 임시 raw BIN을 만들기 때문에 작업 중 충분한 디스크 여유 공간이 필요합니다.
