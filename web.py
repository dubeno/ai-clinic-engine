"""极简 Web 界面 — 机构零门槛使用

启动: python web.py 或双击 start.bat
访问: http://localhost:8080
"""

import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# 确保项目根目录在 path 中
os.chdir(Path(__file__).parent)

from clinic_engine.checker import QualityChecker
from clinic_engine.generator import ContentGenerator
from clinic_engine.industries import get_profile
from clinic_engine.keyword import KeywordEngine
from clinic_engine.models import ArticleStatus, ContentType

try:
    from clinic_engine.rag import KnowledgeBase
except ImportError:
    KnowledgeBase = None

try:
    from clinic_engine.verifier import ReActVerifier
except ImportError:
    ReActVerifier = None


class Handler(SimpleHTTPRequestHandler):
    """处理网页请求"""

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._serve_index()
        elif path == "/api/profile":
            self._api_profile()
        elif path == "/api/topics":
            self._api_topics()
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        if path == "/api/generate":
            self._api_generate(body)
        elif path == "/api/check":
            self._api_check(body)
        elif path == "/api/verify":
            self._api_verify(body)
        elif path == "/api/publish":
            self._api_publish(body)
        else:
            self.send_error(404)

    def _serve_index(self):
        html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    def _api_profile(self):
        """返回当前行业 profile 元数据"""
        profile = get_profile()
        specialties = {}
        for k, v in profile.specialty_names.items():
            specialties[k] = v
        self._json_response({
            "industry_id": profile.industry_id,
            "industry_name": profile.industry_name,
            "brand_name": profile.brand_name,
            "reviewer_role": profile.reviewer_role,
            "default_specialty": profile.default_specialty.value,
            "specialty_names": specialties,
            "default_disclaimer": profile.default_disclaimer,
        })

    def _api_topics(self):
        """列出数据库中已有关键词"""
        from clinic_engine.db import Database
        db = Database()
        topics = db.get_pending_topics(limit=20)
        result = [{"id": t.id, "keyword": t.keyword, "status": t.status} for t in topics]
        self._json_response(result)

    def _api_generate(self, body):
        """生成文章"""
        params = json.loads(body) if body else {}
        profile = get_profile()
        topic = params.get("topic", "")
        if not topic:
            topic = profile.seed_keywords.get(profile.default_specialty.value, ["通用"])[0]
        specialty = params.get("specialty", profile.default_specialty.value)
        content_type = params.get("content_type", "seo_article")

        try:
            # 1. 关键词研究
            ke = KeywordEngine()
            topics = ke.research(specialty, seed=topic, content_type=content_type, limit=1)
            t = topics[0]

            # 2. 生成文章
            gen = ContentGenerator()
            ct = ContentType.SEO_ARTICLE if content_type == "seo_article" else ContentType.WECHAT
            article = gen.generate_article(t, ct)

            self._json_response({
                "success": True,
                "article_id": article.id,
                "title": article.title,
                "content": article.content,
                "content_type": content_type,
                "length": len(article.content),
            })
        except Exception as e:
            self._json_response({"success": False, "error": str(e)}, status=500)

    def _api_check(self, body):
        """质量检查"""
        params = json.loads(body)
        article_id = params.get("article_id")

        try:
            from clinic_engine.db import Database
            db = Database()
            article = db.get_article(article_id)
            if not article:
                self._json_response({"success": False, "error": f"未找到文章 ID={article_id}"}, status=404)
                return

            checker = QualityChecker()
            result = checker.check_article(article)

            self._json_response({
                "success": True,
                "passed": result.passed,
                "issues": [
                    {"rule": i.rule, "severity": i.severity, "message": i.message, "location": i.location}
                    for i in result.issues
                ],
            })
        except Exception as e:
            self._json_response({"success": False, "error": str(e)}, status=500)

    def _api_verify(self, body):
        """医学声明验证"""
        params = json.loads(body)
        article_id = params.get("article_id")

        try:
            from clinic_engine.db import Database
            db = Database()
            article = db.get_article(article_id)
            if not article:
                self._json_response({"success": False, "error": f"未找到文章 ID={article_id}"}, status=404)
                return

            kb = KnowledgeBase() if KnowledgeBase else None
            if kb and kb.count() == 0:
                kb.ingest_directory()

            verifier = ReActVerifier(kb=kb, use_online=False) if ReActVerifier else None
            if not verifier:
                self._json_response({"success": False, "error": "验证模块不可用"}, status=500)
                return

            report = verifier.verify_article(article.title, article.content)

            self._json_response({
                "success": True,
                "total": report.total_claims,
                "verified": report.verified,
                "partially": report.partially,
                "unverified": report.unverified,
                "needs_review": report.needs_review,
                "pass_rate": round(report.pass_rate, 2),
                "results": [
                    {
                        "claim": r.claim[:100],
                        "category": r.category,
                        "status": r.status.value,
                        "confidence": round(r.confidence, 2),
                        "sources": r.sources[:2],
                        "reasoning": r.reasoning[:100],
                    }
                    for r in report.results
                ],
            })
        except Exception as e:
            self._json_response({"success": False, "error": str(e)}, status=500)

    def _api_publish(self, body):
        """发布文章到本地文件"""
        params = json.loads(body)
        article_id = params.get("article_id")

        try:
            from clinic_engine.db import Database
            from clinic_engine.publisher import FilePublisher

            db = Database()
            article = db.get_article(article_id)
            if not article:
                self._json_response({"success": False, "error": f"未找到文章 ID={article_id}"}, status=404)
                return

            publisher = FilePublisher()
            result = publisher.publish(article)
            self._json_response({"success": True, "path": result["path"]})
        except Exception as e:
            self._json_response({"success": False, "error": str(e)}, status=500)

    def log_message(self, format, *args):
        """静默日志"""
        pass


def main():
    port = 8083
    profile = get_profile()
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"{profile.brand_name} 内容引擎已启动: http://localhost:{port}")
    print(f"按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
