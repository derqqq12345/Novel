"""
소설 내보내기 서비스 테스트
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chapter import Chapter
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.schemas.export import PDFFormatOptions
from backend.app.services.export_service import export_service


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """테스트 사용자 생성"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def test_project(db: AsyncSession, test_user: User) -> Project:
    """테스트 프로젝트 생성"""
    project = Project(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="테스트 소설",
        genre="fantasy",
        description="테스트용 소설입니다.",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(project)
    await db.flush()
    return project


@pytest.fixture
async def test_chapters(db: AsyncSession, test_project: Project) -> list[Chapter]:
    """테스트 챕터 생성"""
    chapters = []
    for i in range(1, 4):
        chapter = Chapter(
            id=uuid.uuid4(),
            project_id=test_project.id,
            chapter_number=i,
            title=f"챕터 {i}",
            content=f"이것은 챕터 {i}의 내용입니다.\n\n" * 50,  # 충분한 길이
            word_count=100 * i,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(chapter)
        chapters.append(chapter)
    await db.flush()
    return chapters


@pytest.mark.asyncio
async def test_export_to_txt(
    db: AsyncSession, test_project: Project, test_chapters: list[Chapter]
):
    """TXT 내보내기 테스트"""
    # TXT 내보내기 실행
    output_path = await export_service.export_to_txt(db, test_project.id)

    # 파일 생성 확인
    assert output_path.exists()
    assert output_path.suffix == ".txt"

    # 파일 내용 확인
    content = output_path.read_text(encoding="utf-8")
    assert test_project.title in content
    assert "챕터 1" in content
    assert "챕터 2" in content
    assert "챕터 3" in content

    # 정리
    output_path.unlink()


@pytest.mark.asyncio
async def test_export_to_pdf(
    db: AsyncSession, test_project: Project, test_chapters: list[Chapter]
):
    """PDF 내보내기 테스트"""
    # PDF 옵션 설정
    options = PDFFormatOptions(
        font_size=12,
        line_spacing=1.5,
        include_toc=True,
        include_page_numbers=True,
    )

    # PDF 내보내기 실행
    output_path = await export_service.export_to_pdf(db, test_project.id, options)

    # 파일 생성 확인
    assert output_path.exists()
    assert output_path.suffix == ".pdf"
    assert output_path.stat().st_size > 0

    # 정리
    output_path.unlink()


@pytest.mark.asyncio
async def test_export_to_epub(
    db: AsyncSession, test_project: Project, test_chapters: list[Chapter]
):
    """EPUB 내보내기 테스트"""
    # EPUB 내보내기 실행
    output_path = await export_service.export_to_epub(db, test_project.id)

    # 파일 생성 확인
    assert output_path.exists()
    assert output_path.suffix == ".epub"
    assert output_path.stat().st_size > 0

    # 정리
    output_path.unlink()


@pytest.mark.asyncio
async def test_export_empty_project(db: AsyncSession, test_project: Project):
    """챕터가 없는 프로젝트 내보내기 테스트"""
    # 챕터가 없는 프로젝트 내보내기 시도
    with pytest.raises(ValueError, match="내보낼 챕터가 없습니다"):
        await export_service.export_to_txt(db, test_project.id)


@pytest.mark.asyncio
async def test_export_nonexistent_project(db: AsyncSession):
    """존재하지 않는 프로젝트 내보내기 테스트"""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="프로젝트를 찾을 수 없습니다"):
        await export_service.export_to_txt(db, fake_id)
