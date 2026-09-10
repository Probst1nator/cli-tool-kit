"""Deterministic k-means over normalised vectors, plus group labelling.

Pure python, no numpy, so the result is identical on every host. Vectors are
L2-normalised, which makes squared euclidean distance a stand-in for cosine
distance.
"""

import math
import random
import re
from typing import Dict, List, Sequence, Tuple

STOPWORDS = {
    "a", "about", "after", "all", "also", "an", "and", "any", "are", "as", "at",
    "back", "be", "because", "been", "before", "being", "below", "between",
    "both", "but", "by", "can", "claude", "code", "com", "d", "de", "did", "do",
    "does", "doing", "done", "each", "etc", "even", "every", "few", "file",
    "files", "for", "from", "get", "gets", "github", "had", "has", "have", "he",
    "her", "here", "how", "http", "https", "i", "if", "in", "install", "into",
    "is", "it", "its", "just", "like", "made", "main", "make", "makes", "many",
    "md", "more", "most", "must", "my", "need", "needs", "new", "no", "not",
    "now", "of", "off", "on", "once", "one", "only", "or", "other", "our",
    "out", "over", "own", "path", "py", "python", "readme", "repo", "run",
    "runs", "same", "script", "see", "set", "she", "should", "since", "so",
    "some", "still", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "tool",
    "tools", "two", "under", "until", "up", "us", "use", "used", "uses",
    "using", "very", "was", "way", "we", "were", "what", "when", "where",
    "python3", "json", "name", "names", "default", "defaults", "example",
    "examples", "args", "arg", "note", "notes", "directory", "dir", "output",
    "which", "while", "who", "why", "will", "with", "would", "you", "your",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize(vectors: Sequence[Sequence[float]]) -> List[List[float]]:
    """Scale every vector to unit length."""
    out = []
    for vec in vectors:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            out.append([0.0] * len(vec))
        else:
            out.append([x / norm for x in vec])
    return out


def _sqdist(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((x - y) * (x - y) for x, y in zip(a, b))


def _kmeans_plusplus(vectors: List[List[float]], k: int, rng: random.Random) -> List[List[float]]:
    """Pick k starting centroids, spread out, using the given rng."""
    first = rng.randrange(len(vectors))
    centroids = [list(vectors[first])]
    while len(centroids) < k:
        dists = [min(_sqdist(v, c) for c in centroids) for v in vectors]
        total = sum(dists)
        if total <= 0.0:
            centroids.append(list(vectors[rng.randrange(len(vectors))]))
            continue
        target = rng.random() * total
        running = 0.0
        chosen = len(vectors) - 1
        for i, d in enumerate(dists):
            running += d
            if running >= target:
                chosen = i
                break
        centroids.append(list(vectors[chosen]))
    return centroids


def _assign(vectors: List[List[float]], centroids: List[List[float]]) -> List[int]:
    """Assign each vector to its nearest centroid."""
    labels = []
    for vec in vectors:
        best, best_d = 0, None
        for ci, cen in enumerate(centroids):
            d = _sqdist(vec, cen)
            if best_d is None or d < best_d:
                best, best_d = ci, d
        labels.append(best)
    return labels


def _assign_balanced(
    vectors: List[List[float]], centroids: List[List[float]], cap: int
) -> List[int]:
    """Assign vectors nearest-first, never letting a cluster exceed cap."""
    pairs = []
    for vi, vec in enumerate(vectors):
        for ci, cen in enumerate(centroids):
            pairs.append((_sqdist(vec, cen), vi, ci))
    pairs.sort()

    labels = [-1] * len(vectors)
    sizes = [0] * len(centroids)
    placed = 0
    for _, vi, ci in pairs:
        if labels[vi] != -1 or sizes[ci] >= cap:
            continue
        labels[vi] = ci
        sizes[ci] += 1
        placed += 1
        if placed == len(vectors):
            break
    # Anything left over (all its clusters full) goes to the emptiest cluster.
    for vi, lab in enumerate(labels):
        if lab == -1:
            ci = min(range(len(centroids)), key=lambda c: (sizes[c], c))
            labels[vi] = ci
            sizes[ci] += 1
    return labels


def _recentre(
    vectors: List[List[float]], labels: List[int], centroids: List[List[float]]
) -> List[List[float]]:
    """Move each centroid to the mean of its members, normalised."""
    dim = len(vectors[0])
    sums = [[0.0] * dim for _ in centroids]
    counts = [0] * len(centroids)
    for vec, lab in zip(vectors, labels):
        counts[lab] += 1
        row = sums[lab]
        for i, x in enumerate(vec):
            row[i] += x
    new = []
    for ci, count in enumerate(counts):
        if count == 0:
            new.append(list(centroids[ci]))
        else:
            new.append([x / count for x in sums[ci]])
    return normalize(new)


def kmeans(
    vectors: Sequence[Sequence[float]],
    k: int,
    seed: int = 0,
    iters: int = 50,
    balanced: bool = True,
) -> List[int]:
    """Cluster vectors into k groups and return one cluster index per vector.

    With balanced=True no cluster grows past ceil(N/k)+1 members.
    """
    points = normalize(vectors)
    n = len(points)
    if n == 0:
        return []
    k = max(1, min(k, n))
    cap = math.ceil(n / k) + 1

    rng = random.Random(seed)
    centroids = _kmeans_plusplus(points, k, rng)

    labels = []
    for _ in range(iters):
        if balanced:
            new_labels = _assign_balanced(points, centroids, cap)
        else:
            new_labels = _assign(points, centroids)
        if new_labels == labels:
            break
        labels = new_labels
        centroids = _recentre(points, labels, centroids)
    return labels


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens, stopwords and 1-2 char words dropped."""
    return [
        t
        for t in _TOKEN_RE.findall(text.lower())
        if len(t) > 2 and t not in STOPWORDS and not t.isdigit()
    ]


def label_group(
    group_docs: Sequence[str], other_docs: Sequence[str], top: int = 1
) -> str:
    """Name a group by its most distinctive tokens, joined with ' · '.

    ``top`` is how many tokens the name may carry; one by default.
    """
    if not group_docs:
        return "Ungrouped"

    def doc_freq(docs):
        counts = {}
        for doc in docs:
            for token in set(tokenize(doc)):
                counts[token] = counts.get(token, 0) + 1
        return counts

    def term_freq(docs):
        counts = {}
        for doc in docs:
            for token in tokenize(doc):
                counts[token] = counts.get(token, 0) + 1
        return counts

    inside_df = doc_freq(group_docs)
    inside_tf = term_freq(group_docs)
    outside_df = doc_freq(other_docs)
    n_in = len(group_docs)
    n_out = max(1, len(other_docs))

    # A token found in only one document of a multi-document group names that
    # document, not the group, so require two documents whenever we can.
    min_docs = 2 if n_in > 2 else 1

    scored = []
    for token, docs_with in inside_df.items():
        if docs_with < min_docs:
            continue
        tf = inside_tf[token] / n_in
        spread = docs_with / n_in
        idf = math.log((n_out + 1) / (outside_df.get(token, 0) + 1)) + 1.0
        scored.append((-(tf * spread * idf), token))
    scored.sort()
    picked = [token for _, token in scored[:top]]
    return " · ".join(picked) if picked else "Ungrouped"


def cluster_documents(
    names: Sequence[str],
    vectors: Sequence[Sequence[float]],
    docs: Dict[str, str],
    k: int,
    seed: int = 0,
    balanced: bool = True,
    top: int = 1,
) -> List[Tuple[str, List[str]]]:
    """Cluster the tools and return (label, members) per group."""
    labels = kmeans(vectors, k, seed=seed, balanced=balanced)
    buckets: Dict[int, List[str]] = {}
    for name, lab in zip(names, labels):
        buckets.setdefault(lab, []).append(name)

    groups = []
    for lab in sorted(buckets):
        members = sorted(buckets[lab])
        inside = [docs.get(m, "") for m in members]
        outside = [docs.get(n, "") for n in names if n not in set(members)]
        groups.append((label_group(inside, outside, top=top), members))

    # Two clusters can land on the same tokens; keep the labels unique.
    seen = {}
    unique = []
    for label, members in groups:
        if label in seen:
            seen[label] += 1
            label = f"{label} ({seen[label]})"
        else:
            seen[label] = 1
        unique.append((label, members))
    return unique
