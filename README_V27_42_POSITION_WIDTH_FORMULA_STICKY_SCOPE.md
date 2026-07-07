# v27.42 position width/formula/sticky scope fix

## 전수조사 적용 결과

| 요청 | 수정 위치 | 적용 내용 |
|---|---|---|
| 보유 종목 현황 카드 가로 크기 복구 | `app/static/index.html` CSS | 운영현황 본문을 2:1 고정 비율로 복구하고 보유종목 표는 가로 스크롤 방식으로 복원 |
| 매수 금액 계산 공식 정상 표시 | `app/static/index.html` CSS | 과도한 고정 높이를 제거하고 내용 기준 높이로 복구 |
| 세로 스크롤 불필요 표는 표제목 고정 제외 | `app/static/index.html`, `app/static/app.js` | JS가 실제 세로 스크롤 필요 여부를 판정해 `.needs-vscroll` 패널에만 카드 제목/표 헤더 sticky 적용 |

## 검증
- Python 컴파일 확인
- JavaScript 문법 확인
- 버전: `v27.42-position-width-formula-sticky-scope`
