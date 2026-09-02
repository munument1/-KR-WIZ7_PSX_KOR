# PSX v11 아이템명 native passthrough 실험 (2026-09-02)

v9의 신규 MIPS 아이템 렌더러 주입은 실기에서 화면 붕괴와 프리즈를 일으켜 폐기했다. v11 EXP는 v10 안정판에서 최소 변경만 적용한다.

## 원인

`SCENARIJ.DBS`의 한국어 아이템 이름은 이미 프로젝트 native DBCS로 인코딩돼 있다. 기존 `FUN_8006D198`은 high byte 문자열을 발견하면 일본어 Shift-JIS 입력이라고 가정하고 임시 버퍼로 다시 변환한다. 이미 native인 한국어 바이트가 이 변환을 한 번 더 통과하면서 v8에서 깨졌다.

## v11 변경

- 신규 렌더러 주입 없음.
- `FUN_8006D198`의 `addiu s0,sp,0x18` 한 명령을 NOP 처리해 원본 native DBCS 입력 포인터를 유지.
- 인벤토리/아이템 상세 6개 호출부만 PS1에 이미 존재하는 DBCS-capable wrapper로 연결.
- v10에서 영어로 복구했던 571개 아이템명 필드만 한국어 필드로 되돌림.
- v10의 본문/메뉴/몬스터/한글 슬롯 경계 수정은 그대로 유지.

## 정적 변경 범위

v10 트리 대비 변경 파일은 정확히 2개다.

```text
PSX.EXE
CDS/D/SCENARIJ.DBS
```

`PSX.EXE`는 실제 9바이트만 달라진다(6개 JAL target byte + passthrough 명령의 non-zero 3바이트). `SCENARIJ.DBS`의 차이는 571개 아이템 이름 22-byte 필드 내부에만 존재하며 그 밖의 바이트 차이는 0이다.

## 빌드 검증

```text
v11 EXP BIN MD5    15eefa64ee67b194c482d5d0a4437399
v11 EXP BIN SHA256 e700723b54c94152fd48adfb2631930287bf0bb6c48878ccf535538224ef9a79
v11 EXP xdelta SHA256 5d746237e7500318702cba2108d30ed90ed376d2d8144e6a7ba47509fcbf921f
```

- 원본 BIN -> xdelta -> v11 EXP BIN: byte-identical.
- v11 EXP BIN -> CHD -> BIN: byte-identical.
- CHD verify 성공.
- 실기 검증 전까지 production/stable 경로에는 병합하지 않는다.

## 실기 확인 항목

1. 인벤토리를 열었을 때 프리즈가 없는가.
2. 아이템명이 한국어로 정상 표시되는가.
3. `/` 분할 이름이 정상인가.
4. 아이템 상세/감정 화면 진입과 종료가 정상인가.
