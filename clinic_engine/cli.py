import fire
from loguru import logger

from .analytics import AnalyticsTracker
from .checker import QualityChecker
from .config import config
from .db import Database
from .generator import ContentGenerator
from .keyword import KeywordEngine
from .industries import get_profile
from .models import ArticleStatus, ContentType
from .publisher import FilePublisher
from .review import ReviewManager

try:
    from .rag import KnowledgeBase
except ImportError:
    KnowledgeBase = None


class KeywordCLI:
    """关键词研究模块"""

    def __init__(self):
        self.engine = KeywordEngine()

    def research(self, specialty="general", seed=None, content_type="seo_article", limit=20):
        """
        研究关键词并生成选题队列

        Args:
            specialty: 专科类型 (general/tcm/dental/dermatology/gynecology)
            seed: 种子关键词
            content_type: 内容类型 (seo_article/wechat/xiaohongshu)
            limit: 生成数量
        """
        topics = self.engine.research(specialty, seed, content_type, limit)
        print(f"\n已生成 {len(topics)} 个关键词:")
        print(f"{'ID':<6}{'关键词':<25}{'搜索量':<10}{'竞争度':<8}{'优先级':<10}")
        print("-" * 60)
        for t in topics:
            print(f"{t.id:<6}{t.keyword:<25}{t.search_volume:<10}{t.competition:<8}{t.priority_score:<10}")
        return topics

    def list(self, status=None, limit=50):
        """
        列出关键词

        Args:
            status: 状态筛选 (queued/in_progress/done)
            limit: 显示数量
        """
        topics = self.engine.list_topics(status=status, limit=limit)
        print(f"\n关键词列表 ({len(topics)} 条):")
        print(f"{'ID':<6}{'关键词':<25}{'状态':<12}{'优先级':<10}")
        print("-" * 55)
        for t in topics:
            print(f"{t.id:<6}{t.keyword:<25}{t.status:<12}{t.priority_score:<10}")
        return topics


class GenerateCLI:
    """内容生成模块"""

    def __init__(self):
        self.generator = ContentGenerator()

    def article(self, topic_id, content_type=None):
        """
        根据关键词生成文章

        Args:
            topic_id: 关键词ID
            content_type: 内容类型 (seo_article/wechat/xiaohongshu)，默认使用关键词设定
        """
        db = Database()
        topic = db.get_topic(topic_id)
        if not topic:
            print(f"未找到关键词: id={topic_id}")
            return None

        ct = ContentType(content_type) if content_type else topic.content_type
        article = self.generator.generate_article(topic, ct)
        print(f"\n文章已生成:")
        print(f"  ID: {article.id}")
        print(f"  标题: {article.title}")
        print(f"  类型: {article.content_type.value}")
        print(f"  字数: {len(article.content)}")
        print(f"  状态: {article.status.value}")
        return article

    def batch(self, specialty="general", content_type="seo_article", limit=3):
        """
        批量生成文章

        Args:
            specialty: 专科类型
            content_type: 内容类型
            limit: 生成数量
        """
        articles = self.generator.generate_batch(specialty, content_type, limit)
        print(f"\n批量生成完成: {len(articles)} 篇文章")
        for a in articles:
            print(f"  [{a.id}] {a.title} ({a.content_type.value})")
        return articles


