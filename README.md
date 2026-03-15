# AI 기반 스크린샷 정보 추출 시스템 (AI-based Screenshot Insight Extractor)

AI 기술과 확장 가능한 클라우드 아키텍처를 적용하여, 스크린샷 속 비활성화된 이미지로부터 유의미한 정보를 추출하는 실용적인 솔루션을 구축한다.

## 1. 프로젝트 개요
일상에서 생성되는 스크린샷은 유용한 데이터를 포함하지만 대부분 활용되지 않는다. 본 프로젝트는 OCR 및 LLM 기술을 통합한 자동화 서비스를 통해 이미지 속 텍스트를 정보 자산으로 변환하는 것을 목표로 한다.

이는 단순 API 호출을 넘어, 실제 문제 해결을 위한 시스템을 설계하고 점진적으로 고도화하는 과정을 담고자 한다.

## 2. 아키텍처 설계
본 시스템은 확장성을 고려하여 3단계의 고도화 과정을 거쳐 개발한다. 각 기능 모듈을 독립적으로 설계하여, 변화하는 요구사항에 유연하게 대응하고 시스템의 안정성과 처리 용량을 점진적으로 확보하는 것을 목표로 한다.

### Phase 1: MVP 구현(완료)
+ 목표: 핵심 기능(이미지 업로드 → OCR → LLM 요약)의 기술적 타당성을 신속하게 검증한다.

+ 구조: Streamlit 기반의 단일 서버에서 모든 로직을 동기적으로 처리하는 모놀리식 구조를 채택한다. 이 방식은 신속한 개발에 용이하나, 대규모 요청 처리에는 한계가 있다.

### Phase 2: 기능 분리 및 비동기 처리(현재 단계)
+ 목표: UI 서버와 핵심 로직을 분리하여 시스템 안정성 및 확장성을 확보한다.

+ 지향 업로드/UI는 요청만 만들고, 실제 OCR·분석·인덱싱은 Job 단위로 분리된 백엔드가 비동기적으로 수행한다. 상태와 결과는 DB에 누적되어 재시도·관측·확장이 가능해야 하며, 모든 조회/처리는 유저 스코프(tenant) 기준으로 격리된다.

### Phase 3: 대규모 트래픽 대응
+ 목표: 실제 서비스 수준의 대규모 트래픽을 안정적으로 처리할 수 있는 고가용성 아키텍처를 구현한다.

+ 구조: 클라이언트가 Pre-signed URL을 통해 S3에 직접 업로드하고, SQS를 통해 요청을 안정적으로 제어하여 시스템 전체의 유연성을 더한다.

## 3. 적용 기술
+ Backend: FastAPI, SQLAlchemy
+ DB: PostgreSQL (docker-compose)
+ Frontend: Streamlit
+ OCR/LLM: Naver Clova OCR, OpenAI (현재 Streamlit 결합 상태)
+ Vector: FAISS + OpenAI Embeddings (로컬 파일 기반, 추후 교체 가능 지점)

## 4. 설치 커맨드
+ pip install -r requirements.txt
+ docker compose up -d
+ python -m scripts.init_db
+ uvicorn app.main:app --reload

## 5. Jobs API 실행 순서
+ docker compose up -d
+ python -m scripts.init_db
+ uvicorn app.main:app --reload


## 6. 설계 메모
- 인덱스 선택 이유  
  `get_job`의 실제 조회 조건이 `job_id + user_id`이고, 이번 변경의 핵심이 user scope 보호이기 때문에 `(user_id, job_id)` 인덱스를 우선 적용했다. 향후 유저별 목록 조회 API가 추가되면 `(user_id, created_at)` 인덱스는 그 시점에 다시 검토한다.

- 이후 확장 방향
  이번 PR에서는 Jobs API의 저장소를 Postgres로 전환하고, 생성 시 `queued` 상태만 저장하도록 범위를 제한했다. 이후 worker 도입 시 `queued -> running -> succeeded|failed` 상태머신과 `current_step`, `progress`, `attempt` 연결은 별도 PR에서 확장할 예정이다.

- 에러 코드 표준 초안  
  에러 코드는 `JOB_401`, `JOB_404`, `OCR_429`, `OCR_500`, `LLM_429`, `LLM_500`처럼 prefix 기반 규칙으로 정리하는 방향을 초안으로 둔다. 이번 PR에서는 핵심 동작 변경(Postgres 전환, user scope 강제)에 집중하고, 에러 코드 필드/포맷 도입은 하지 않고 문서 초안만 남긴다.
