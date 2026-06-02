"""声明验证模块 — ReAct Agent 架构

从文章中提取声明，通过"思考-行动-观察"循环逐条验证：
1. Thought: 分析声明，确定验证策略
2. Action: grep 知识库 / 联网搜索
3. Observation: 评估搜索结果
4. 重复直到得出结论

支持两种验证来源：
- 本地知识库 grep（快速、免费）
- 联网搜索（补充外部权威来源）
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger

from .config import config
from .industries import get_profile
from .rag import KnowledgeBase


class ClaimStatus(str, Enum):
    VERIFIED = "verified"  # 有可靠来源支持
    PARTIALLY = "partially"  # 部分支持
    UNVERIFIED = "unverified"  # 未找到来源
    CONTRADICTED = "contradicted"  # 与来源矛盾
    NEEDS_REVIEW = "needs_review"  # 需要医生审核


@dataclass
class Claim:
    text: str
    category: str = ""  # dosage, statistic, recommendation, contraindication
    keywords: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    claim: str
    category: str
    status: ClaimStatus
    confidence: float  # 0-1
    sources: list[str] = field(default_factory=list)
    reasoning: str = ""
    actions_taken: list[dict] = field(default_factory=list)


@dataclass
class VerificationReport:
    article_title: str
    total_claims: int = 0
    verified: int = 0
    partially: int = 0
    unverified: int = 0
    contradicted: int = 0
    needs_review: int = 0
    results: list[VerificationResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return self.verified / self.total_claims

    def summary(self) -> str:
        lines = [
            f"验证报告: {self.article_title}",
            f"  总声明数: {self.total_claims}",
            f"  已验证: {self.verified}",
            f"  部分验证: {self.partially}",
            f"  未验证: {self.unverified}",
            f"  存在矛盾: {self.contradicted}",
            f"  需审核: {self.needs_review}",
            f"  验证通过率: {self.pass_rate:.0%}",
        ]
        if self.contradicted > 0:
            lines.append("\n  ⚠️ 存在与来源矛盾的声明，请重点审核：")
            for r in self.results:
                if r.status == ClaimStatus.CONTRADICTED:
                    lines.append(f"    - {r.claim[:60]}... (置信度: {r.confidence:.0%})")
        if self.needs_review > 0:
            lines.append("\n  需审核的声明：")
            for r in self.results:
                if r.status == ClaimStatus.NEEDS_REVIEW:
                    lines.append(f"    - {r.claim[:60]}...")
        return "\n".join(lines)


class ReActVerifier:
    """ReAct 架构的医学声明验证 Agent

    每条声明经历多轮"思考-行动-观察"循环：
    - Thought: 分析声明，选择验证策略（grep 知识库 / 联网搜索 / 提取关键词）
    - Action: 执行搜索操作
    - Observation: 评估搜索结果与声明的一致性
    - 循环直到有足够证据做出判断
    """

    MAX_STEPS = 5

    def __init__(self, kb: KnowledgeBase | None = None, use_online: bool = True):
        self.kb = kb or KnowledgeBase()
        self.use_online = use_online
        # 延迟导入避免循环依赖
        self._search_fn = None

    def _get_search_fn(self):
        if self._search_fn is None:
            try:
                from duckduckgo_search import DDGS
                self._search_fn = lambda q: [
                    {"title": r["title"], "body": r["body"], "href": r["href"]}
                    for r in DDGS().text(q, max_results=5)
                ]
            except Exception:
                self._search_fn = None
        return self._search_fn

    def verify_article(self, title: str, content: str) -> VerificationReport:
        """验证文章中的所有医学声明"""
        claims = self._extract_claims(content)
        report = VerificationReport(article_title=title, total_claims=len(claims))

        for claim in claims:
            result = self._verify_claim_react(claim)
            report.results.append(result)
            if result.status == ClaimStatus.VERIFIED:
                report.verified += 1
            elif result.status == ClaimStatus.PARTIALLY:
                report.partially += 1
            elif result.status == ClaimStatus.UNVERIFIED:
                report.unverified += 1
            elif result.status == ClaimStatus.CONTRADICTED:
                report.contradicted += 1
            else:
                report.needs_review += 1

        logger.info(f"验证完成: {report.verified}/{report.total_claims} 已验证")
        return report

    def _extract_claims(self, content: str) -> list[Claim]:
        """从文章中提取需要验证的声明"""
        claims = []
        # 按段落切分
        paragraphs = re.split(r'\n{2,}', content)

        # 从行业 profile 获取声明提取模式
        profile = get_profile()
        patterns = {}
        for cp in profile.claim_patterns:
            patterns[cp.category] = re.compile(cp.pattern)

        for para in paragraphs:
            para = para.strip()
            if len(para) < 15:
                continue
            # 跳过免责声明和纯标题
            if "不构成" in para and "医疗建议" in para:
                continue
            if para.startswith("#") and len(para) < 50:
                continue

            matched_categories = []
            keywords = []
            for cat, pat in patterns.items():
                if pat.search(para):
                    matched_categories.append(cat)
                    keywords.extend(pat.findall(para))

            if matched_categories:
                # 提取关键词用于搜索
                search_kws = self._extract_search_keywords(para)
                claims.append(Claim(
                    text=para,
                    category=matched_categories[0],
                    keywords=search_kws,
                ))

        # 去重（去除被其他段落包含的短段落）
        deduped = []
        for c in claims:
            if not any(c.text in other.text and c.text != other.text for other in claims):
                deduped.append(c)

        logger.info(f"提取到 {len(deduped)} 条待验证声明")
        return deduped

    def _extract_search_keywords(self, text: str) -> list[str]:
        """从声明中提取搜索关键词"""
        keywords = []
        # 提取中文术语（2-6字的连续中文）
        terms = re.findall(r'[一-鿿]{2,6}', text)
        # 过滤常见虚词 + 行业自定义停用词
        stopwords = {"的", "了", "在", "是", "和", "与", "或", "及", "对", "为",
                     "从", "到", "被", "把", "给", "让", "向", "以", "而", "但",
                     "因为", "所以", "如果", "虽然", "可以", "能够", "需要", "应该",
                     "建议", "推荐", "应当", "可能", "不会", "没有", "是否"}
        stopwords |= get_profile().claim_stopwords()
        for t in terms:
            if t not in stopwords and len(t) >= 2:
                keywords.append(t)

        # 提取剂量数字
        doses = re.findall(r'(\d+\.?\d*)\s*(mg|毫克|μg|微克)', text)
        for d in doses:
            keywords.append(f"{d[0]}{d[1]}")

        # 去重保序
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique[:10]

    def _verify_claim_react(self, claim: Claim) -> VerificationResult:
        """ReAct 循环验证单条声明"""
        history = []
        evidence = []
        sources = []
        step = 0

        # 初始化思考
        thought = f"需要验证声明：「{claim.text[:80]}...」（类别: {claim.category}）"
        logger.debug(f"[ReAct] Thought: {thought}")

        while step < self.MAX_STEPS:
            step += 1
            action, action_input = self._decide_action(claim, history, step)
            logger.debug(f"[ReAct] Step {step} Action: {action}, Input: {action_input}")

            observation = self._execute_action(action, action_input)
            history.append({
                "step": step,
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
            })

            if observation.get("evidence"):
                evidence.append(observation["evidence"])
            if observation.get("source"):
                sources.append(observation["source"])

            # 评估是否已有足够证据
            thought, should_stop = self._evaluate(claim, history, evidence)
            logger.debug(f"[ReAct] Thought: {thought}")
            if should_stop:
                break

        # 最终判断
        return self._judge(claim, evidence, sources, history)

    def _decide_action(self, claim: Claim, history: list[dict], step: int) -> tuple[str, dict]:
        """决定下一步行动"""
        tried_kw = set()
        for h in history:
            if h["action"] == "grep_kb":
                tried_kw.add(h["action_input"].get("keyword", ""))
            elif h["action"] == "online_search":
                tried_kw.add(h["action_input"].get("query", ""))

        if step == 1:
            # 第一步：用最相关的关键词 grep 知识库
            if claim.keywords:
                kw = claim.keywords[0]
                return "grep_kb", {"keyword": kw}
            return "grep_kb", {"keyword": claim.text[:10]}

        if step == 2:
            # 第二步：用其他关键词 grep
            for kw in claim.keywords[1:4]:
                if kw not in tried_kw:
                    return "grep_kb", {"keyword": kw}
            # 所有关键词都试过了，转在线搜索
            if self.use_online and self._get_search_fn():
                return "online_search", {"query": claim.text[:50]}
            return "grep_kb", {"keyword": claim.text[:8]}

        if step == 3 and self.use_online and self._get_search_fn():
            # 第三步：联网搜索
            query = " ".join(claim.keywords[:3]) if claim.keywords else claim.text[:40]
            return "online_search", {"query": query}

        if step == 4:
            # 第四步：用不同组合再搜一次
            query = claim.text[:50]
            if self.use_online and self._get_search_fn():
                return "online_search", {"query": query}
            return "grep_kb", {"keyword": claim.text[:6]}

        # 最后一步：关键词精确匹配
        return "grep_exact", {"keywords": claim.keywords[:5]}

    def _execute_action(self, action: str, action_input: dict) -> dict:
        """执行搜索动作，返回观察结果"""
        if action == "grep_kb":
            keyword = action_input.get("keyword", "")
            if not keyword:
                return {"evidence": None, "source": None, "found": False, "detail": "空关键词"}
            results = self.kb.grep(keyword)
            if results:
                best = results[0]
                return {
                    "evidence": best["content"][:200],
                    "source": best["source"],
                    "found": True,
                    "match_count": len(results),
                    "detail": f"知识库中找到 {len(results)} 处匹配「{keyword}」",
                }
            return {"evidence": None, "source": None, "found": False,
                    "detail": f"知识库中未找到「{keyword}」"}

        if action == "grep_exact":
            keywords = action_input.get("keywords", [])
            if not keywords:
                return {"evidence": None, "source": None, "found": False, "detail": "无关键词"}
            results = self.kb.grep_multi(keywords)
            if results:
                best = results[0]
                return {
                    "evidence": best["content"][:200],
                    "source": best["source"],
                    "found": True,
                    "match_count": len(results),
                    "matched_kws": best.get("matched_keywords", []),
                    "detail": f"精确搜索匹配 {len(results)} 处",
                }
            return {"evidence": None, "source": None, "found": False,
                    "detail": f"精确搜索未找到匹配"}

        if action == "online_search":
            query = action_input.get("query", "")
            if not query:
                return {"evidence": None, "source": None, "found": False, "detail": "空查询"}
            search_fn = self._get_search_fn()
            if search_fn is None:
                return {"evidence": None, "source": None, "found": False,
                        "detail": "联网搜索不可用"}
            try:
                results = search_fn(query)
                if results:
                    best = results[0]
                    return {
                        "evidence": best.get("body", "")[:200],
                        "source": best.get("href", ""),
                        "found": True,
                        "result_count": len(results),
                        "detail": f"联网搜索找到 {len(results)} 条结果",
                    }
                return {"evidence": None, "source": None, "found": False,
                        "detail": f"联网搜索「{query}」无结果"}
            except Exception as e:
                return {"evidence": None, "source": None, "found": False,
                        "detail": f"联网搜索出错: {e}"}

        return {"evidence": None, "source": None, "found": False, "detail": "未知动作"}

    def _evaluate(self, claim: Claim, history: list[dict], evidence: list) -> tuple[str, bool]:
        """评估当前证据，决定是否继续搜索"""
        found_count = sum(1 for h in history if h["observation"].get("found"))

        if found_count >= 2:
            return "已找到多条支持证据，可以做出判断", True

        if found_count >= 1 and len(history) >= 2:
            return "已找到支持证据，做出判断", True

        if len(history) >= self.MAX_STEPS:
            return "已达最大搜索步数，基于现有证据判断", True

        if len(history) >= 2 and found_count == 0:
            # 连续两次未找到
            return "知识库未找到相关证据，尝试联网搜索", False

        return "继续搜索更多证据", False

    def _judge(self, claim: Claim, evidence: list, sources: list,
               history: list[dict]) -> VerificationResult:
        """基于 ReAct 循环的证据做出最终判断"""
        found_count = sum(1 for h in history if h["observation"].get("found"))
        total_steps = len(history)

        # 构建推理过程摘要
        reasoning_parts = []
        for h in history:
            obs = h["observation"]
            if obs.get("found"):
                reasoning_parts.append(
                    f"Step {h['step']}: 搜索「{h['action_input']}」→ 找到 {obs.get('match_count', obs.get('result_count', 0))} 条结果"
                )
            else:
                reasoning_parts.append(
                    f"Step {h['step']}: 搜索「{h['action_input']}」→ 未找到"
                )

        reasoning = "; ".join(reasoning_parts)

        # 判断逻辑
        if found_count >= 2:
            status = ClaimStatus.VERIFIED
            confidence = 0.9
        elif found_count == 1:
            status = ClaimStatus.PARTIALLY
            confidence = 0.6
        elif found_count == 0 and self.use_online:
            # 知识库和在线都没找到，需要医生审核
            status = ClaimStatus.NEEDS_REVIEW
            confidence = 0.3
            reasoning += " | 知识库和在线搜索均未找到支持证据，建议医生审核"
        elif found_count == 0:
            status = ClaimStatus.UNVERIFIED
            confidence = 0.2
            reasoning += " | 知识库未找到支持证据"
        else:
            status = ClaimStatus.PARTIALLY
            confidence = 0.5

        # 检查剂量类声明是否与来源一致
        if claim.category == "dosage" and evidence:
            for ev in evidence:
                if self._check_contradiction(claim.text, ev):
                    status = ClaimStatus.CONTRADICTED
                    confidence = 0.8
                    reasoning += " | 发现与来源矛盾的剂量信息"
                    break

        return VerificationResult(
            claim=claim.text[:100],
            category=claim.category,
            status=status,
            confidence=confidence,
            sources=sources,
            reasoning=reasoning,
            actions_taken=history,
        )

    @staticmethod
    def _check_contradiction(claim_text: str, evidence_text: str) -> bool:
        """简单检查声明与证据是否存在数字矛盾"""
        claim_nums = set(re.findall(r'\d+\.?\d*', claim_text))
        evidence_nums = set(re.findall(r'\d+\.?\d*', evidence_text))
        # 如果声明中的数字在证据中完全不存在，可能存在矛盾
        if claim_nums and evidence_nums and not claim_nums & evidence_nums:
            # 但也要考虑单位不同，所以只在数字差异很大时标记
            return True
        return False
