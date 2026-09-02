Wizardry VII PS1 한국어 자동 패처 v9
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

v9 핵심 수정
- v8의 잘못된 아이템 DBCS 호출 전환을 폐기
- SCENARIJ.DBS의 이미 인코딩된 한국어 아이템 이름을 Shift-JIS로 재변환하지 않도록
  PSX.EXE에 direct-native 아이템 렌더러 래퍼 4개를 새로 주입
- 인벤토리/아이템 상세의 아이템 이름 출력 8개 호출부를 원래 좌표/폰트 계열을 유지한 채
  direct-native 경로로 연결
- v8의 FONT.MMT 64-slot 행 경계 보정 유지 (예: "없음"의 "음"이 다른 음절로 치환되던 문제)
- 아이템 정보창의 초소형 고정폭 UI는 안정성을 위해 영어 유지
- PS1 영문패치 베이스 및 한국어 본문/아이템/몬스터/타이틀 오버레이 유지

현재 폰트 정책
- 본문/대화/아이템명/몬스터명: FONT.MMT + Galmuri11 + 2바이트 DBCS
- 초소형 1바이트 UI: 현재 영어 유지. 추후 OFONT.MMT + Galmuri7 전용 소형 한글 코드표 검토

검증 원본 raw BIN
MD5    188d3ee5a2a2242a719f290ea595e5ec
CRC32  bab5dd73

검증 한국어 v9 BIN
MD5    3b3f08395e545e9d42930bd0f780491e
SHA256 9af89f1545cbfd5e17b6b8cdeef482ddc473d0ffc2fbc40375283ade727a6adc
SIZE   324187920 bytes

v9 xdelta
MD5    997bb307fde02c6e9e48f51068418d79
SHA256 89c1c88a88495460442d6e5c6492ddee9d5017372e7d9466a1683f3759c78d66

검증
- 일본판 원본 BIN -> v9 xdelta -> v9 BIN 바이트 일치
- v9 BIN -> CHD -> BIN 바이트 일치
- chdman verify 성공
- v8 대비 실제 디스크 파일 변경은 PSX.EXE 1개뿐
- PS1 영문패치 파일시스템 대비 의도한 7개 파일만 변경
  MISCJ.HDR / MSGJ.DBS / MSGJ.HDR / SCENARIJ.DBS / FONT.MMT / TITL.MMT / PSX.EXE

현재 실제 플레이 테스트 중인 개발 빌드입니다.
이번 빌드에서는 인벤토리/아이템 상세의 한국어 아이템 이름과 "특이한 것은 없음" 등
행 경계 한글 치환 문구를 우선 확인해 주세요.

원본 게임 데이터는 배포 패키지에 포함하지 않습니다.
CHD 입력은 임시 raw BIN을 만들기 때문에 작업 중 충분한 디스크 여유 공간이 필요합니다.
