"""
Rule-based metrics implemented on DeepEval's BaseMetric interface.
These metrics require NO judge model — zero LLM cost.
"""

import re
import jieba
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class F1Metric(BaseMetric):
    """
    Token-level F1 score: 2*P*R/(P+R).
    Uses jieba for Chinese tokenization or whitespace split for English.
    V3.2 fix: p/r variables initialized in all branches.
    """

    def __init__(self, threshold: float = 0.6, params: dict = None):
        self.threshold = threshold
        self.tokenizer = (params or {}).get("tokenizer", "jieba")
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        ref = self._tokenize(test_case.expected_output or "")
        hyp = self._tokenize(test_case.actual_output or "")
        if not ref or not hyp:
            self.score = 0.0
            p, r = 0.0, 0.0  # V3.2 fix: ensure p/r defined in all branches
        else:
            ref_set, hyp_set = set(ref), set(hyp)
            common = ref_set & hyp_set
            p = len(common) / len(hyp_set) if hyp_set else 0
            r = len(common) / len(ref_set) if ref_set else 0
            self.score = 2 * p * r / (p + r) if (p + r) else 0
        self.success = self.score >= self.threshold
        self.reason = f"F1={self.score:.3f} (P={p:.2f}, R={r:.2f})"
        return self.score

    def _tokenize(self, text: str) -> list:
        if self.tokenizer == "jieba":
            return list(jieba.cut(text))
        return text.split()

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "F1 Score"


class ExactMatchMetric(BaseMetric):
    """
    Binary: is actual_output exactly equal to expected_output after normalization?
    Score = 1.0 if match, 0.0 otherwise.
    """

    def __init__(self, threshold: float = 0.8, params: dict = None):
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        normalize = lambda s: re.sub(r"\s+", "", (s or "").strip())
        self.score = 1.0 if normalize(test_case.actual_output) == normalize(test_case.expected_output) else 0.0
        self.success = self.score >= self.threshold
        self.reason = "Exact match" if self.success else "Output differs from expected"
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Exact Match"


class RougeLMetric(BaseMetric):
    """
    ROUGE-L: Longest Common Subsequence based text similarity.
    F = 2*P*R/(P+R) where P and R are LCS-based precision and recall.
    """

    def __init__(self, threshold: float = 0.5, params: dict = None):
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        ref = list(jieba.cut(test_case.expected_output or ""))
        hyp = list(jieba.cut(test_case.actual_output or ""))
        lcs_len = self._lcs_length(ref, hyp)
        p = lcs_len / len(hyp) if hyp else 0
        r = lcs_len / len(ref) if ref else 0
        self.score = 2 * p * r / (p + r) if (p + r) else 0
        self.success = self.score >= self.threshold
        self.reason = f"ROUGE-L={self.score:.3f} (P={p:.2f}, R={r:.2f})"
        return self.score

    @staticmethod
    def _lcs_length(a: list, b: list) -> int:
        """Compute LCS length using dynamic programming."""
        m, n = len(a), len(b)
        # Space-optimized: only keep two rows
        prev = [0] * (n + 1)
        curr = [0] * (n + 1)
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    curr[j] = prev[j - 1] + 1
                else:
                    curr[j] = max(prev[j], curr[j - 1])
            prev, curr = curr, [0] * (n + 1)
        return prev[n] if prev else 0

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "ROUGE-L"


