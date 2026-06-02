import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from loguru import logger

from .config import config

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"  # fallback, 优先用 profile
DB_DIR = Path(config.DB_PATH).parent / "rag_store"


class KnowledgeBase:
    def __init__(self, collection_name: str | None = None):
        from .industries import get_profile
        profile = get_profile()
        collection_name = collection_name or profile.collection_name

        DB_DIR.mkdir(parents=True, exist_ok=True)
        self.store_path = DB_DIR / f"{collection_name}.json"
        self._knowledge_dir = profile.knowledge_dir
        self.chunks: list[dict] = []
        self._load()
        logger.info(f"知识库已连接: {collection_name}, 文档数={len(self.chunks)}")

    def _load(self):
        if self.store_path.exists():
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            self.chunks = data

    def _save(self):
        self.store_path.write_text(json.dumps(self.chunks, ensure_ascii=False, indent=1), encoding="utf-8")

    def ingest_text(self, text: str, source: str, chunk_size: int = 500, chunk_overlap: int = 100) -> int:
        """将文本切分后摄入知识库"""
        parts = self._split_text(text, chunk_size, chunk_overlap)

        # Remove existing chunks from this source
        self.chunks = [c for c in self.chunks if c["source"] != source]

        for i, part in enumerate(parts):
            chunk_id = hashlib.md5(f"{source}_{i}_{part[:50]}".encode()).hexdigest()
            tokens = self._tokenize(part)
            self.chunks.append({
                "id": chunk_id,
                "content": part,
                "source": source,
                "chunk_index": i,
                "tokens": tokens,
            })

        self._save()
        logger.success(f"已摄入 {len(parts)} 个文档块: {source}")
        return len(parts)

    def ingest_file(self, file_path: str | Path) -> int:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if file_path.suffix.lower() == ".pdf":
            text = self._read_pdf(file_path)
        else:
            text = file_path.read_text(encoding="utf-8")
        return self.ingest_text(text, source=file_path.name)

    @staticmethod
    def _read_pdf(file_path: Path) -> str:
        import pdfplumber
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n\n".join(pages)

    def ingest_directory(self, dir_path: str | Path | None = None) -> int:
        dir_path = Path(dir_path) if dir_path else self._knowledge_dir
        total = 0
        for f in sorted(dir_path.glob("*")):
            if f.suffix in (".txt", ".md", ".pdf"):
                count = self.ingest_file(f)
                total += count
                logger.info(f"  已处理: {f.name} ({count} chunks)")
        logger.success(f"批量摄入完成: 共 {total} 个文档块")
        return total

    def query(self, question: str, n_results: int = 5) -> list[dict]:
        """用 BM25 检索相关知识"""
        if not self.chunks:
            return []

        query_tokens = self._tokenize(question)
        scored = []

        # Compute IDF
        N = len(self.chunks)
        df = Counter()
        for chunk in self.chunks:
            for token in set(chunk["tokens"]):
                df[token] += 1

        idf = {token: math.log((N - freq + 0.5) / (freq + 0.5) + 1) for token, freq in df.items()}

        # BM25 scoring
        k1, b = 1.5, 0.75
        avgdl = sum(len(c["tokens"]) for c in self.chunks) / N if N > 0 else 1

        for chunk in self.chunks:
            if not chunk["tokens"]:
                continue
            score = 0.0
            dl = len(chunk["tokens"])
            token_counts = Counter(chunk["tokens"])
            for qt in query_tokens:
                if qt in token_counts:
                    tf = token_counts[qt]
                    tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
                    score += idf.get(qt, 0) * tf_norm
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: -x[0])
        max_score = scored[0][0] if scored else 1.0

        results = []
        for score, chunk in scored[:n_results]:
            results.append({
                "content": chunk["content"],
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "relevance": round(score / max_score, 3),
            })
        return results

    def get_context(self, question: str, n_results: int = 3, min_relevance: float = 0.1) -> str:
        docs = self.query(question, n_results=n_results)
        filtered = [d for d in docs if d["relevance"] >= min_relevance]
        if not filtered:
            return ""
        parts = []
        for d in filtered:
            parts.append(f"[来源: {d['source']}]\n{d['content']}")
        return "\n\n---\n\n".join(parts)

    def count(self) -> int:
        return len(self.chunks)

    def clear(self):
        self.chunks = []
        if self.store_path.exists():
            self.store_path.unlink()
        logger.info("知识库已清空")

    def list_sources(self) -> list[str]:
        sources = set(c["source"] for c in self.chunks)
        return sorted(sources)

    def grep(self, keyword: str, case_sensitive: bool = False) -> list[dict]:
        """在知识库中按关键词搜索，返回匹配的文档块"""
        results = []
        for chunk in self.chunks:
            content = chunk["content"]
            if not case_sensitive:
                if keyword.lower() in content.lower():
                    results.append({
                        "content": content,
                        "source": chunk["source"],
                        "chunk_index": chunk["chunk_index"],
                    })
            else:
                if keyword in content:
                    results.append({
                        "content": content,
                        "source": chunk["source"],
                        "chunk_index": chunk["chunk_index"],
                    })
        return results

    def grep_multi(self, keywords: list[str], case_sensitive: bool = False) -> list[dict]:
        """多关键词搜索，返回包含任一关键词的文档块"""
        results = []
        seen = set()
        for kw in keywords:
            for item in self.grep(kw, case_sensitive=case_sensitive):
                key = (item["source"], item["chunk_index"])
                if key not in seen:
                    seen.add(key)
                    item["matched_keywords"] = [kw]
                    results.append(item)
                else:
                    for r in results:
                        if (r["source"], r["chunk_index"]) == key:
                            if kw not in r["matched_keywords"]:
                                r["matched_keywords"].append(kw)
                            break
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中文友好分词：按字符和标点切分"""
        import re
        # Keep Chinese characters, English words, numbers
        tokens = re.findall(r'[一-鿿]|[a-zA-Z]+|\d+', text.lower())
        # For Chinese, also generate bigrams for better matching
        result = []
        for token in tokens:
            if len(token) == 1 and '一' <= token <= '鿿':
                result.append(token)
            else:
                result.append(token)
        # Add bigrams for Chinese text
        chinese_chars = [t for t in tokens if len(t) == 1 and '一' <= t <= '鿿']
        for i in range(len(chinese_chars) - 1):
            result.append(chinese_chars[i] + chinese_chars[i + 1])
        return result

    @staticmethod
    def _split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) + 2 <= chunk_size:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current:
                    chunks.append(current.strip())
                if len(para) > chunk_size:
                    for j in range(0, len(para), chunk_size - chunk_overlap):
                        chunks.append(para[j:j + chunk_size])
                    current = ""
                else:
                    current = para
        if current.strip():
            chunks.append(current.strip())
        return chunks
