#!/usr/bin/env python3
"""
codex-quantum-v1.py — Codex Quantum Version 1: Flat File Enhancement

Three additions to the existing flat file system:
  1. BM25 Keyword Scoring — rank_bm25 replaces custom keyword counting
  2. Metadata Blocks — structured .meta companion files per Codex file
  3. Query Rewriting — gemma3:4b generates alternative phrasings

Everything built here feeds directly into LightRAG in Version 2.

Usage:
  python scripts/codex-quantum-v1.py --build       # Build BM25 index + metadata blocks
  python scripts/codex-quantum-v1.py --query "..."  # Search with query rewriting
  python scripts/codex-quantum-v1.py --test         # Run the five test queries
  python scripts/codex-quantum-v1.py --status       # Show current index status

Hard rules:
  - num_ctx = 8192 on all Ollama calls
  - gemma3:4b for local inference (summaries + query rewriting)
  - Max 100 tokens per metadata block
  - Total context must never exceed 8192 tokens
  - If anything fails, COI falls back to plain flat files
"""

import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

# ── PATHS ────────────────────────────────────────────────────
ICM_ROOT  = Path("K:/Coi Codex/COI-Codex-ICM-V5")
CODEX_DIR = ICM_ROOT / "COI"
INDEX_PATH = ICM_ROOT / "scripts" / "cq-v1-index.json"

# Ollama config — hard caps
OLLAMA_HOST  = "http://localhost:11434"
GEMMA_MODEL  = "gemma3:4b-cq"  # Custom Modelfile with num_ctx=8190 baked in
NUM_CTX      = 8192  # Non-negotiable. Protects VRAM headroom on RX 6600.

# Token budget
MAX_CONTEXT_TOKENS   = 8192
META_BLOCK_MAX_TOKENS = 100
APPROX_CHARS_PER_TOKEN = 4  # conservative estimate for English text

# File extensions to index
INDEXABLE_EXTENSIONS = {".md", ".json", ".jsonl", ".txt"}

# Skip directories inside COI/
SKIP_DIRS = {".git", "__pycache__", ".claude", "training", "sessions", "briefings"}

# Stopwords for BM25 tokenization
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "each",
    "all", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "same", "so", "than", "too", "very", "just", "but",
    "and", "or", "if", "this", "that", "these", "those", "it", "its",
    "they", "them", "their", "we", "our", "you", "your", "he", "she",
    "his", "her", "i", "my", "what", "which", "who", "how", "when",
    "where", "why", "then", "there", "here",
}


# ── HELPERS ──────────────────────────────────────────────────

def log(msg, level="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[36m", "OK": "\033[32m",
        "WARN": "\033[33m", "ERROR": "\033[31m",
        "BM25": "\033[35m", "META": "\033[34m",
        "QUERY": "\033[33m",
    }
    c = colors.get(level, "\033[36m")
    print(f"{c}[{t}] [{level}]\033[0m {msg}")


def tokenize(text: str) -> list[str]:
    """Tokenize text for BM25: lowercase, remove stopwords, min length 2."""
    words = re.findall(r"[a-z][a-z0-9_-]*", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) >= 2]