class CheckCLI:
    """质量检查模块"""

    def __init__(self):
        self.checker = QualityChecker()

    def article(self, article_id):
        """
        检查单篇文章质量

        Args:
            article_id: 文章ID
        """
        db = Database()
        article = db.get_article(article_id)
        if not article:
            print(f"未找到文章: id={article_id}")
            return None

        result = self.checker.check_article(article)
        status = "通过" if result.passed else "不通过"
        print(f"\n质量检查结果: {status}")
        print(f"文章: {article.title}")
        if result.issues:
            print(f"\n问题 ({len(result.issues)} 个):")
            for issue in result.issues:
                icon = {"error": "X", "warning": "!", "info": "i"}.get(issue.severity, "?")
                print(f"  [{icon}] [{issue.rule}] {issue.message}")
                if issue.location:
                    print(f"       位置: {issue.location}")
        else:
            print("无问题发现")
        return result

    def batch(self, status="draft", limit=50):
        """
        批量检查文章质量

        Args:
            status: 文章状态
            limit: 检查数量
        """
        results = self.checker.check_batch(status, limit)
        print(f"\n批量检查完成: {len(results)} 篇文章")
        for article, result in results:
            status_str = "PASS" if result.passed else "FAIL"
            errors = sum(1 for i in result.issues if i.severity == "error")
            warnings = sum(1 for i in result.issues if i.severity == "warning")
            print(f"  [{status_str}] [{article.id}] {article.title} (errors={errors}, warnings={warnings})")
        return results


class ReviewCLI:
    """内容审核模块"""

    def __init__(self):
        self.manager = ReviewManager()
        self._profile = get_profile()

    def list(self, status="quality_checked", limit=50):
        """列出待审核文章"""
        articles = self.manager.list_articles(status=status, limit=limit)
        print(f"\n文章列表 ({len(articles)} 篇):")
        print(f"{'ID':<6}{'标题':<40}{'状态':<18}{'创建时间':<20}")
        print("-" * 85)
        for a in articles:
            title = a.title[:38] + ".." if len(a.title) > 38 else a.title
            print(f"{a.id:<6}{title:<40}{a.status.value:<18}{a.created_at.strftime('%Y-%m-%d %H:%M'):<20}")
        return articles

    def approve(self, article_id, reviewer=None, notes=None):
        """审核通过文章"""
        reviewer = reviewer or self._profile.reviewer_role
        article = self.manager.approve(article_id, reviewer, notes)
        print(f"文章已审核通过: [{article.id}] {article.title}")
        return article

    def reject(self, article_id, reviewer=None, notes=""):
        """打回文章（返回草稿状态）"""
        reviewer = reviewer or self._profile.reviewer_role
        article = self.manager.reject(article_id, reviewer, notes)
        print(f"文章已打回: [{article.id}] {article.title}")
        print(f"原因: {notes}")
        return article

    def notes(self, article_id, notes=""):
        """
        添加审核备注

        Args:
            article_id: 文章ID
            notes: 备注内容
        """
        article = self.manager.add_notes(article_id, notes)
        print(f"已添加备注: [{article.id}]")
        return article


class PublishCLI:
    """内容发布模块"""

    def __init__(self):
        self.publisher = FilePublisher()

    def file(self, article_id, output_dir=None):
        """
        发布文章到本地文件

        Args:
            article_id: 文章ID
            output_dir: 输出目录
        """
        db = Database()
        article = db.get_article(article_id)
        if not article:
            print(f"未找到文章: id={article_id}")
            return None

        result = self.publisher.publish(article, output_dir)
        print(f"文章已发布: {result['path']}")
        return result


class AnalyticsCLI:
    """数据分析模块"""

    def __init__(self):
        self.tracker = AnalyticsTracker()

    def summary(self):
        """查看发布统计摘要"""
        data = self.tracker.get_summary()
        print(f"\n发布统计:")
        print(f"  已发布文章总数: {data['total_published']}")
        if data['by_content_type']:
            print(f"  按内容类型:")
            for ct, count in data['by_content_type'].items():
                print(f"    {ct}: {count}")
        if data['by_status']:
            print(f"  按状态:")
            for st, count in data['by_status'].items():
                print(f"    {st}: {count}")
        return data


