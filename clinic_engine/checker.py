import re
from datetime import datetime

from loguru import logger

from .config import config
from .db import Database
from .industries import get_profile
from .models import Article, ArticleStatus, QualityIssue, QualityResult


class QualityChecker:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.profile = get_profile()

    def check_article(self, article: Article) -> QualityResult:
        logger.info(f"质量检查: id={article.id}, 标题={article.title}")

        issues: list[QualityIssue] = []

        issues.extend(self._check_advertising_law(article.content))
        issues.extend(self._check_disclaimer(article.content))
        issues.extend(self._check_content_length(article.content, article.title))
        issues.extend(self._check_structure(article.content))
        issues.extend(self._check_scope(article.content, article.specialty))

        passed = not any(i.severity == "error" for i in issues)

        result = QualityResult(passed=passed, issues=issues)

        if article.id:
            self.db.update_article_status(
                article.id,
                ArticleStatus.QUALITY_CHECKED,
                quality_result=result,
            )

        status_str = "通过" if passed else "不通过"
        error_count = sum(1 for i in issues if i.severity == "error")
        warn_count = sum(1 for i in issues if i.severity == "warning")
        logger.info(f"质量检查结果: {status_str}, errors={error_count}, warnings={warn_count}")

        return result

    def check_batch(self, status: str = "draft", limit: int = 50) -> list[tuple[Article, QualityResult]]:
        from .models import ArticleStatus as AS

        articles = self.db.get_articles_by_status(AS.DRAFT, limit=limit)
        results = []
        for article in articles:
            qr = self.check_article(article)
            results.append((article, qr))
        return results

    def _check_advertising_law(self, content: str) -> list[QualityIssue]:
        issues = []
        for rule in self.profile.ad_law_patterns:
            matches = list(re.finditer(rule.pattern, content))
            for m in matches:
                start = max(0, m.start() - 10)
                end = min(len(content), m.end() + 10)
                context = content[start:end].replace("\n", " ")
                issues.append(QualityIssue(
                    rule="advertising_law",
                    severity=rule.severity,
                    message=f"{rule.message}: '{m.group()}'",
                    location=f"...{context}...",
                ))
        return issues

    def _check_disclaimer(self, content: str) -> list[QualityIssue]:
        has_disclaimer = any(re.search(p, content) for p in self.profile.disclaimer_patterns)
        if not has_disclaimer:
            return [QualityIssue(
                rule="disclaimer_missing",
                severity="warning",
                message="文章缺少免责声明",
            )]
        return []

    def _check_content_length(self, content: str, title: str) -> list[QualityIssue]:
        issues = []
        if len(content) < 300:
            issues.append(QualityIssue(
                rule="content_too_short",
                severity="warning",
                message=f"文章内容过短（{len(content)}字），建议至少500字以上",
            ))
        if not title or len(title) < 5:
            issues.append(QualityIssue(
                rule="title_too_short",
                severity="error",
                message="文章标题缺失或过短",
            ))
        return issues

    def _check_structure(self, content: str) -> list[QualityIssue]:
        issues = []
        has_headers = bool(re.search(r"^#{1,3}\s", content, re.MULTILINE))
        if not has_headers and len(content) > 500:
            issues.append(QualityIssue(
                rule="no_structure",
                severity="info",
                message="文章缺少标题结构（H1/H2/H3），建议添加小标题提升可读性",
            ))
        return issues

    def _check_scope(self, content: str, specialty: str) -> list[QualityIssue]:
        terms = self.profile.out_of_scope_terms(specialty)
        issues = []
        for term in terms:
            if term in content:
                issues.append(QualityIssue(
                    rule="scope_check",
                    severity="warning",
                    message=f"内容涉及'{term}'，可能超出业务范围，请确认是否保留",
                ))
        return issues
