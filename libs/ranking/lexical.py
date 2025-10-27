"""
Lexical Scorers: TF-IDF and BM25 for deterministic ranking.

This module provides real lexical scoring algorithms (TF-IDF and Okapi BM25)
with deterministic vocabulary ordering, stable tokenization, and sklearn-
compatible interfaces.

SCA v13.8 Compliance:
- Deterministic: Fixed vocab sorting, stable tie-breaking
- Type-safe: 100% annotated, mypy --strict clean
- Offline: Pure computation, no network
- Real algorithms: No placeholders or mocks

References:
- TF-IDF: Salton & Buckley (1988)
- BM25: Robertson & Walker (1994), Okapi implementation
"""

from __future__ import annotations
from typing import Dict, List, Sequence
import math
import re
from collections import Counter

# Unicode-safe tokenization pattern
_TOKEN_RX = re.compile(r"[\w]+", flags=re.UNICODE)


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into lowercase words (deterministic).

    Uses Unicode-safe word boundary matching and ASCII lowercasing.
    Deterministic: identical text always produces identical tokens.

    Args:
        text: Input text to tokenize

    Returns:
        List of lowercase word tokens

    Examples:
        >>> tokenize("Hello World!")
        ['hello', 'world']
        >>> tokenize("ESG sustainability")
        ['esg', 'sustainability']
    """
    if not text:
        return []
    return [m.group(0).lower() for m in _TOKEN_RX.finditer(text)]


class TFIDFScorer:
    """
    TF-IDF scorer with sklearn-compatible interface.

    Implements Term Frequency-Inverse Document Frequency scoring with:
    - Deterministic vocabulary ordering (sorted)
    - Smooth IDF: log((N+1)/(df+1)) + 1.0
    - L2 normalization via sigmoid: 1/(1+exp(-score))

    Attributes:
        _vocab: Term to index mapping (deterministic order)
        _idf: IDF values for each vocab term
        _fitted: Whether fit() has been called

    Methods:
        fit(corpus): Compute IDF from corpus
        score(query, texts): Return scores in [0, 1]
        rank(query, texts): Return indices sorted by score
    """

    def __init__(self) -> None:
        """Initialize TFIDFScorer (unfitted)."""
        self._vocab: Dict[str, int] = {}
        self._idf: List[float] = []
        self._fitted: bool = False

    def fit(self, corpus: Sequence[str]) -> "TFIDFScorer":
        """
        Fit TF-IDF model to corpus (compute IDF values).

        Builds deterministic vocabulary (sorted alphabetically) and computes
        smooth IDF for each term: log((N+1)/(df+1)) + 1.0

        Args:
            corpus: List of documents (strings)

        Returns:
            Self for method chaining

        Raises:
            No exceptions (gracefully handles empty corpus)
        """
        # Tokenize all documents
        docs_tokens = [tokenize(doc) for doc in corpus]

        # Count document frequency (DF) for each term
        df: Counter[str] = Counter()
        for tokens in docs_tokens:
            # Count each term once per document (set removes duplicates)
            for term in sorted(set(tokens)):  # Deterministic iteration
                df[term] += 1

        # Build deterministic vocabulary (sorted)
        vocab_terms = sorted(df.keys())
        self._vocab = {term: idx for idx, term in enumerate(vocab_terms)}

        # Compute smooth IDF for each term
        n_docs = max(1, len(corpus))
        self._idf = [
            math.log((n_docs + 1.0) / (df[term] + 1.0)) + 1.0
            for term in vocab_terms
        ]

        self._fitted = True
        return self

    def score(self, query: str, texts: Sequence[str]) -> List[float]:
        """
        Score texts against query using TF-IDF.

        Computes TF-IDF score for each text:
        - TF: raw term frequency
        - IDF: precomputed from fit()
        - Final: sum(TF * IDF) for query terms, normalized to [0, 1]

        Args:
            query: Query string
            texts: List of texts to score

        Returns:
            List of scores in [0, 1] range (one per text)

        Raises:
            AssertionError: If scorer not fitted
        """
        assert self._fitted, "TFIDFScorer not fitted"

        # Tokenize query and count term frequencies
        query_tokens = tokenize(query)
        query_term_counts = Counter(query_tokens)

        scores: List[float] = []

        for text in texts:
            # Tokenize text and count term frequencies
            text_tokens = tokenize(text)
            text_tf = Counter(text_tokens)

            # Compute TF-IDF score
            score_raw = 0.0
            for term, query_count in sorted(query_term_counts.items()):  # Deterministic
                if term in self._vocab:
                    vocab_idx = self._vocab[term]
                    idf_value = self._idf[vocab_idx]
                    tf_value = text_tf[term]
                    score_raw += (tf_value * idf_value) * query_count

            # Normalize to [0, 1] using sigmoid
            score_normalized = 1.0 / (1.0 + math.exp(-score_raw))
            scores.append(score_normalized)

        return scores

    def rank(self, query: str, texts: Sequence[str]) -> List[int]:
        """
        Rank texts by TF-IDF score (descending).

        Returns indices of texts sorted by score (highest first).
        Tie-breaking: stable sort by index (lowest index first).

        Args:
            query: Query string
            texts: List of texts to rank

        Returns:
            List of indices sorted by score (descending)
        """
        scores = self.score(query, texts)
        # Sort by (-score, index) for deterministic tie-breaking
        ranked = sorted(enumerate(scores), key=lambda x: (-x[1], x[0]))
        return [idx for idx, _ in ranked]


class BM25Scorer:
    """
    BM25 (Okapi) scorer with sklearn-compatible interface.

    Implements Okapi BM25 ranking function with:
    - Deterministic vocabulary and document frequency tracking
    - Tunable parameters: k1 (term saturation), b (length normalization)
    - Robertson-Sparck Jones IDF formula
    - Score normalization to [0, 1]

    Attributes:
        k1: Term frequency saturation parameter (default 1.2)
        b: Length normalization parameter (default 0.75)
        _avgdl: Average document length in corpus
        _df: Document frequency for each term
        _N: Number of documents in corpus
        _fitted: Whether fit() has been called

    Methods:
        fit(corpus): Compute corpus statistics
        score(query, texts): Return BM25 scores in [0, 1]
        rank(query, texts): Return indices sorted by score
    """

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        """
        Initialize BM25Scorer with parameters.

        Args:
            k1: Term frequency saturation (default 1.2)
            b: Length normalization (default 0.75)

        Raises:
            ValueError: If k1 <= 0 or b not in [0, 1]
        """
        if k1 <= 0 or not (0.0 <= b <= 1.0):
            raise ValueError("Invalid BM25 params")

        self.k1 = k1
        self.b = b
        self._avgdl: float = 0.0
        self._df: Dict[str, int] = {}
        self._N: int = 0
        self._fitted: bool = False

    def fit(self, corpus: Sequence[str]) -> "BM25Scorer":
        """
        Fit BM25 model to corpus (compute DF and avgdl).

        Computes:
        - Document frequency (DF) for each term
        - Average document length (avgdl)
        - Number of documents (N)

        Args:
            corpus: List of documents (strings)

        Returns:
            Self for method chaining
        """
        # Tokenize all documents
        docs_tokens = [tokenize(doc) for doc in corpus]

        # Store corpus size
        self._N = len(corpus)

        # Compute average document length
        total_len = sum(len(tokens) for tokens in docs_tokens)
        self._avgdl = total_len / max(1, self._N) if self._N > 0 else 1.0

        # Count document frequency for each term
        df: Counter[str] = Counter()
        for tokens in docs_tokens:
            # Count each term once per document
            for term in sorted(set(tokens)):  # Deterministic iteration
                df[term] += 1

        self._df = dict(df)
        self._fitted = True
        return self

    def _idf(self, term: str) -> float:
        """
        Compute IDF for term using Robertson-Sparck Jones formula.

        IDF = log((N - df(t) + 0.5) / (df(t) + 0.5) + 1.0)

        Args:
            term: Term to compute IDF for

        Returns:
            IDF value (float)
        """
        df_term = self._df.get(term, 0)
        numerator = self._N - df_term + 0.5
        denominator = df_term + 0.5
        return math.log(numerator / denominator + 1.0)

    def score(self, query: str, texts: Sequence[str]) -> List[float]:
        """
        Score texts against query using BM25.

        BM25 formula:
            score = sum over query terms of:
                IDF(t) * (f(t, D) * (k1 + 1)) / (f(t, D) + k1 * (1 - b + b * |D| / avgdl))

        where:
        - f(t, D) = term frequency in document
        - |D| = document length
        - avgdl = average document length

        Args:
            query: Query string
            texts: List of texts to score

        Returns:
            List of scores in [0, 1] range

        Raises:
            AssertionError: If scorer not fitted
        """
        assert self._fitted, "BM25Scorer not fitted"

        # Tokenize query (unique terms only for scoring)
        query_tokens = tokenize(query)
        query_terms = sorted(set(query_tokens))  # Deterministic order

        scores: List[float] = []

        for text in texts:
            # Tokenize text and count term frequencies
            text_tokens = tokenize(text)
            doc_len = len(text_tokens) if text_tokens else 1
            text_tf = Counter(text_tokens)

            # Compute BM25 score
            score_raw = 0.0
            for term in query_terms:
                idf_value = self._idf(term)
                freq = text_tf[term]

                # BM25 formula components
                numerator = freq * (self.k1 + 1.0)

                # Compute length normalization term
                avgdl_safe = self._avgdl if self._avgdl > 0 else 1.0
                denominator = freq + self.k1 * (
                    1.0 - self.b + self.b * doc_len / avgdl_safe
                )

                if denominator > 0:
                    score_raw += idf_value * numerator / denominator

            # Normalize to [0, 1] using x/(x+1) mapping
            score_normalized = score_raw / (score_raw + 1.0)
            scores.append(score_normalized)

        return scores

    def rank(self, query: str, texts: Sequence[str]) -> List[int]:
        """
        Rank texts by BM25 score (descending).

        Returns indices of texts sorted by score (highest first).
        Tie-breaking: stable sort by index (lowest index first).

        Args:
            query: Query string
            texts: List of texts to rank

        Returns:
            List of indices sorted by score (descending)
        """
        scores = self.score(query, texts)
        # Sort by (-score, index) for deterministic tie-breaking
        ranked = sorted(enumerate(scores), key=lambda x: (-x[1], x[0]))
        return [idx for idx, _ in ranked]