class WorkflowCLI:
    """完整流水线"""

    def __init__(self):
        self.keyword_engine = KeywordEngine()
        self.generator = ContentGenerator()
        self.checker = QualityChecker()
        self.publisher = FilePublisher()
        self.analytics = AnalyticsTracker()

    def run(self, specialty="general", content_type="seo_article", limit=3, auto_check=True):
        """
        运行完整内容生产流水线：关键词研究 → 内容生成 → 质量检查 → 发布

        Args:
            specialty: 专科类型
            content_type: 内容类型
            limit: 生成数量
            auto_check: 是否自动质量检查
        """
        logger.info("=" * 60)
        logger.info("开始执行内容生产流水线")
        logger.info("=" * 60)

        # Step 1: Keyword research
        logger.info("Step 1: 关键词研究...")
        topics = self.keyword_engine.research(specialty, content_type=content_type, limit=limit)
        logger.info(f"  生成 {len(topics)} 个关键词")

        # Step 2: Generate articles
        logger.info("Step 2: 内容生成...")
        articles = self.generator.generate_batch(specialty, content_type, limit)
        logger.info(f"  生成 {len(articles)} 篇文章")

        # Step 3: Quality check
        if auto_check:
            logger.info("Step 3: 质量检查...")
            for article in articles:
                result = self.checker.check_article(article)
                status_str = "通过" if result.passed else "需修改"
                logger.info(f"  [{article.id}] {article.title}: {status_str}")

        logger.success("=" * 60)
        _profile = get_profile()
        logger.success(f"流水线完成: {len(articles)} 篇文章待{_profile.reviewer_role}审核")
        logger.success("使用 'clinic-engine review list' 查看待审核文章")
        logger.success("=" * 60)

        return articles

    def daily(self, specialty=None, content_type="seo_article", limit=1):
        """
        每日定时任务：生成一篇新文章

        Args:
            specialty: 专科类型，默认使用当前行业配置
            content_type: 内容类型
            limit: 生成数量
        """
        import schedule
        import time

        profile = get_profile()
        specialty = specialty or profile.default_specialty.value

        def job():
            self.run(specialty=specialty, content_type=content_type, limit=limit)

        schedule.every().day.at("08:00").do(job)
        logger.info("定时任务已启动，每天 08:00 自动生成文章")
        logger.info("按 Ctrl+C 停止")
        while True:
            schedule.run_pending()
            time.sleep(60)


class KnowledgeCLI:
    """知识库管理（RAG）"""

    def __init__(self):
        if not KnowledgeBase:
            raise ImportError("请安装 chromadb: pip install chromadb")
        self.kb = KnowledgeBase()

    def ingest(self, path=None):
        """
        摄入知识文档

        Args:
            path: 文件或目录路径，默认使用内置 knowledge 目录
        """
        if path:
            from pathlib import Path
            p = Path(path)
            if p.is_dir():
                count = self.kb.ingest_directory(p)
            else:
                count = self.kb.ingest_file(p)
        else:
            count = self.kb.ingest_directory()
        print(f"已摄入 {count} 个文档块")

    def query(self, question, n=3):
        """
        检索知识库

        Args:
            question: 查询问题
            n: 返回条数
        """
        results = self.kb.query(question, n_results=n)
        print(f"\n检索结果 ({len(results)} 条):\n")
        for i, r in enumerate(results, 1):
            print(f"--- [{i}] 来源: {r['source']} (相关度: {r['relevance']}) ---")
            print(r['content'][:300])
            print()

    def grep(self, keyword):
        """
        关键词精确搜索知识库

        Args:
            keyword: 搜索关键词
        """
        results = self.kb.grep(keyword)
        print(f"\ngrep「{keyword}」匹配 {len(results)} 处:\n")
        for i, r in enumerate(results, 1):
            print(f"--- [{i}] {r['source']} (chunk #{r['chunk_index']}) ---")
            # 高亮匹配部分
            content = r['content']
            highlighted = content.replace(keyword, f">>>{keyword}<<<")
            print(highlighted[:400])
            print()

    def status(self):
        """查看知识库状态"""
        count = self.kb.count()
        sources = self.kb.list_sources()
        print(f"\n知识库状态:")
        print(f"  文档块总数: {count}")
        print(f"  文档来源: {', '.join(sources) if sources else '无'}")

    def clear(self):
        """清空知识库"""
        self.kb.clear()
        print("知识库已清空")


