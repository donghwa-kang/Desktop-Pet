# Windows 로컬에서 이어가기

현재 모델을 직접 편집하는 시작 절차다. 클라우드 환경이나 Unity를 새로 준비할 필요는 없다.

## 1. 저장소를 로컬 폴더에 준비

Git을 사용할 수 있는 PowerShell에서 원하는 작업 폴더로 이동한 뒤 실행한다.

```powershell
git clone https://github.com/donghwa-kang/Desktop-Pet.git
cd Desktop-Pet
```

이미 이 저장소를 복제했다면 먼저 `git status`로 로컬 변경을 확인한다. 변경이 없는 `main` 작업본에서는 `git pull --ff-only`로 업데이트할 수 있다. 다른 작업이 있으면 덮어쓰지 말고 보존한 뒤 최신 변경을 가져온다.

Codex에서 이 `Desktop-Pet` 폴더를 열고 작업 위치를 **This computer / 이 컴퓨터**로 선택한다. 시작할 때 `AGENTS.md`와 `docs/HANDOFF.md`를 읽게 한다.

## 2. 모델 준비

[최신 모델 ZIP 다운로드](https://drive.google.com/file/d/1v9LjZD3fCzQs4TVqE2TAsByFbadaCyzX/view). 기존 업로드 계정으로 로그인한다. 링크는 공개 공유로 바꾸지 않았으며, Git 저장소에는 이 ZIP이나 `.blend`가 들어 있지 않다.

ZIP을 풀면 `ogong_fullbody05/ogong_fullbody05.blend`, 렌더 7장, 검수 JSON과 설명서가 나온다. Blender의 **File → Open**으로 `.blend`를 연다. 이미 같은 파일을 열었다면 다시 다운로드하거나 재생성할 필요는 없다.

전달본 확인값:

- ZIP 크기: **100,884,196 bytes**.
- `.blend` 크기: **96,909,802 bytes**.
- ZIP SHA-256: `ec7cc8cfe12cd816d223467234dd45e33d846858b8812fea28d54e4be12e60b6`.
- 기본 표정: **closed**. 개인 원본 참고 사진: **0장**.

선택적으로 다운로드한 ZIP을 PowerShell에서 확인한다. 아래 이름은 실제 다운로드 파일명과 다르면 수정한다.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '.\ogong_fullbody05.zip'
```

직접 수정할 때는 `ArtSource/FullbodyStudy/`처럼 Git에서 제외된 작업 폴더에 별도 이름의 사본을 저장한다. 예: `ogong_fullbody06_work.blend`. 이 이름은 다음 작업본을 위한 예시이며, 해당 모델이 이미 만들어졌다는 뜻은 아니다.

## 3. Blender MCP 확인

Blender MCP 서버를 켠 상태로 유지한다. 사용자가 제공한 현재 설정은 다음과 같다.

| 항목 | 현재 기준 |
| --- | --- |
| Blender 애드온 | MCP for Blender 1.8 |
| 실행 명령 | 로컬 설치의 `mcp-for-blender.exe` 절대 경로 |
| `BLENDER_HOST` | `localhost` |
| `BLENDER_PORT` | `9876` |

Windows의 실행 파일 경로를 Linux 클라우드 경로로 바꾸거나 새 클라우드 서버를 추가하지 않는다. 현재 EXE의 존재와 프로세스 실행 여부는 로컬에서 확인한다. Blender 버전과 실제 사용 가능한 MCP 도구도 로컬에서 확인한다.

첫 확인은 **현재 열린 파일명, Blender 버전, 장면 오브젝트 수를 읽기**다. 모델과 장면을 수정하지 않고 이 정보를 실제 도구 응답으로 확인한다. 애드온의 포트 표시만 보고 성공했다고 답하지 않는다.

로컬에서도 도구가 없으면 Codex의 MCP 서버 활성화·시작 오류와 실행 경로부터 확인한다. 셸에서 `codex` 명령을 사용할 수 있다면 `codex mcp list`로 등록 상태를 볼 수 있다. CLI가 없다는 이유로 모델링 자체가 불가능한 것은 아니다.

설정 화면의 `BLENDER_MCP_DISABLE_TELEMETRY=1`은 현재 [MCP for Blender 설정 문서](https://www.mcp-for-blender.com/docs/reference/configuration)의 `DISABLE_TELEMETRY=true`와 다르다. 텔레메트리를 끄려면 문서에 맞춰 수정한다. 이 항목을 연결 실패의 원인으로 단정하지 않는다.

## 4. 참조 자료 준비

개인 강아지 사진은 로컬 `ReferencePhotos/`에 둔다. 사용자가 가장 나중에 제공한 **입을 다문 5방향 그림**을 별도 참조로 보관한다. Git에는 사진 원본과 그림이 포함돼 있지 않으므로 README의 모델 렌더를 실제 사진으로 착각하지 않는다.

Blender 전달본에도 개인 사진이 내장돼 있지 않다. 원본 사진이나 최신 그림이 이미 컴퓨터에 있으면 그 파일을 사용하고, 필요한 참조만 찾을 수 없을 때 사용자에게 요청한다.

## 5. 새 로컬 대화의 첫 메시지

아래를 붙여 넣으면 인수인계부터 진행할 수 있다.

```text
이 저장소의 AGENTS.md와 docs/HANDOFF.md, docs/LOCAL_SETUP.md,
docs/CONVERSATION_HISTORY.md를 읽고 기존 오공이 작업을 이어줘.

클라우드 대신 이 Windows 컴퓨터의 로컬 Blender MCP를 사용해줘.
먼저 현재 열린 파일명, Blender 버전과 장면 오브젝트 수를 읽어 연결을 확인해줘.
최신 기준 모델은 입을 다문 ogong_fullbody05.blend야.
우리 강아지의 얼굴과 다리·목·몸통 비율을 기준 사진에 최대한 가깝게 다듬는 작업이 우선이야.
원본을 보존하고 수정본은 새 파일명으로 저장해줘.
```

## 생성 스크립트는 필요할 때만

기존 장면을 직접 편집하는 데 Python 표면 추출 파이프라인을 재설치할 필요는 없다. 전체 재생성이 필요할 때는 [REPRODUCING.md](REPRODUCING.md)를 따른다. 선행 사진과 재질 장면이 필요하고, 같은 태그 실행은 생성 파일을 덮어쓴다. 클라우드의 `/tmp` 설치 경로는 Windows에 존재하지 않는다.
