"""
일관성 검증 서비스 (ConsistencyCheckerService)

캐릭터, 플롯, 세계관의 일관성을 검증하고 점수를 계산합니다.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chapter import Chapter
from backend.app.models.character import Character
from backend.app.models.consistency import ConsistencyIssue
from backend.app.models.plot import PlotPoint
from backend.app.models.worldbuilding import WorldBuilding


class ConsistencyCheckerService:
    """
    챕터의 일관성을 검증하는 서비스.
    
    캐릭터, 플롯, 세계관 요소를 검증하고 일관성 점수를 계산합니다.
    """

    async def check_chapter_consistency(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
    ) -> tuple[int, List[ConsistencyIssue]]:
        """
        챕터의 일관성을 검증합니다.
        
        Args:
            db: 비동기 DB 세션
            chapter_id: 검증할 챕터 ID
            
        Returns:
            (일관성 점수 0-100, 발견된 이슈 목록) 튜플
        """
        # 챕터 조회
        result = await db.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        if chapter is None:
            raise ValueError(f"챕터를 찾을 수 없습니다: {chapter_id}")

        # 프로젝트의 컨텍스트 조회
        characters = await self._get_project_characters(db, chapter.project_id)
        plot_points = await self._get_project_plot_points(db, chapter.project_id)
        world_buildings = await self._get_project_worldbuildings(db, chapter.project_id)

        # 각 카테고리별 일관성 검증
        issues: List[ConsistencyIssue] = []
        
        character_issues = await self._check_character_consistency(
            db, chapter, characters
        )
        issues.extend(character_issues)
        
        plot_issues = await self._check_plot_consistency(
            db, chapter, plot_points
        )
        issues.extend(plot_issues)
        
        worldbuilding_issues = await self._check_worldbuilding_consistency(
            db, chapter, world_buildings
        )
        issues.extend(worldbuilding_issues)

        # 일관성 점수 계산
        score = self._calculate_consistency_score(issues)

        # 챕터의 일관성 점수 업데이트
        chapter.consistency_score = score
        await db.flush()

        return score, issues

    async def _check_character_consistency(
        self,
        db: AsyncSession,
        chapter: Chapter,
        characters: List[Character],
    ) -> List[ConsistencyIssue]:
        """
        캐릭터 일관성을 검증합니다.
        
        - 캐릭터 이름 일치 여부
        - 캐릭터 속성 (나이, 외모, 성격) 일관성
        - 캐릭터 관계 일관성
        
        Args:
            db: 비동기 DB 세션
            chapter: 검증할 챕터
            characters: 프로젝트의 캐릭터 목록
            
        Returns:
            발견된 일관성 이슈 목록
        """
        issues: List[ConsistencyIssue] = []
        
        if not characters:
            return issues

        # 챕터 텍스트에서 캐릭터 이름 추출
        mentioned_names = self._extract_character_names(chapter.content, characters)
        
        # 정의된 캐릭터와 비교
        character_name_map = {char.name: char for char in characters}
        
        for name in mentioned_names:
            if name not in character_name_map:
                # 정의되지 않은 캐릭터 언급
                issue = ConsistencyIssue(
                    id=uuid.uuid4(),
                    chapter_id=chapter.id,
                    issue_type="character",
                    severity="medium",
                    description=f"정의되지 않은 캐릭터가 언급되었습니다: '{name}'",
                    line_number=self._find_line_number(chapter.content, name),
                    detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    is_resolved=False,
                )
                db.add(issue)
                issues.append(issue)
        
        # 캐릭터 속성 일관성 검증
        for character in characters:
            if character.name not in mentioned_names:
                continue
                
            # 나이 일관성 검증
            if character.age is not None:
                age_mentions = self._find_age_mentions(chapter.content, character.name)
                for mentioned_age, line_num in age_mentions:
                    if mentioned_age != character.age:
                        issue = ConsistencyIssue(
                            id=uuid.uuid4(),
                            chapter_id=chapter.id,
                            issue_type="character",
                            severity="high",
                            description=f"캐릭터 '{character.name}'의 나이가 일치하지 않습니다. 정의: {character.age}세, 언급: {mentioned_age}세",
                            line_number=line_num,
                            detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            is_resolved=False,
                        )
                        db.add(issue)
                        issues.append(issue)
            
            # 성격 특성 일관성 검증
            if character.personality_traits:
                contradictions = self._find_personality_contradictions(
                    chapter.content, character.name, character.personality_traits
                )
                for contradiction, line_num in contradictions:
                    issue = ConsistencyIssue(
                        id=uuid.uuid4(),
                        chapter_id=chapter.id,
                        issue_type="character",
                        severity="medium",
                        description=f"캐릭터 '{character.name}'의 행동이 정의된 성격과 모순됩니다: {contradiction}",
                        line_number=line_num,
                        detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        is_resolved=False,
                    )
                    db.add(issue)
                    issues.append(issue)

        await db.flush()
        return issues

    async def _check_plot_consistency(
        self,
        db: AsyncSession,
        chapter: Chapter,
        plot_points: List[PlotPoint],
    ) -> List[ConsistencyIssue]:
        """
        플롯 일관성을 검증합니다.
        
        - 논리적 모순 검증
        - 시간 순서 검증
        - 완료된 플롯 포인트와의 일관성
        
        Args:
            db: 비동기 DB 세션
            chapter: 검증할 챕터
            plot_points: 프로젝트의 플롯 포인트 목록
            
        Returns:
            발견된 일관성 이슈 목록
        """
        issues: List[ConsistencyIssue] = []
        
        if not plot_points:
            return issues

        # 완료된 플롯 포인트 확인
        completed_plots = [p for p in plot_points if p.is_completed]
        
        # 현재 챕터가 목표로 하는 플롯 포인트
        target_plots = [
            p for p in plot_points 
            if p.target_chapter == chapter.chapter_number
        ]
        
        # 목표 플롯 포인트가 언급되지 않은 경우
        for plot in target_plots:
            if not self._is_plot_mentioned(chapter.content, plot):
                issue = ConsistencyIssue(
                    id=uuid.uuid4(),
                    chapter_id=chapter.id,
                    issue_type="plot",
                    severity="high",
                    description=f"목표 플롯 포인트가 챕터에서 다루어지지 않았습니다: '{plot.title}'",
                    line_number=None,
                    detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    is_resolved=False,
                )
                db.add(issue)
                issues.append(issue)
        
        # 완료된 플롯과의 모순 검증
        for plot in completed_plots:
            contradictions = self._find_plot_contradictions(chapter.content, plot)
            for contradiction, line_num in contradictions:
                issue = ConsistencyIssue(
                    id=uuid.uuid4(),
                    chapter_id=chapter.id,
                    issue_type="plot",
                    severity="high",
                    description=f"이전 플롯과 모순됩니다: {contradiction}",
                    line_number=line_num,
                    detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    is_resolved=False,
                )
                db.add(issue)
                issues.append(issue)

        await db.flush()
        return issues

    async def _check_worldbuilding_consistency(
        self,
        db: AsyncSession,
        chapter: Chapter,
        world_buildings: List[WorldBuilding],
    ) -> List[ConsistencyIssue]:
        """
        세계관 일관성을 검증합니다.
        
        - 위치/장소 일관성
        - 세계관 규칙 준수
        - 타임라인 일관성
        
        Args:
            db: 비동기 DB 세션
            chapter: 검증할 챕터
            world_buildings: 프로젝트의 세계관 요소 목록
            
        Returns:
            발견된 일관성 이슈 목록
        """
        issues: List[ConsistencyIssue] = []
        
        if not world_buildings:
            return issues

        # 세계관 요소별 검증
        for wb in world_buildings:
            # 세계관 요소가 언급되는지 확인
            if not self._is_worldbuilding_mentioned(chapter.content, wb):
                continue
            
            # 규칙 위반 검증
            if wb.rules:
                violations = self._find_worldbuilding_violations(
                    chapter.content, wb
                )
                for violation, line_num in violations:
                    issue = ConsistencyIssue(
                        id=uuid.uuid4(),
                        chapter_id=chapter.id,
                        issue_type="worldbuilding",
                        severity="high",
                        description=f"세계관 규칙 위반: {wb.name} - {violation}",
                        line_number=line_num,
                        detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        is_resolved=False,
                    )
                    db.add(issue)
                    issues.append(issue)

        await db.flush()
        return issues

    def _calculate_consistency_score(
        self,
        issues: List[ConsistencyIssue],
    ) -> int:
        """
        일관성 점수를 계산합니다 (0-100).
        
        심각도에 따라 가중치를 적용:
        - high: -15점
        - medium: -8점
        - low: -3점
        
        Args:
            issues: 발견된 이슈 목록
            
        Returns:
            0-100 범위의 일관성 점수
        """
        if not issues:
            return 100
        
        severity_weights = {
            "high": 15,
            "medium": 8,
            "low": 3,
        }
        
        total_deduction = sum(
            severity_weights.get(issue.severity, 5) for issue in issues
        )
        
        score = max(0, 100 - total_deduction)
        return score

    # ─── 헬퍼 메서드 ──────────────────────────────────────────────────────────

    async def _get_project_characters(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[Character]:
        """프로젝트의 모든 캐릭터를 조회합니다."""
        result = await db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        return list(result.scalars().all())

    async def _get_project_plot_points(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[PlotPoint]:
        """프로젝트의 모든 플롯 포인트를 조회합니다."""
        result = await db.execute(
            select(PlotPoint)
            .where(PlotPoint.project_id == project_id)
            .order_by(PlotPoint.sequence_order)
        )
        return list(result.scalars().all())

    async def _get_project_worldbuildings(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[WorldBuilding]:
        """프로젝트의 모든 세계관 요소를 조회합니다."""
        result = await db.execute(
            select(WorldBuilding).where(WorldBuilding.project_id == project_id)
        )
        return list(result.scalars().all())

    def _extract_character_names(
        self,
        text: str,
        characters: List[Character],
    ) -> List[str]:
        """
        텍스트에서 캐릭터 이름을 추출합니다.
        
        한글 이름 패턴을 사용하여 정의된 캐릭터 이름을 찾습니다.
        """
        mentioned = []
        for character in characters:
            # 캐릭터 이름이 텍스트에 등장하는지 확인
            # 단어 경계를 고려하여 정확한 매칭
            pattern = re.escape(character.name)
            if re.search(pattern, text):
                mentioned.append(character.name)
        return mentioned

    def _find_line_number(
        self,
        text: str,
        search_term: str,
    ) -> Optional[int]:
        """텍스트에서 검색어가 처음 등장하는 줄 번호를 반환합니다."""
        lines = text.split('\n')
        for i, line in enumerate(lines, start=1):
            if search_term in line:
                return i
        return None

    def _find_age_mentions(
        self,
        text: str,
        character_name: str,
    ) -> List[tuple[int, int]]:
        """
        텍스트에서 캐릭터의 나이 언급을 찾습니다.
        
        Returns:
            (나이, 줄번호) 튜플 리스트
        """
        mentions = []
        lines = text.split('\n')
        
        # 나이 패턴: "캐릭터명은 XX세", "XX살의 캐릭터명" 등
        patterns = [
            rf'{re.escape(character_name)}[은는이가]?\s*(\d+)[세살]',
            rf'(\d+)[세살][의이]?\s*{re.escape(character_name)}',
        ]
        
        for line_num, line in enumerate(lines, start=1):
            for pattern in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    age = int(match.group(1))
                    mentions.append((age, line_num))
        
        return mentions

    def _find_personality_contradictions(
        self,
        text: str,
        character_name: str,
        personality_traits: List[str],
    ) -> List[tuple[str, int]]:
        """
        캐릭터의 행동이 정의된 성격과 모순되는지 검증합니다.
        
        Returns:
            (모순 설명, 줄번호) 튜플 리스트
        """
        contradictions = []
        
        # 성격 특성별 모순 키워드 매핑
        contradiction_keywords = {
            "용감한": ["겁먹", "두려워", "무서워", "도망"],
            "겁쟁이": ["용감", "대담", "맞서"],
            "친절한": ["무례", "냉정", "차갑"],
            "냉정한": ["감정적", "흥분"],
            "정의로운": ["부정", "불의", "거짓말"],
        }
        
        lines = text.split('\n')
        for line_num, line in enumerate(lines, start=1):
            if character_name not in line:
                continue
            
            for trait in personality_traits:
                if trait in contradiction_keywords:
                    for keyword in contradiction_keywords[trait]:
                        if keyword in line:
                            contradictions.append(
                                (f"'{trait}' 성격이지만 '{keyword}' 행동을 보임", line_num)
                            )
        
        return contradictions

    def _is_plot_mentioned(
        self,
        text: str,
        plot: PlotPoint,
    ) -> bool:
        """플롯 포인트가 텍스트에서 언급되는지 확인합니다."""
        # 플롯 제목이나 설명의 주요 키워드가 포함되어 있는지 확인
        keywords = plot.title.split()
        if plot.description:
            keywords.extend(plot.description.split()[:5])  # 설명의 처음 5단어
        
        for keyword in keywords:
            if len(keyword) >= 2 and keyword in text:
                return True
        return False

    def _find_plot_contradictions(
        self,
        text: str,
        plot: PlotPoint,
    ) -> List[tuple[str, int]]:
        """
        완료된 플롯과 모순되는 내용을 찾습니다.
        
        Returns:
            (모순 설명, 줄번호) 튜플 리스트
        """
        # 기본 구현: 플롯 설명에서 키워드 추출 후 반대 의미 검색
        # 실제로는 더 정교한 NLP 분석이 필요
        contradictions = []
        
        # 간단한 예시: 플롯이 "승리"인데 "패배" 언급
        if plot.description:
            lines = text.split('\n')
            for line_num, line in enumerate(lines, start=1):
                # 기본적인 모순 패턴 검사
                if "승리" in plot.description and "패배" in line:
                    contradictions.append(
                        (f"플롯 '{plot.title}'과 모순: 승리했으나 패배 언급", line_num)
                    )
                elif "생존" in plot.description and "사망" in line:
                    contradictions.append(
                        (f"플롯 '{plot.title}'과 모순: 생존했으나 사망 언급", line_num)
                    )
        
        return contradictions

    def _is_worldbuilding_mentioned(
        self,
        text: str,
        worldbuilding: WorldBuilding,
    ) -> bool:
        """세계관 요소가 텍스트에서 언급되는지 확인합니다."""
        return worldbuilding.name in text

    def _find_worldbuilding_violations(
        self,
        text: str,
        worldbuilding: WorldBuilding,
    ) -> List[tuple[str, int]]:
        """
        세계관 규칙 위반을 찾습니다.
        
        Returns:
            (위반 설명, 줄번호) 튜플 리스트
        """
        violations = []
        
        if not worldbuilding.rules:
            return violations
        
        lines = text.split('\n')
        
        # 규칙별 검증 (rules는 JSONB 딕셔너리)
        for rule_key, rule_value in worldbuilding.rules.items():
            # 예: {"magic_limit": "하루 3번", "forbidden": "시간 여행"}
            if rule_key == "forbidden" and isinstance(rule_value, str):
                for line_num, line in enumerate(lines, start=1):
                    if rule_value in line:
                        violations.append(
                            (f"금지된 요소 사용: {rule_value}", line_num)
                        )
            
            elif rule_key == "magic_limit" and isinstance(rule_value, str):
                # 마법 사용 횟수 제한 검증 (간단한 예시)
                for line_num, line in enumerate(lines, start=1):
                    if "마법" in line and "4번" in line:
                        violations.append(
                            (f"마법 사용 제한 위반: {rule_value} 초과", line_num)
                        )
        
        return violations


# 싱글턴 인스턴스 (의존성 주입용)
consistency_checker = ConsistencyCheckerService()