class VerifyCLI:
    """声明验证模块（ReAct Agent）"""

    def __init__(self):
        from .verifier import ReActVerifier
        kb = KnowledgeBase() if KnowledgeBase else None
        self.verifier = ReActVerifier(kb=kb, use_online=True)

    def article(self, article_id, online=True):
        """
        验证文章中的声明

        使用 ReAct Agent 逐条验证声明：
        1. Thought: 分析声明，确定搜索关键词
        2. Action: grep 知识库 / 联网搜索
        3. Observation: 评估结果
        4. 循环直到有足够证据

        Args:
            article_id: 文章ID
            online: 是否启用联网搜索
        """
        from .verifier import ReActVerifier
        db = Database()
        article = db.get_article(article_id)
        if not article:
            print(f"未找到文章: id={article_id}")
            return None

        kb = KnowledgeBase() if KnowledgeBase else None
        verifier = ReActVerifier(kb=kb, use_online=online)
        report = verifier.verify_article(article.title, article.content)
        print(report.summary())
        print()
        for r in report.results:
            status_icon = {"verified": "✓", "partially": "~", "unverified": "?",
                           "contradicted": "X", "needs_review": "!"}.get(r.status.value, "?")
            print(f"  [{status_icon}] {r.category}: {r.claim[:60]}...")
            print(f"      置信度: {r.confidence:.0%} | {r.reasoning[:80]}")
            if r.sources:
                print(f"      来源: {', '.join(r.sources[:2])}")
            print()
        return report

    def text(self, title, content):
        """
        验证任意文本中的声明

        Args:
            title: 文章标题
            content: 文章内容
        """
        from .verifier import ReActVerifier
        kb = KnowledgeBase() if KnowledgeBase else None
        verifier = ReActVerifier(kb=kb, use_online=True)
        report = verifier.verify_article(title, content)
        print(report.summary())
        print()
        for r in report.results:
            status_icon = {"verified": "✓", "partially": "~", "unverified": "?",
                           "contradicted": "X", "needs_review": "!"}.get(r.status.value, "?")
            print(f"  [{status_icon}] {r.category}: {r.claim[:60]}...")
            print(f"      置信度: {r.confidence:.0%} | {r.reasoning[:80]}")
            print()
        return report


