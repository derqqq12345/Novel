"""
일관성 검증 서비스 테스트
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.chapter import Chapter
from backend.app.models.character import Character
from backend.app.models.plot import PlotPoint
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.models.worldbuilding import WorldBuilding
from backend.app.services.consistency_checker import ConsistencyCheckerService


# ─── 테스트 픽스처 ────────────────────────────────────────────────────────────


@pytest.fixture
async def db_session():
    """인메모리 SQLite 데이터베이스 세션을 생성합니다."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """테스트 사용자를 생성합니다."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        username="testuser",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_project(db_session: AsyncSession, test_user: User):
    """테스트 프로젝트를 생성합니다."""
    project = Project(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="테스트 소설",
        genre="fantasy",
        description="테스트용 판타지 소설",
        ai_model="qwen",
        ai_model_config={},
        total_word_count=0,
        status="active",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest.fixture
async def test_character(db_session: AsyncSession, test_project: Project):
    """테스트 캐릭터를 생성합니다."""
    character = Character(
        id=uuid.uuid4(),
        project_id=test_project.id,
        name="주인공",
        age=25,
        personality_traits=["용감한", "정의로운"],
        appearance="검은 머리, 키가 큰",
        background="평범한 마을 출신",
        relationships={},
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(character)
    await db_session.flush()
    return character


@pytest.fixture
async def test_chapter(
    db_session: AsyncSession,
    test_project: Project,
):
    """테스트 챕터를 생성합니다."""
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=test_project.id,
        chapter_number=1,
        title="첫 번째 챕터",
        content="주인공은 25세의 용감한 전사였다. 그는 마을을 지키기 위해 싸웠다.",
        word_count=30,
        consistency_score=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_deleted=False,
    )
    db_session.add(chapter)
    await db_session.flush()
    return chapter


# ─── 테스트 케이스 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_chapter_consistency_no_issues(
    db_session: AsyncSession,
    test_chapter: Chapter,
    test_character: Character,
):
    """일관성 이슈가 없는 경우 100점을 반환해야 합니다."""
    service = ConsistencyCheckerService()
    
    score, issues = await service.check_chapter_consistency(
        db_session, test_chapter.id
    )
    
    assert score == 100
    assert len(issues) == 0
    
    # 챕터의 consistency_score가 업데이트되었는지 확인
    result = await db_session.execute(
        select(Chapter).where(Chapter.id == test_chapter.id)
    )
    updated_chapter = result.scalar_one()
    assert updated_chapter.consistency_score == 100


@pytest.mark.asyncio
async def test_check_character_consistency_undefined_character(
    db_session: AsyncSession,
    test_project: Project,
    test_character: Character,
):
    """정의되지 않은 캐릭터가 언급되면 이슈를 생성해야 합니다."""
    # 정의되지 않은 캐릭터를 언급하는 챕터
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=test_project.id,
        chapter_number=2,
        title="두 번째 챕터",
        content="주인공과 악당이 싸웠다. 악당은 강력한 마법을 사용했다.",
        word_count=25,
        consistency_score=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_deleted=False,
    )
    db_session.add(chapter)
    await db_session.flush()
    
    service = ConsistencyCheckerService()
    score, issues = await service.check_chapter_consistency(
        db_session, chapter.id
    )
    
    # 정의되지 않은 캐릭터 "악당"에 대한 이슈가 있어야 함
    assert score < 100
    assert len(issues) > 0
    
    # 이슈 타입 확인
    character_issues = [i for i in issues if i.issue_type == "character"]
    assert len(character_issues) > 0
    assert any("악당" in issue.description for issue in character_issues)


@pytest.mark.asyncio
async def test_check_character_consistency_age_mismatch(
    db_session: AsyncSession,
    test_project: Project,
    test_character: Character,
):
    """캐릭터 나이가 일치하지 않으면 이슈를 생성해야 합니다."""
    # 나이가 다르게 언급된 챕터
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=test_project.id,
        chapter_number=3,
        title="세 번째 챕터",
        content="주인공은 30세였다. 그는 오랜 전투 경험이 있었다.",
        word_count=20,
        consistency_score=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_deleted=False,
    )
    db_session.add(chapter)
    await db_session.flush()
    
    service = ConsistencyCheckerService()
    score, issues = await service.check_chapter_consistency(
        db_session, chapter.id
    )
    
    # 나이 불일치 이슈가 있어야 함
    assert score < 100
    assert len(issues) > 0
    
    age_issues = [
        i for i in issues 
        if "나이" in i.description and i.severity == "high"
    ]
    assert len(age_issues) > 0


