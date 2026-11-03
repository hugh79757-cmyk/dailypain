## 2026-10-25 22:30 — DAILYPAIN-THREADS-02

### 한 일
- 필터 결함 수정: None post_id 대체 키(permalink/hash) + 광고 불만 글 유지(exclude_policy 좁힘).
- Llama: 마크다운 펜스 제거 파싱 + cluster() 실제 군집(카테고리 기준, pain_score 최대값).
- worker: 부분 본문 POST null 기본값 적용.
- 테스트 4건 통과(test_filters 3, test_cluster 1).
- 데모 데이터 고정 파일 data/demo_pains.json 생성.
- UI 별표 보안 방식 (a) 채택: 관리자 페이지에서 토큰 로컬 입력, 코드에 저장 안 함. 출처 필터·링크 폴백은 서버 지원 완료, UI HTML은 인라인 minified라 후속.

### 결과
- [검증됨] 필터 단위 테스트 통과 (None post_id, 광고 불만 글 케이스). 근거: pytest 3 passed.
- [검증됨] 군집 단위 테스트 통과. 근거: pytest 1 passed.
- [검증됨] worker 부분 POST: null 기본값 코드 적용.
- [검증불가] Llama 형식 검증: 엔드포인트·키 미확보 → "미검증" 명시. fail-open 유지.
- [검증불가] 수집 end-to-end: 공개 페이지 실측 미수행 (운영 계정 로그인 금지 유지).
- [검증불가] 배포·D1: hugh79757 계정 토큰 미확인, database_id 미설정.
- [부분검증] UI: 서버 source 필터 지원, HTML 인라인 편집 미완.

### 잔존 위험
- 배포·D1·수집 실측·제출 문서·데모 영상 미완. Llama 미검증.

### 다음 행동
- 대표님과 hugh79757 토큰·Llama 키 협의 후 배포 및 실측.
완료 — 0번 verify 요청

---

## 2026-10-25 21:50 — DAILYPAIN-THREADS-01

### 한 일
- /Users/twinssn/Projects/dailypain → /Users/twinssn/projects2/dailypain 복원 (worker.js, collector, sql).
- SQL: pain_points에 Threads 확장 컬럼(post_id, author, permalink, source_ext) 추가.
- worker.js: POST /api/pain Threads 필드 저장 + source 필터(/api/pains?source=).
- collector/threads_collector.py: 한국어 필터·중복제거·제외정책.
- collector/llama_analyze.py: Llama 채점 4축 가중치, 군집, fail-open.

### 결과
- [부분검증] 워커 복원 + UI 렌더링: 원본 worker.js 재사용, 배포는 미수행.
- [검증불가] D1 확인: hugh79757 계정 기존 pain_points DB 존재 여부 미확인.
- [검증불가] 수집 실측: 미수행.
- [부분검증] 필터/llama: 코드 작성, 실행 미검증.

### 잔존 위험
- 배포·D1·수집 실측 미완. 데모 데이터 고정 미완. 제출 문서 미작성.

### 다음 행동
- hugh79757 계정으로 D1 확인 및 배포.
- Threads 공개 페이지 실측 수행.
- 데모 데이터 고정 + 영어 제출 문서 작성.