class BLEUMetric(BaseMetric):
    """
    BLEU score: n-gram precision with brevity penalty.
    Uses sentence-level BLEU (smoothed) for short texts.
    """

    def __init__(self, threshold: float = 0.3, params: dict = None):
        self.threshold = threshold
        self.max_n = (params or {}).get("max_n", 4)
        self.smooth = (params or {}).get("smooth", True)
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        ref = list(jieba.cut(test_case.expected_output or ""))
        hyp = list(jieba.cut(test_case.actual_output or ""))

        if not ref or not hyp:
            self.score = 0.0
            self.success = False
            self.reason = "Empty input or output"
            return self.score

        # Compute n-gram precisions
        precisions = []
        for n in range(1, self.max_n + 1):
            ref_ngrams = self._get_ngrams(ref, n)
            hyp_ngrams = self._get_ngrams(hyp, n)
            # Count overlapping n-grams (min of counts)
            common = sum(min(ref_ngrams.get(g, 0), c) for g, c in hyp_ngrams.items())
            total = sum(hyp_ngrams.values())
            if self.smooth:
                precisions.append((common + 1) / (total + 1))
            else:
                precisions.append(common / total if total > 0 else 0)

        # Geometric mean of precisions
        import math
        log_avg = sum(math.log(p) if p > 0 else -1e10 for p in precisions) / len(precisions)
        bleu = math.exp(log_avg)

        # Brevity penalty
        bp = 1.0 if len(hyp) > len(ref) else math.exp(1 - len(ref) / len(hyp))
        self.score = bp * bleu

        self.success = self.score >= self.threshold
        self.reason = f"BLEU={self.score:.3f} (ref_len={len(ref)}, hyp_len={len(hyp)})"
        return self.score

    @staticmethod
    def _get_ngrams(tokens: list, n: int) -> dict:
        ngrams = {}
        for i in range(len(tokens) - n + 1):
            gram = tuple(tokens[i:i + n])
            ngrams[gram] = ngrams.get(gram, 0) + 1
        return ngrams

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "BLEU"


class StringSimilarityMetric(BaseMetric):
    """
    Character-level string similarity using SequenceMatcher.
    Score = similarity ratio (0.0 to 1.0).
    """

    def __init__(self, threshold: float = 0.7, params: dict = None):
        self.threshold = threshold
        self.normalize = (params or {}).get("normalize", True)
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        import difflib
        ref = test_case.expected_output or ""
        hyp = test_case.actual_output or ""

        if self.normalize:
            ref = re.sub(r"\s+", "", ref.strip())
            hyp = re.sub(r"\s+", "", hyp.strip())

        if not ref and not hyp:
            self.score = 1.0
        else:
            self.score = difflib.SequenceMatcher(None, ref, hyp).ratio()

        self.success = self.score >= self.threshold
        self.reason = f"Similarity={self.score:.3f} (ref_len={len(ref)}, hyp_len={len(hyp)})"
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "String Similarity"


class LengthRatioMetric(BaseMetric):
    """
    Output length ratio: min(|ref|,|hyp|) / max(|ref|,|hyp|).
    Measures if the output length is proportionally similar to expected.
    Useful for detecting overly verbose or too-short outputs.
    """

    def __init__(self, threshold: float = 0.5, params: dict = None):
        self.threshold = threshold
        self.unit = (params or {}).get("unit", "char")  # "char" or "token"
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        ref = test_case.expected_output or ""
        hyp = test_case.actual_output or ""

        if self.unit == "token":
            ref_len = len(list(jieba.cut(ref)))
            hyp_len = len(list(jieba.cut(hyp)))
        else:
            ref_len = len(ref)
            hyp_len = len(hyp)

        if ref_len == 0 and hyp_len == 0:
            self.score = 1.0
        elif ref_len == 0 or hyp_len == 0:
            self.score = 0.0
        else:
            self.score = min(ref_len, hyp_len) / max(ref_len, hyp_len)

        self.success = self.score >= self.threshold
        self.reason = f"LengthRatio={self.score:.3f} (ref={ref_len}, hyp={hyp_len})"
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Length Ratio"


class KeywordCoverageMetric(BaseMetric):
    """
    Keyword coverage: what fraction of expected keywords appear in the output.
    Keywords can be specified in params or extracted from expected_output.
    """

    def __init__(self, threshold: float = 0.6, params: dict = None):
        self.threshold = threshold
        self.keywords = (params or {}).get("keywords", [])
        self.extract_method = (params or {}).get("extract", "jieba")  # "jieba" or "split"
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        hyp = test_case.actual_output or ""

        # Get keywords: from config or from expected_output
        if self.keywords:
            keywords = set(self.keywords)
        else:
            ref = test_case.expected_output or ""
            # Try to parse JSON: if expected_output is a JSON structure like
            # {"expected_output": "钼铁"}, extract inner values as keywords.
            extracted = self._extract_values_from_json(ref)
            if extracted:
                keywords = set(extracted)
            elif self.extract_method == "jieba":
                keywords = set(w for w in jieba.cut(ref) if len(w) >= 2)
            else:
                keywords = set(w for w in ref.split() if len(w) >= 2)

        if not keywords:
            self.score = 1.0 if not hyp else 0.0
            self.success = self.score >= self.threshold
            self.reason = "No keywords to check"
            return self.score

        # Check how many keywords appear in output
        hyp_lower = hyp.lower()
        found = sum(1 for kw in keywords if kw.lower() in hyp_lower)
        self.score = found / len(keywords)

        self.success = self.score >= self.threshold
        self.reason = f"KeywordCoverage={self.score:.3f} ({found}/{len(keywords)} keywords found)"
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @staticmethod
    def _extract_values_from_json(text: str) -> list:
        """
        Extract meaningful string values from a JSON structure.
        For {"expected_output": "钼铁"} → returns ["钼铁"].
        Handles nested dicts and lists, filtering out non-value JSON artifacts.
        """
        import json
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return []

        results = []

        def _walk(obj):
            if isinstance(obj, str):
                # Filter out JSON structural strings like '{', ':', etc.
                stripped = obj.strip()
                if stripped and not all(c in '{}[]":, \t\n\r' for c in stripped):
                    results.append(stripped)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)

        _walk(data)
        return [r for r in results if r]

    @property
    def __name__(self):
        return "Keyword Coverage"