@pytest.mark.asyncio
async def test_check_plot_consistency_missing_target(
    db_session: AsyncSession,
    test_project: Project,
    test_character: Character,
):
    """목표 플롯 포인트가 언급되지 않으면 이슈를 생성해야 합니다."""
    # 플롯 포인트 생성
    plot = PlotPoint(
        id=uuid.uuid4(),
        project_id=test_project.id,
        title="마왕과의 대결",
        description="주인공이 마왕과 최종 대결을 벌인다",
        plot_stage="climax",
        sequence_order=1,
        is_completed=False,
        target_chapter=1,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(plot)
    
    # 플롯과 무관한 내용의 챕터
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=test_project.id,
        chapter_number=1,
        title="첫 번째 챕터",
        content="주인공은 평화로운 마을에서 일상을 보냈다.",
        word_count=20,
        consistency_score=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_deleted=False,
    )
    db_session.add(chapter)
    await db_session.flush()
    
    service = ConsistencyCheckerService()
    score, issues = await service.check_chapter_consistency(
        db_session, chapter.id
    )
    
    # 플롯 이슈가 있어야 함
    plot_issues = [i for i in issues if i.issue_type == "plot"]
    assert len(plot_issues) > 0
    assert any("목표 플롯" in issue.description for issue in plot_issues)


@pytest.mark.asyncio
async def test_check_worldbuilding_consistency_rule_violation(
    db_session: AsyncSession,
    test_project: Project,
    test_character: Character,
):
    """세계관 규칙 위반 시 이슈를 생성해야 합니다."""
    # 세계관 규칙 생성
    worldbuilding = WorldBuilding(
        id=uuid.uuid4(),
        project_id=test_project.id,
        category="magic_system",
        name="마법",
        description="이 세계의 마법 시스템",
        rules={"forbidden": "시간 여행"},
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(worldbuilding)
    
    # 금지된 요소를 사용하는 챕터
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=test_project.id,
        chapter_number=4,
        title="네 번째 챕터",
        content="주인공은 마법을 사용하여 시간 여행을 했다.",
        word_count=15,
        consistency_score=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_deleted=False,
    )
    db_session.add(chapter)
    await db_session.flush()
    
    service = ConsistencyCheckerService()
    score, issues = await service.check_chapter_consistency(
        db_session, chapter.id
    )
    
    # 세계관 규칙 위반 이슈가 있어야 함
    wb_issues = [i for i in issues if i.issue_type == "worldbuilding"]
    assert len(wb_issues) > 0
    assert any("금지된 요소" in issue.description for issue in wb_issues)


@pytest.mark.asyncio
async def test_calculate_consistency_score_with_multiple_issues(
    db_session: AsyncSession,
    test_project: Project,
    test_character: Character,
):
    """여러 이슈가 있을 때 심각도에 따라 점수가 차감되어야 합니다."""
    # 여러 문제가 있는 챕터
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=test_project.id,
        chapter_number=5,
        title="다섯 번째 챕터",
        content="주인공은 30세였다. 악당과 싸웠다. 주인공은 겁먹고 도망쳤다.",
        word_count=20,
        consistency_score=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        is_deleted=False,
    )
    db_session.add(chapter)
    await db_session.flush()
    
    service = ConsistencyCheckerService()
    score, issues = await service.check_chapter_consistency(
        db_session, chapter.id
    )
    
    # 여러 이슈가 있어야 함
    assert len(issues) >= 2
    
    # 점수가 100보다 낮아야 함
    assert score < 100
    
    # 심각도별 이슈 확인
    high_issues = [i for i in issues if i.severity == "high"]
    medium_issues = [i for i in issues if i.severity == "medium"]
    
    # 나이 불일치 (high), 정의되지 않은 캐릭터 (medium), 성격 모순 (medium)
    assert len(high_issues) >= 1
    assert len(medium_issues) >= 1


@pytest.mark.asyncio
async def test_extract_character_names_korean(
    db_session: AsyncSession,
    test_project: Project,
):
    """한글 캐릭터 이름을 정확히 추출해야 합니다."""
    # 여러 캐릭터 생성
    characters = [
        Character(
            id=uuid.uuid4(),
            project_id=test_project.id,
            name=name,
            age=20,
            personality_traits=[],
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        for name in ["김철수", "이영희", "박민수"]
    ]
    for char in characters:
        db_session.add(char)
    await db_session.flush()
    
    service = ConsistencyCheckerService()
    
    # 캐릭터 이름 추출 테스트
    text = "김철수와 이영희가 만났다. 박민수는 멀리서 지켜보았다."
    extracted = service._extract_character_names(text, characters)
    
    assert len(extracted) == 3
    assert "김철수" in extracted
    assert "이영희" in extracted
    assert "박민수" in extracted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
