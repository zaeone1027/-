# 대표병 결산 생성 프로그램 (Google Cloud Run 배포용)

이 저장소는 생활관 인원의 결산을 생성하는 Streamlit 기반 웹 애플리케이션입니다.
Google Cloud Platform (GCP)의 **Cloud Run** 서비스에 배포하기 위해 Docker 환경이 구성되어 있습니다.

## 배포 방법 (Google Cloud)
1. 이 파일들을 GitHub 레포지토리에 푸시(Push)합니다.
2. Google Cloud Console에 접속하여 Cloud Shell을 엽니다.
3. 레포지토리를 클론(Clone)합니다.
4. 아래 명령어로 Cloud Run에 배포합니다:
   `gcloud run deploy squad-dashboard --source . --port 8080 --allow-unauthenticated`

**주의사항 (데이터 지속성)**:
Cloud Run은 상태를 유지하지 않는(Stateless) 컨테이너입니다. 
로컬 SQLite 파일(`squad.db`)을 사용하면 컨테이너가 재시작될 때 데이터가 초기화됩니다. 
영구적인 저장을 위해서는 GCP의 **Cloud Storage FUSE**를 마운트하거나 **Cloud SQL**을 연동하는 아키텍처 확장이 필요합니다.