class MetaValidationMetric(BaseMetric):
    """
    Validates SSE meta fields (agentId, convId, title, etc.) against expected values.

    Compares test_case._actual_meta (from SSE event: meta) against
    test_case._expected_meta (from dataset expected_meta field).

    Supports:
      - Exact match: {"agentId": "72d2ab..."}
      - Contains match: {"title_contains": "华为"}
      - Pattern match: {"convId_pattern": "^\\d+$"}  (regex)
      - Field exists: {"agentId": "__exists__"}
    """

    def __init__(self, threshold: float = 1.0, params: dict = None):
        self.threshold = threshold
        self.check_fields = (params or {}).get("check_fields", [])  # empty = check all
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        import json as _json

        actual_meta = getattr(test_case, "_actual_meta", None) or {}
        expected_meta = getattr(test_case, "_expected_meta", None) or {}

        # Fallback: try parsing from expected_output if it looks like meta JSON
        if not expected_meta and test_case.expected_output:
            try:
                parsed = _json.loads(test_case.expected_output)
                if isinstance(parsed, dict) and any(
                    k in parsed for k in ("agentId", "convId", "title", "aiMsgId")
                ):
                    expected_meta = parsed
            except (ValueError, TypeError):
                pass

        if not expected_meta:
            self.score = 1.0
            self.success = True
            self.reason = "No expected meta to validate"
            return self.score

        if not actual_meta:
            self.score = 0.0
            self.success = False
            self.reason = "No actual meta captured from SSE response"
            return self.score

        # Determine which fields to check
        checks = []
        details = []
        passed = 0

        for key, expected_val in expected_meta.items():
            # Support "field_contains" suffix
            if key.endswith("_contains"):
                field = key[:-9]  # strip _contains
                actual_val = str(actual_meta.get(field, ""))
                match = expected_val.lower() in actual_val.lower()
                checks.append((f"{field} contains '{expected_val}'", match))
            # Support "field_pattern" suffix
            elif key.endswith("_pattern"):
                field = key[:-8]  # strip _pattern
                actual_val = str(actual_meta.get(field, ""))
                match = bool(re.match(expected_val, actual_val))
                checks.append((f"{field} matches '{expected_val}'", match))
            # Special marker: __exists__
            elif expected_val == "__exists__":
                match = key in actual_meta and actual_meta[key] is not None
                checks.append((f"{key} exists", match))
            # Exact match (skip if field not in check_fields filter)
            else:
                actual_val = actual_meta.get(key)
                match = str(actual_val) == str(expected_val)
                checks.append((f"{key}='{expected_val}'", match))

        # Apply field filter if specified
        if self.check_fields:
            checks = [(desc, m) for desc, m in checks
                       if any(f in desc for f in self.check_fields)]

        if not checks:
            self.score = 1.0
            self.success = True
            self.reason = "No matching fields to check"
            return self.score

        passed = sum(1 for _, m in checks if m)
        total = len(checks)
        self.score = passed / total

        # Build detail string
        detail_parts = []
        for desc, match in checks:
            status = "✓" if match else "✗"
            detail_parts.append(f"{status} {desc}")

        self.success = self.score >= self.threshold
        self.reason = f"MetaValidation={self.score:.2f} ({passed}/{total}): {'; '.join(detail_parts)}"
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Meta Validation"