def count_tokens(text: str) -> int:
    """Approximate token count. Conservative: ~4 chars per token."""
    return max(1, len(text) // APPROX_CHARS_PER_TOKEN)


def read_file_safe(path: Path) -> Optional[str]:
    """Read file content safely, return None on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return None


# ── FILE DISCOVERY ───────────────────────────────────────────

def find_codex_files() -> list[Path]:
    """Find all indexable files in the Codex directory."""
    files = []
    for path in CODEX_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in INDEXABLE_EXTENSIONS:
            continue
        # Skip directories we don't want to index
        parts = path.relative_to(CODEX_DIR).parts
        if any(skip in parts for skip in SKIP_DIRS):
            continue
        # Skip .meta files (our own output)
        if path.suffix == ".meta" or path.name.endswith(".meta"):
            continue
        files.append(path)
    return sorted(files)


# ══════════════════════════════════════════════════════════════
# COMPONENT 1: BM25 KEYWORD SCORING
# ══════════════════════════════════════════════════════════════

@dataclass
class BM25Index:
    """Holds the BM25 index and document metadata."""
    file_paths: list[Path]
    file_contents: list[str]
    tokenized_docs: list[list[str]]
    bm25: BM25Okapi
    file_keywords: dict  # {filepath_str: [(term, score), ...]}


def build_bm25_index(files: list[Path]) -> Optional[BM25Index]:
    """Build BM25 index across all Codex files."""
    if not files:
        log("No files to index", "ERROR")
        return None

    file_paths = []
    file_contents = []
    tokenized_docs = []

    for f in files:
        content = read_file_safe(f)
        if not content or len(content.strip()) < 10:
            continue
        tokens = tokenize(content)
        if not tokens:
            continue
        file_paths.append(f)
        file_contents.append(content)
        tokenized_docs.append(tokens)

    if not tokenized_docs:
        log("No documents with content found", "ERROR")
        return None

    log(f"Building BM25 index: {len(tokenized_docs)} documents", "BM25")
    bm25 = BM25Okapi(tokenized_docs)

    # Extract top keywords per file using BM25 self-scoring
    file_keywords = {}
    for i, (path, tokens) in enumerate(zip(file_paths, tokenized_docs)):
        # Get unique terms in this document
        unique_terms = list(set(tokens))
        # Score each term as a single-word query against this specific document
        term_scores = {}
        for term in unique_terms:
            scores = bm25.get_scores([term])
            # The score for THIS document when queried with this term
            term_scores[term] = scores[i]

        # Normalize scores to 0-1 range
        if term_scores:
            max_score = max(term_scores.values())
            if max_score > 0:
                term_scores = {t: round(s / max_score, 2)
                              for t, s in term_scores.items()}

        # Keep top 15 terms
        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)[:15]
        rel_path = str(path.relative_to(ICM_ROOT))
        file_keywords[rel_path] = sorted_terms

    log(f"BM25 index built: {len(file_keywords)} documents indexed", "OK")
    return BM25Index(
        file_paths=file_paths,
        file_contents=file_contents,
        tokenized_docs=tokenized_docs,
        bm25=bm25,
        file_keywords=file_keywords,
    )


def bm25_search(index: BM25Index, query: str, top_n: int = 5) -> list[tuple[Path, float]]:
    """Search the BM25 index. Returns [(filepath, score), ...] ranked by relevance."""
    tokens = tokenize(query)
    if not tokens:
        return []

    scores = index.bm25.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results = []
    for doc_idx, score in ranked[:top_n]:
        if score > 0:
            results.append((index.file_paths[doc_idx], round(score, 4)))
    return results


# ══════════════════════════════════════════════════════════════
# COMPONENT 2: METADATA BLOCKS
# ══════════════════════════════════════════════════════════════

def _classify_file_type(path: Path) -> str:
    """Classify a Codex file into a type based on its location."""
    rel = path.relative_to(CODEX_DIR)
    parts = rel.parts

    if "00-constitution" in parts:
        return "constitution"
    if "L1-Routing" in parts:
        return "routing"
    if "L2-Contracts" in parts:
        return "contract"
    if "L3-Reference" in parts:
        return "reference"
    if "L4-Working" in parts:
        if "memory" in parts:
            return "memory"
        if "graph" in parts:
            return "graph"
        return "working"
    return "document"


def _classify_component(path: Path, content: str) -> str:
    """Determine which COI component this file relates to."""
    name_lower = path.stem.lower()
    content_lower = content[:2000].lower()

    component_signals = {
        "Forge": ["forge", "department", "job_routing", "forge_manager"],
        "Desktop": ["desktop", "pyqt", "ui", "chat", "panel"],
        "Codex": ["codex", "icm", "knowledge", "memory", "graph"],
        "VRAM": ["vram", "gpu", "rx 6600", "model_load"],
        "Pipeline": ["pipeline", "intake", "generate", "review", "sandbox", "deploy"],
        "Constitution": ["constitution", "article", "immutable", "succession"],
        "Intelligence": ["intelligence", "classifier", "routing", "tier"],
        "Training": ["training", "benchmark", "scoring", "dataset"],
    }

    for component, signals in component_signals.items():
        if any(s in name_lower or s in content_lower for s in signals):
            return component
    return "General"


def _generate_summary_local(filepath: Path, content: str) -> Optional[str]:
    """Generate a one-sentence summary using gemma3:4b locally via Ollama."""
    # Truncate content to keep prompt small
    snippet = content[:1500]
    prompt = (
        "Write exactly one sentence summarizing what this file is and what it does. "
        "Be specific. No fluff.\n\n"
        f"Filename: {filepath.name}\n"
        f"Content:\n{snippet}\n\n"
        "One-sentence summary:"
    )

    payload = json.dumps({
        "model": GEMMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "num_predict": 80,
            "temperature": 0.1,
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        summary = data.get("response", "").strip()
        # Clean up — take first real sentence (handle dots in filenames/abbreviations)
        if summary:
            # Split on sentence-ending patterns: period followed by space+uppercase or end-of-string
            sentences = re.split(r'(?<=[a-z])\.\s+(?=[A-Z])', summary, maxsplit=1)
            first = sentences[0].strip()
            if not first.endswith("."):
                first += "."
            # Cap at ~150 chars to stay within token budget
            if len(first) > 150:
                first = first[:147] + "..."
            return first
        return None
    except Exception as e:
        log(f"  Ollama summary failed for {filepath.name}: {e}", "WARN")
        return None


def _extract_manual_summary(content: str) -> Optional[str]:
    """Check if the file has an existing manual summary (first non-heading paragraph)."""
    lines = content.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---") or line.startswith("|"):
            continue
        # Found first content line — use it as summary if it's descriptive enough
        if len(line) > 30 and not line.startswith("```"):
            # Truncate to one sentence
            first = line.split(".")[0].strip()
            if len(first) > 20:
                return first + "."
        break
    return None


def generate_metadata_block(
    filepath: Path,
    content: str,
    keywords: list[tuple[str, float]],
    use_ollama: bool = True,
) -> str:
    """Generate a metadata block for a Codex file.

    Args:
        filepath: Path to the Codex file
        content: File content
        keywords: BM25-scored keywords [(term, score), ...]
        use_ollama: Whether to use Ollama for summary generation

    Returns:
        Formatted metadata block string
    """
    file_type = _classify_file_type(filepath)
    component = _classify_component(filepath, content)
    modified = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
    rel_path = filepath.relative_to(ICM_ROOT)

    # Summary: try manual first, then Ollama
    summary = _extract_manual_summary(content)
    if not summary and use_ollama:
        summary = _generate_summary_local(filepath, content)
    if not summary:
        summary = f"{filepath.stem} — {file_type} file in {component}."

    # Format keywords — fit within token budget
    # Each keyword entry is roughly: "term(0.95), " = ~15 chars = ~4 tokens
    # Budget for keywords line: ~60 tokens (leaving ~40 for other fields)
    kw_parts = []
    kw_token_budget = 60
    kw_tokens_used = 0
    for term, score in keywords:
        entry = f"{term}({score:.2f})"
        entry_tokens = count_tokens(entry + ", ")
        if kw_tokens_used + entry_tokens > kw_token_budget:
            break
        kw_parts.append(entry)
        kw_tokens_used += entry_tokens

    keywords_str = ", ".join(kw_parts)

    block = (
        f"---\n"
        f"FILE: {rel_path}\n"
        f"TYPE: {file_type}\n"
        f"COMPONENT: {component}\n"
        f"MODIFIED: {modified}\n"
        f"SUMMARY: {summary}\n"
        f"KEY_CONCEPTS: {keywords_str}\n"
        f"---"
    )

    # Verify token budget
    block_tokens = count_tokens(block)
    if block_tokens > META_BLOCK_MAX_TOKENS:
        # Trim keywords until we fit
        while kw_parts and count_tokens(block) > META_BLOCK_MAX_TOKENS:
            kw_parts.pop()
            keywords_str = ", ".join(kw_parts)
            block = (
                f"---\n"
                f"FILE: {rel_path}\n"
                f"TYPE: {file_type}\n"
                f"COMPONENT: {component}\n"
                f"MODIFIED: {modified}\n"
                f"SUMMARY: {summary}\n"
                f"KEY_CONCEPTS: {keywords_str}\n"
                f"---"
            )

    return block


def save_metadata_block(filepath: Path, block: str):
    """Save metadata block as a companion .meta file."""
    meta_path = filepath.parent / (filepath.name + ".meta")
    meta_path.write_text(block, encoding="utf-8")
    return meta_path


def needs_metadata_rebuild(filepath: Path) -> bool:
    """Check if metadata needs regenerating by comparing timestamps."""
    meta_path = filepath.parent / (filepath.name + ".meta")
    if not meta_path.exists():
        return True
    try:
        source_mtime = os.path.getmtime(filepath)
        meta_mtime = os.path.getmtime(meta_path)
        return source_mtime > meta_mtime
    except OSError:
        return True


def load_metadata_block(filepath: Path) -> Optional[str]:
    """Load a cached metadata block for a file."""
    meta_path = filepath.parent / (filepath.name + ".meta")
    if meta_path.exists():
        return read_file_safe(meta_path)
    return None


# ══════════════════════════════════════════════════════════════
# COMPONENT 3: QUERY REWRITING
# ══════════════════════════════════════════════════════════════

def rewrite_query(query: str) -> list[str]:
    """Generate two alternative query phrasings using gemma3:4b.

    Returns list of three queries: [original, variation1, variation2].
    Falls back to [original] if Ollama fails.
    """
    prompt = (
        f'Given this query: {query}\n'
        'Return exactly two alternative search queries '
        'that mean the same thing using different '
        'technical terminology. Return as JSON:\n'
        '{"variation1": "...", "variation2": "..."}\n'
        'Return ONLY the JSON, nothing else.'
    )

    payload = json.dumps({
        "model": GEMMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "num_predict": 150,
            "temperature": 0.3,
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        raw = data.get("response", "").strip()

        # Parse JSON from response — handle markdown code blocks
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)

        # Find the JSON object
        match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if match:
            variations = json.loads(match.group())
            v1 = variations.get("variation1", "").strip()
            v2 = variations.get("variation2", "").strip()
            queries = [query]
            if v1:
                queries.append(v1)
            if v2:
                queries.append(v2)
            return queries
    except Exception as e:
        log(f"Query rewriting failed: {e}", "WARN")

    return [query]  # Fallback — original only


# ══════════════════════════════════════════════════════════════
# INTEGRATED SEARCH — ALL THREE COMPONENTS WORKING TOGETHER
# ══════════════════════════════════════════════════════════════

@dataclass
class SearchResult:
    """A single search result with metadata."""
    filepath: Path
    score: float
    metadata_block: str
    content: str
    token_count: int


def search_codex(
    query: str,
    index: BM25Index,
    top_n: int = 5,
    use_rewriting: bool = True,
    context_budget: int = MAX_CONTEXT_TOKENS,
) -> list[SearchResult]:
    """Full CQ V1 search pipeline.

    1. Query rewriting — generates 2 variations (3 queries total)
    2. BM25 search — all 3 queries against all files
    3. Merge, deduplicate, rank by best score
    4. Load metadata blocks
    5. Enforce token budget

    Returns list of SearchResult with metadata + content, within budget.
    """
    # Step 1: Query rewriting
    if use_rewriting:
        queries = rewrite_query(query)
        log(f"Query variations: {queries}", "QUERY")
    else:
        queries = [query]

    # Step 2: BM25 search across all queries
    all_results = {}  # filepath -> best_score
    for q in queries:
        results = bm25_search(index, q, top_n=top_n * 2)
        for filepath, score in results:
            key = str(filepath)
            if key not in all_results or score > all_results[key][1]:
                all_results[key] = (filepath, score)

    # Step 3: Rank by best score, take top_n
    ranked = sorted(all_results.values(), key=lambda x: x[1], reverse=True)[:top_n]

    if not ranked:
        return []

    # Step 4: Build search results with metadata blocks
    results = []
    for filepath, score in ranked:
        meta = load_metadata_block(filepath)
        if not meta:
            meta = f"---\nFILE: {filepath.relative_to(ICM_ROOT)}\n---"

        content = read_file_safe(filepath)
        if not content:
            continue

        results.append(SearchResult(
            filepath=filepath,
            score=score,
            metadata_block=meta,
            content=content,
            token_count=count_tokens(meta) + count_tokens(content),
        ))

    # Step 5: Enforce token budget
    # Metadata blocks are never cut. Content is allocated proportionally by score.
    total_meta_tokens = sum(count_tokens(r.metadata_block) for r in results)
    remaining_budget = context_budget - total_meta_tokens

    if remaining_budget <= 0:
        # Even metadata blocks exceed budget — take only top results
        trimmed = []
        budget_left = context_budget
        for r in results:
            meta_tokens = count_tokens(r.metadata_block)
            if budget_left - meta_tokens < 0:
                break
            r.content = ""  # No room for content
            r.token_count = meta_tokens
            budget_left -= meta_tokens
            trimmed.append(r)
        return trimmed

    # Proportional allocation by BM25 score
    total_score = sum(r.score for r in results) or 1.0
    for r in results:
        proportion = r.score / total_score
        content_budget_chars = int(proportion * remaining_budget * APPROX_CHARS_PER_TOKEN)
        if len(r.content) > content_budget_chars:
            r.content = r.content[:content_budget_chars] + "\n[...truncated...]"
        r.token_count = count_tokens(r.metadata_block) + count_tokens(r.content)

    # Final check — if total still exceeds budget, trim from bottom
    total_tokens = sum(r.token_count for r in results)
    while total_tokens > context_budget and len(results) > 1:
        removed = results.pop()
        total_tokens -= removed.token_count

    return results


def format_context(results: list[SearchResult]) -> str:
    """Format search results into a context string for the LLM."""
    parts = []
    for r in results:
        parts.append(r.metadata_block)
        if r.content:
            parts.append(r.content)
        parts.append("")  # blank line separator
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════
# BUILD COMMAND — FULL INDEX + METADATA GENERATION
# ══════════════════════════════════════════════════════════════

def build_all(use_ollama: bool = True):
    """Full build: BM25 index + metadata blocks for all Codex files."""
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   Codex Quantum V1 — Build               ║")
    print("  ║   BM25 + Metadata + Query Rewriting       ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    # Find files
    files = find_codex_files()
    log(f"Found {len(files)} Codex files", "INFO")

    if not files:
        log("No files found in Codex directory", "ERROR")
        return None

    # Build BM25 index
    index = build_bm25_index(files)
    if not index:
        return None

    # Show BM25 keyword scores
    print()
    log("BM25 keyword scores per file:", "BM25")
    for rel_path, keywords in sorted(index.file_keywords.items()):
        top_5 = keywords[:5]
        kw_str = ", ".join(f"{t}({s})" for t, s in top_5)
        log(f"  {rel_path}: {kw_str}", "BM25")

    # Generate metadata blocks
    print()
    log("Generating metadata blocks...", "META")
    meta_count = 0
    skipped = 0

    for filepath in index.file_paths:
        rel_path = str(filepath.relative_to(ICM_ROOT))
        keywords = index.file_keywords.get(rel_path, [])

        if not needs_metadata_rebuild(filepath):
            skipped += 1
            continue

        content = read_file_safe(filepath)
        if not content:
            continue

        log(f"  Generating: {filepath.name}", "META")
        block = generate_metadata_block(filepath, content, keywords, use_ollama=use_ollama)
        save_metadata_block(filepath, block)
        meta_count += 1

    log(f"Metadata: {meta_count} generated, {skipped} cached (up to date)", "OK")

    # Save index state
    state = {
        "version": "1.0",
        "built": datetime.now().isoformat(),
        "file_count": len(index.file_paths),
        "files": [str(p.relative_to(ICM_ROOT)) for p in index.file_paths],
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    log(f"Index state saved: {INDEX_PATH}", "OK")

    return index


# ══════════════════════════════════════════════════════════════
# TEST COMMAND — FIVE TEST QUERIES
# ══════════════════════════════════════════════════════════════

TEST_QUERIES = [
    "What are you and what is your purpose",
    "What model handles job routing in the Forge",
    "What happens when VRAM runs out during a job",
    "What is Codex Quantum",
    "What is the current build phase of COI",
]


def run_tests(index: BM25Index, use_rewriting: bool = True):
    """Run the five test queries and show results."""
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   Codex Quantum V1 — Test Queries         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}")
        log(f"Test {i}: {query}", "QUERY")
        print(f"{'='*60}")

        t0 = time.perf_counter()
        results = search_codex(query, index, top_n=3, use_rewriting=use_rewriting)
        elapsed = (time.perf_counter() - t0) * 1000

        if not results:
            log("No results found", "WARN")
            continue

        total_tokens = sum(r.token_count for r in results)
        log(f"Results: {len(results)} files, {total_tokens} tokens, {elapsed:.0f}ms", "OK")

        for j, r in enumerate(results, 1):
            rel = r.filepath.relative_to(ICM_ROOT)
            print(f"\n  [{j}] {rel} (score: {r.score})")
            # Show metadata block
            for line in r.metadata_block.splitlines():
                if line.strip() and line.strip() != "---":
                    print(f"      {line.strip()}")

    print()


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Codex Quantum V1 — Flat File Enhancement")
    parser.add_argument("--build", action="store_true",
                        help="Build BM25 index + metadata blocks")
    parser.add_argument("--build-no-ollama", action="store_true",
                        help="Build without Ollama (skip LLM summaries)")
    parser.add_argument("--query", type=str,
                        help="Search the Codex with query rewriting")
    parser.add_argument("--query-simple", type=str,
                        help="Search without query rewriting")
    parser.add_argument("--test", action="store_true",
                        help="Run five test queries")
    parser.add_argument("--test-no-rewrite", action="store_true",
                        help="Run test queries without query rewriting")
    parser.add_argument("--status", action="store_true",
                        help="Show current index status")
    args = parser.parse_args()

    if args.build or args.build_no_ollama:
        use_ollama = not args.build_no_ollama
        index = build_all(use_ollama=use_ollama)
        if index and (args.build or args.build_no_ollama):
            print()
            log("Build complete. Run --test to verify.", "OK")

    elif args.query or args.query_simple:
        query_text = args.query or args.query_simple
        use_rewriting = bool(args.query)

        files = find_codex_files()
        index = build_bm25_index(files)
        if not index:
            log("Could not build index", "ERROR")
            sys.exit(1)

        t0 = time.perf_counter()
        results = search_codex(query_text, index, top_n=5, use_rewriting=use_rewriting)
        elapsed = (time.perf_counter() - t0) * 1000

        if not results:
            log("No results found", "WARN")
        else:
            total_tokens = sum(r.token_count for r in results)
            log(f"Results: {len(results)} files, {total_tokens} tokens, {elapsed:.0f}ms", "OK")
            for r in results:
                rel = r.filepath.relative_to(ICM_ROOT)
                print(f"\n  {rel} (score: {r.score})")
                print(f"  {r.metadata_block}")

    elif args.test or args.test_no_rewrite:
        files = find_codex_files()
        index = build_bm25_index(files)
        if not index:
            log("Could not build index", "ERROR")
            sys.exit(1)
        run_tests(index, use_rewriting=not args.test_no_rewrite)

    elif args.status:
        if INDEX_PATH.exists():
            state = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            print(f"\nCQ V1 Index Status:")
            print(f"  Version:    {state.get('version')}")
            print(f"  Built:      {state.get('built')}")
            print(f"  Files:      {state.get('file_count')}")

            # Count .meta files
            meta_count = sum(1 for f in CODEX_DIR.rglob("*.meta") if f.is_file())
            print(f"  Meta files: {meta_count}")

            # Check stale
            files = find_codex_files()
            stale = sum(1 for f in files if needs_metadata_rebuild(f))
            print(f"  Stale:      {stale}")
        else:
            print("\nNo CQ V1 index found. Run --build first.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
