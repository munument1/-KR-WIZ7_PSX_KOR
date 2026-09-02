Wizardry VII PS1 한국어 자동 패처 v8
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

v8 빌드 기준
- 일본 PS1판 원본에 Gertius WIZ7_PSX_ENG V1.0을 먼저 적용한 결과를 베이스로 사용합니다.
- DOS판/Gold판 실행 파일이나 UI 자산을 베이스로 사용하지 않습니다.
- 영문 PS1 패치의 메뉴/미디어/스크립트 자산은 유지하고 한국어 MSG/FONT/SCENARIO/EXE만 오버레이합니다.

v8 핵심 변경점
- FONT.MMT의 실제 관계를 단순 renderer-4가 아닌 64셀 행 내부 1셀 좌측 래핑으로 수정
- 이 경계 버그로 다른 정상 한글로 치환되던 16자 일괄 수정
  퍼 팽 팬 팩 / 읏 읍 음 읊 / 봄 볼 본 복 / 되 됐 돼 동
- 제보된 "없음 -> 없본" 현상을 같은 원인으로 수정
- Galmuri11 x 배치 1픽셀 유지(ㅏ가 ㅣ처럼 보이던 문제 수정 유지)
- SCENARIJ.DBS의 한국어 아이템 이름을 표시하도록 PSX.EXE 아이템 이름 출력 6개 호출부를 DBCS 경로로 전환
- 아이템 정보창의 초소형/고정폭 UI는 깨짐 방지를 위해 PS1 영문판 ASCII로 임시 안정화
  (USE/ASSAY/SPECIAL/DAMAGE/RESISTANCES 등)
- 캐릭터 정보창의 고정폭 UI도 계속 영어 ASCII로 유지
- TITL.MMT의 일본어 부제는 "가디아의 보주"로 유지

현재 폰트 정책
- 본문/대화/아이템명/몬스터명: FONT.MMT + Galmuri11 + 2바이트 DBCS
- 초소형 1바이트 UI: 현재 영어 유지. 추후 OFONT.MMT + Galmuri7 전용 소형 한글 코드표 검토

검증 원본 raw BIN
MD5    188d3ee5a2a2242a719f290ea595e5ec
CRC32  bab5dd73

검증 한국어 v8 BIN
MD5    fcb5eb5d6d5db9ac511585b9d7e74033
SHA256 50237b8b2feb0ec9f30896fb93810d65307ebad9ae7df0295788389ea3371ed6

v8 xdelta SHA256
80a7f13918874547c8b200614ebea99de642648820843fcd147a43feea314703

검증
- 일본판 원본 BIN → v8 xdelta → v8 BIN 바이트 일치
- v8 BIN → CHD → BIN 바이트 일치
- chdman verify 성공
- PS1 영문패치 파일시스템 대비 의도한 7개 파일만 변경
  MISCJ.HDR / MSGJ.DBS / MSGJ.HDR / SCENARIJ.DBS / FONT.MMT / TITL.MMT / PSX.EXE
- 현재 공용 코드표 1,133개 한글을 새 FONT 행-래핑 규칙으로 전수 검증

현재 실제 플레이 테스트 중인 개발 빌드입니다.
우선 확인할 항목:
- "특이한 것은 없음"에서 "없음"이 정확히 표시되는지
- 게임 곳곳에서 특정 한글이 다른 한글로 치환되던 현상이 사라졌는지
- 인벤토리/아이템 목록의 아이템 이름이 한국어로 표시되는지
- 아이템 정보창에 깨진 글자가 사라지고 작은 라벨은 영어로 정상 표시되는지

원본 게임 데이터는 배포 패키지에 포함하지 않습니다.
CHD 입력은 임시 raw BIN을 만들기 때문에 작업 중 충분한 디스크 여유 공간이 필요합니다.
