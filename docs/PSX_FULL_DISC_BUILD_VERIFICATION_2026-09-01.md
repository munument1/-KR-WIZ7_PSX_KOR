# PS1 한국어판 전체 디스크 빌드 검증 — 2026-09-01

## 결론

실제 `Wizardry VII - Guardia no Houju (Japan)` CHD를 사용하여 다음 전체 경로를 끝까지 검증했다.

```text
CHD
→ chdman extractcd
→ 원본 BIN/CUE
→ dumpsxiso 전체 파일시스템 추출
→ 한국어 6개 자산 교체
→ mkpsxiso BIN/CUE 재빌드
→ dumpsxiso 재추출 비교
→ CHD 재압축/검증/재추출
→ xdelta 생성/재적용 검증
```

원본 게임 바이너리나 재빌드된 전체 게임 이미지는 저장소에 포함하지 않는다.

## 원본 검증

사용한 CHD:

- MD5: `87234265e920cf6a2e4d5426d39f6561`
- SHA-256: `a1d45439c8e38e9a9c106c7735d725f79a22596497ce0690442a8e33c1ecf4b0`

CHD에서 복원한 raw BIN:

- MD5: `188d3ee5a2a2242a719f290ea595e5ec`
- CRC32: `bab5dd73`
- 기존 WIZ7_PSX_ENG 기준 원본과 정확히 일치
- 트랙: 1개, `MODE2/2352`

## 무수정 재빌드 검증

`dumpsxiso 2.30`으로 원본 BIN을 추출하고 생성된 XML을 그대로 `mkpsxiso 2.30`에 입력했다.

- 파일: 351개
- 디렉터리: 22개
- 섹터: 137,964
- 재빌드 BIN MD5: `188d3ee5a2a2242a719f290ea595e5ec`
- 원본과 바이트 단위 100% 동일: **예**

따라서 현재 추출/재빌드 경로가 이 게임의 디스크 레이아웃을 손상시키지 않음을 확인했다.

## 한국어 자산 설치

실제 디스크에서 변경한 파일은 정확히 다음 6개다.

| 디스크 경로 | 한국어판 SHA-256 |
| --- | --- |
| `PSX.EXE` | `1b2e7a82f51a783b990cf904ad91e3a69cfa3b1c589fb26cc8bfb7cf6e97cb63` |
| `CDS/D/MISCJ.HDR` | `212c7e332aad766dd35988b16a622003b1a32a578dde9f3bba60dbf05bf4ef47` |
| `CDS/D/MSGJ.HDR` | `8f953f74fb74920c18f36d6c98c9254f506a03604656dcb3c3ae1a5d530f20e5` |
| `CDS/D/MSGJ.DBS` | `1429037840e89656ec925754353372d31b06841cb19c4b171126b0ac61790c60` |
| `CDS/D/SCENARIJ.DBS` | `f629d3aaa52552c0c8366a81a29934e28f395322e36b2c8ce23e252c9f43e1a1` |
| `CDS/T/FONT.MMT` | `f6e08770dba2d789ffaf3ff7896a1b270f3fba6ac0f113e9f186109298d11d58` |

## 한국어 BIN 결과

- 크기: `324503088` bytes
- 섹터: 137,969
- MD5: `656bdf3fb384efbd5733da6d68c3fa99`
- SHA-256: `9867c85b48514c1ba61c3e47b19ad09b8a8179d79cf7807a2b9fb676d4649d6d`
- 트랙: 1개, `MODE2/2352`
- System ID: `PLAYSTATION`
- Volume ID: `WIZARDRY7`
- Publisher ID: `SCE`
- Application ID: `PLAYSTATION`

원본보다 5섹터 증가했다. 주된 원인은 재인코딩된 `MSGJ.DBS` 크기 증가다.

## 재추출 비교

원본 재빌드 BIN과 한국어 BIN을 각각 다시 `dumpsxiso`로 추출해 모든 파일을 SHA-256 비교했다.

- 추출 파일 집합 차이: 0
- 내용이 달라진 게임 파일: 정확히 6개
- 예상하지 않은 변경 파일: 0
- 나머지 게임 파일: 원본과 동일

즉 디스크 재배치 때문에 다른 파일 내용이 변형되지 않았다.

## CHD 왕복 검증

한국어 CUE/BIN을 `chdman createcd`로 다시 CHD로 만들었다.

- Raw SHA1 verification: 성공
- Overall SHA1 verification: 성공
- 생성한 CHD를 다시 BIN으로 추출: 성공
- 재추출 BIN이 한국어 BIN과 바이트 단위 동일: **예**

## xdelta 검증

원본 raw BIN → 한국어 BIN xdelta 테스트 패치를 생성했다.

- xdelta SHA-256: `868f85d2a2d9d7bee371844e517603d28ae572a60ece56089cc1456bb6cf75ef`
- 크기: 약 293 KiB
- 원본 BIN에 패치를 다시 적용한 결과가 한국어 BIN과 바이트 단위 동일: **예**

따라서 배포 시 전체 게임 이미지를 포함할 필요 없이 작은 패치만 제공할 수 있다.

## 도구 체인

재현성을 위해 `.github/workflows/build-psx-toolchain.yml`을 추가했다.

현재 검증 도구:

- `chdman` — CHD ↔ BIN/CUE
- `dumpsxiso 2.30` — PS1 디스크 추출/XML 생성
- `mkpsxiso 2.30` — PS1 BIN/CUE 재빌드
- `xdelta3` — 배포용 바이너리 패치 생성/검증

## 남은 검증

이 문서는 바이너리/디스크 구조 수준의 전체 빌드 검증이다. 다음 단계는 DuckStation 등 실제 PS1 실행 환경에서 다음을 확인하는 것이다.

- 부팅 및 새 게임 진입
- 한국어 대사 출력
- 아이템/몬스터 이름 출력
- 줄바꿈 및 UI 깨짐
- 초반 이벤트/전투 진행
- 저장/불러오기