class DemoCLI:
    """一键体验 — 零配置跑完全流程"""

    def run(self, topic=None, output_dir=None):
        """
        一键体验完整内容生产流水线

        自动完成：知识库加载 → 文章生成 → 质量检查 → 声明验证 → 输出文件
        无需任何配置，直接运行即可。

        Args:
            topic: 文章主题关键词，默认使用行业种子词
            output_dir: 输出目录，默认 ./demo_output
        """
        import os
        from pathlib import Path

        profile = get_profile()
        topic = topic or (profile.seed_keywords.get(profile.default_specialty.value, ["通用"])[0])
        output_dir = output_dir or "./demo_output"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print(f"  {profile.brand_name} — 一键体验")
        print("=" * 60)

        # Step 1: 加载知识库
        print("\n[1/5] 加载知识库...")
        kb = KnowledgeBase() if KnowledgeBase else None
        if kb:
            if kb.count() == 0:
                print("  知识库为空，自动加载内置参考文档...")
                kb.ingest_directory()
            print(f"  知识库就绪：{kb.count()} 个文档块，{len(kb.list_sources())} 个来源")

        # Step 2: 生成文章
        print(f"\n[2/5] 生成文章：{topic}")
        ke = KeywordEngine()
        topics = ke.research(profile.default_specialty.value, seed=topic, content_type="seo_article", limit=1)
        t = topics[0]

        gen = ContentGenerator()
        article = gen.generate_article(t, ContentType.SEO_ARTICLE)
        print(f"  标题: {article.title}")
        print(f"  字数: {len(article.content)}")

        # Step 3: 质量检查
        print("\n[3/5] 质量检查（合规检测）...")
        checker = QualityChecker()
        result = checker.check_article(article)
        errors = [i for i in result.issues if i.severity == "error"]
        warnings = [i for i in result.issues if i.severity == "warning"]
        status = "通过" if result.passed else "不通过"
        print(f"  结果: {status} (错误: {len(errors)}, 警告: {len(warnings)})")
        for e in errors:
            print(f"    [X] {e.rule}: {e.message}")

        # Step 4: 声明验证
        print(f"\n[4/5] 声明验证（ReAct Agent）...")
        from .verifier import ReActVerifier
        verifier = ReActVerifier(kb=kb, use_online=False)
        report = verifier.verify_article(article.title, article.content)
        print(f"  总声明: {report.total_claims}")
        print(f"  已验证: {report.verified} | 部分验证: {report.partially}")
        print(f"  未验证: {report.unverified} | 需审核: {report.needs_review}")
        print(f"  验证通过率: {report.pass_rate:.0%}")

        # Step 5: 保存输出
        print(f"\n[5/5] 保存文件到 {output_dir}/")
        # 保存文章
        article_path = os.path.join(output_dir, "article.md")
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(f"# {article.title}\n\n")
            f.write(article.content)
        print(f"  文章: {article_path}")

        # 保存验证报告
        report_path = os.path.join(output_dir, "verification_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 验证报告\n\n")
            f.write(f"文章: {article.title}\n\n")
            f.write(report.summary())
            f.write("\n\n## 详细结果\n\n")
            for r in report.results:
                icon = {"verified": "v", "partially": "~", "unverified": "?",
                        "contradicted": "X", "needs_review": "!"}.get(r.status.value, "?")
                f.write(f"- [{icon}] **{r.category}** (置信度: {r.confidence:.0%})\n")
                f.write(f"  - 声明: {r.claim[:80]}...\n")
                f.write(f"  - 判断: {r.reasoning[:100]}\n")
                if r.sources:
                    f.write(f"  - 来源: {', '.join(r.sources[:2])}\n")
                f.write("\n")
        print(f"  验证报告: {report_path}")

        # 保存质量报告
        quality_path = os.path.join(output_dir, "quality_report.md")
        with open(quality_path, "w", encoding="utf-8") as f:
            f.write(f"# 质量检查报告\n\n")
            f.write(f"文章: {article.title}\n")
            f.write(f"结果: {status}\n\n")
            if result.issues:
                for issue in result.issues:
                    f.write(f"- [{issue.severity}] [{issue.rule}] {issue.message}\n")
            else:
                f.write("无问题发现\n")
        print(f"  质量报告: {quality_path}")

        print("\n" + "=" * 60)
        print("  体验完成！查看输出文件了解效果。")
        print("=" * 60)

        return {"article_id": article.id, "output_dir": output_dir}


class ClinicEngine:
    """AI 内容引擎 — 多行业内容生产系统

    模块:
        demo       - 一键体验（零配置跑完全流程）
        keyword    - 关键词研究
        generate   - 内容生成
        check      - 质量检查
        review     - 审核工作流
        publish    - 内容发布
        analytics  - 数据分析
        knowledge  - 知识库管理（RAG）
        verify     - 声明验证（ReAct Agent）
        workflow   - 完整流水线
    """

    def __init__(self):
        self._keyword = KeywordCLI()
        self._generate = GenerateCLI()
        self._check = CheckCLI()
        self._review = ReviewCLI()
        self._publish = PublishCLI()
        self._analytics = AnalyticsCLI()
        self._workflow = WorkflowCLI()
        self._knowledge = KnowledgeCLI() if KnowledgeBase else None
        self._verify = VerifyCLI()
        self._demo = DemoCLI()

    @property
    def keyword(self):
        return self._keyword

    @property
    def generate(self):
        return self._generate

    @property
    def check(self):
        return self._check

    @property
    def review(self):
        return self._review

    @property
    def publish(self):
        return self._publish

    @property
    def analytics(self):
        return self._analytics

    @property
    def workflow(self):
        return self._workflow

    @property
    def knowledge(self):
        return self._knowledge

    @property
    def verify(self):
        return self._verify

    @property
    def demo(self):
        return self._demo


def main():
    fire.Fire(ClinicEngine)


if __name__ == "__main__":
    main()
