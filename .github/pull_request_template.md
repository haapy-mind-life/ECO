# ECO: Streamlit UX 개선 적용

## 변경 요약
- URL 딥링크(쿼리 파라미터) 반영
- 그룹 인지형 상세 필터(차원 토글)
- 빈 결과 가이드 및 KPI 카드
- CSV 다운로드 가드(보안 동의 + 행 제한)
- (On-prem) DRF→Parquet 일일 동기화 / 캐시 로더

## 체크리스트
- [ ] 로컬 구동 확인 (`streamlit run main.py`)
- [ ] DRF API 접근성 확인 (사내망/Cloud 각각)
- [ ] 데이터 스키마 컬럼 확인
- [ ] Nginx 리버스 프록시 경로(`/fmw`) 점검
- [ ] 보안 가이드 복기(내부 반출 금지)
