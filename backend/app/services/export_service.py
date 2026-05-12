"""
소설 내보내기 서비스

PDF, EPUB, TXT 형식으로 소설을 내보냅니다.
"""
import io
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ebooklib import epub
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chapter import Chapter
from backend.app.models.project import Project
from backend.app.schemas.export import PDFFormatOptions

logger = logging.getLogger(__name__)


class ExportService:
    """소설 내보내기 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.export_dir = Path(tempfile.gettempdir()) / "novel_exports"
        self.export_dir.mkdir(exist_ok=True)
        logger.info(f"Export directory: {self.export_dir}")

    async def export_to_pdf(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        options: Optional[PDFFormatOptions] = None,
    ) -> Path:
        """
        프로젝트를 PDF로 내보냅니다.

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            options: PDF 포맷 옵션

        Returns:
            생성된 PDF 파일 경로
        """
        if options is None:
            options = PDFFormatOptions()

        # 프로젝트 및 챕터 조회
        project = await self._get_project(db, project_id)
        chapters = await self._get_chapters(db, project_id)

        if not chapters:
            raise ValueError("내보낼 챕터가 없습니다.")

        # PDF 파일 경로
        filename = f"{project.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        # 파일명에서 특수문자 제거
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        output_path = self.export_dir / filename

        # PDF 생성
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            topMargin=options.margin_top * cm,
            bottomMargin=options.margin_bottom * cm,
            leftMargin=options.margin_left * cm,
            rightMargin=options.margin_right * cm,
        )

        # 스타일 설정
        styles = self._create_pdf_styles(options)
        story = []

        # 제목 페이지
        story.append(Paragraph(project.title, styles["Title"]))
        story.append(Spacer(1, 1 * cm))
        if project.genre:
            story.append(Paragraph(f"장르: {project.genre}", styles["Normal"]))
            story.append(Spacer(1, 0.5 * cm))
        if project.description:
            story.append(Paragraph(project.description, styles["Normal"]))
        story.append(PageBreak())

        # 목차 (옵션)
        if options.include_toc:
            story.append(Paragraph("목차", styles["Heading1"]))
            story.append(Spacer(1, 0.5 * cm))
            for chapter in chapters:
                toc_entry = f"챕터 {chapter.chapter_number}"
                if chapter.title:
                    toc_entry += f": {chapter.title}"
                story.append(Paragraph(toc_entry, styles["TOC"]))
            story.append(PageBreak())

        # 챕터 내용
        for chapter in chapters:
            # 챕터 제목
            chapter_title = f"챕터 {chapter.chapter_number}"
            if chapter.title:
                chapter_title += f": {chapter.title}"
            story.append(Paragraph(chapter_title, styles["Heading1"]))
            story.append(Spacer(1, 0.5 * cm))

            # 챕터 내용 (단락별로 분리)
            paragraphs = chapter.content.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    # 줄바꿈을 <br/>로 변환
                    para_html = para.replace("\n", "<br/>")
                    story.append(Paragraph(para_html, styles["BodyText"]))
                    story.append(Spacer(1, 0.3 * cm))

            story.append(PageBreak())

        # PDF 빌드
        doc.build(story)
        logger.info(f"PDF 생성 완료: {output_path}")
        return output_path

    async def export_to_epub(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> Path:
        """
        프로젝트를 EPUB로 내보냅니다.

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID

        Returns:
            생성된 EPUB 파일 경로
        """
        # 프로젝트 및 챕터 조회
        project = await self._get_project(db, project_id)
        chapters = await self._get_chapters(db, project_id)

        if not chapters:
            raise ValueError("내보낼 챕터가 없습니다.")

        # EPUB 생성
        book = epub.EpubBook()

        # 메타데이터 설정
        book.set_identifier(str(project.id))
        book.set_title(project.title)
        book.set_language("ko")
        if project.genre:
            book.add_metadata("DC", "subject", project.genre)

        # 챕터 추가
        epub_chapters = []
        for chapter in chapters:
            # 챕터 제목
            chapter_title = f"챕터 {chapter.chapter_number}"
            if chapter.title:
                chapter_title += f": {chapter.title}"

            # 챕터 내용 HTML 생성
            content_html = f"<h1>{chapter_title}</h1>\n"
            paragraphs = chapter.content.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    # 줄바꿈을 <br/>로 변환
                    para_html = para.replace("\n", "<br/>")
                    content_html += f"<p>{para_html}</p>\n"

            # EPUB 챕터 생성
            epub_chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f"chapter_{chapter.chapter_number}.xhtml",
                lang="ko",
            )
            epub_chapter.content = content_html
            book.add_item(epub_chapter)
            epub_chapters.append(epub_chapter)

        # 목차 설정
        book.toc = tuple(epub_chapters)

        # Spine 설정 (읽기 순서)
        book.spine = ["nav"] + epub_chapters

        # NCX 및 Nav 추가
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # 기본 CSS 추가
        style = """
        body { font-family: 'Noto Sans KR', sans-serif; line-height: 1.6; }
        h1 { text-align: center; margin-bottom: 2em; }
        p { text-indent: 1em; margin-bottom: 1em; }
        """
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style,
        )
        book.add_item(nav_css)

        # EPUB 파일 저장
        filename = f"{project.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.epub"
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        output_path = self.export_dir / filename

        epub.write_epub(str(output_path), book, {})
        logger.info(f"EPUB 생성 완료: {output_path}")
        return output_path

    async def export_to_txt(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> Path:
        """
        프로젝트를 TXT로 내보냅니다.

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID

        Returns:
            생성된 TXT 파일 경로
        """
        # 프로젝트 및 챕터 조회
        project = await self._get_project(db, project_id)
        chapters = await self._get_chapters(db, project_id)

        if not chapters:
            raise ValueError("내보낼 챕터가 없습니다.")

        # TXT 파일 생성
        filename = f"{project.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        output_path = self.export_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            # 제목
            f.write(f"{project.title}\n")
            f.write("=" * 50 + "\n\n")

            # 메타데이터
            if project.genre:
                f.write(f"장르: {project.genre}\n")
            if project.description:
                f.write(f"설명: {project.description}\n")
            f.write("\n" + "=" * 50 + "\n\n")

            # 챕터 내용
            for chapter in chapters:
                # 챕터 제목
                chapter_title = f"챕터 {chapter.chapter_number}"
                if chapter.title:
                    chapter_title += f": {chapter.title}"
                f.write(f"\n\n{chapter_title}\n")
                f.write("-" * 50 + "\n\n")

                # 챕터 내용
                f.write(chapter.content)
                f.write("\n\n")

        logger.info(f"TXT 생성 완료: {output_path}")
        return output_path

    def _create_pdf_styles(self, options: PDFFormatOptions) -> dict:
        """
        PDF 스타일을 생성합니다.

        Args:
            options: PDF 포맷 옵션

        Returns:
            스타일 딕셔너리
        """
        styles = getSampleStyleSheet()

        # 기본 폰트는 Helvetica 사용 (한글 폰트는 시스템에 설치되어 있어야 함)
        # 실제 운영 환경에서는 Noto Sans KR 폰트 파일을 포함해야 함
        font_name = "Helvetica"  # 기본 폰트

        # 제목 스타일
        styles.add(
            ParagraphStyle(
                name="Title",
                parent=styles["Title"],
                fontName=font_name,
                fontSize=options.font_size + 8,
                alignment=1,  # 중앙 정렬
                spaceAfter=30,
            )
        )

        # 헤딩 스타일
        styles.add(
            ParagraphStyle(
                name="Heading1",
                parent=styles["Heading1"],
                fontName=font_name,
                fontSize=options.font_size + 4,
                spaceAfter=12,
            )
        )

        # 본문 스타일
        styles.add(
            ParagraphStyle(
                name="BodyText",
                parent=styles["Normal"],
                fontName=font_name,
                fontSize=options.font_size,
                leading=options.font_size * options.line_spacing,
                firstLineIndent=options.font_size,
            )
        )

        # 목차 스타일
        styles.add(
            ParagraphStyle(
                name="TOC",
                parent=styles["Normal"],
                fontName=font_name,
                fontSize=options.font_size,
                leftIndent=20,
                spaceAfter=6,
            )
        )

        return styles

    async def _get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project:
        """프로젝트를 조회합니다."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return project

    async def _get_chapters(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> List[Chapter]:
        """프로젝트의 모든 챕터를 조회합니다 (삭제되지 않은 챕터만)."""
        result = await db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id, Chapter.is_deleted.is_(False))
            .order_by(Chapter.chapter_number)
        )
        return list(result.scalars().all())


# 싱글톤 인스턴스
export_service = ExportService()
