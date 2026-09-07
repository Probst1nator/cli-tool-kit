"""Group a tool tree into named bands by what the tools are for.

The installer bands its rows by *something*. ``group_by="capability"`` uses the
one word each tool advertises, which needs no computation. This package is the
other option: it reads what a tree already documents about itself and produces
a small set of named categories, which is what you want once a tree has more
tools than a person can scan.

Three tiers, tried in order, so the feature degrades instead of failing:

1. **LLM** — name six categories, file every tool into them, then review the
   result and let the model move misfits and rename a category to match what it
   actually holds. Uses Gemini when ``GEMINI_API_KEY`` is reachable, otherwise a
   local LM Studio / Ollama server. This is the tier that produces good names.
2. **capability** — band the advertised capability words into a fixed set of
   six. No network, no model, instant, and the names are stable.
3. **embed + k-means** — embed the documents and cluster them, naming each
   cluster after its most distinctive token. Names are poor ("git", "clipboard")
   but the tree still opens.

:func:`~cli_tool_kit.taxonomy.groups.ensure_groups` is the entry point a
wrapper's discoverer calls. It fingerprints the tree's documents and rebuilds
only when they changed, so the common case costs a couple of milliseconds.

    from cli_tool_kit.taxonomy import ensure_groups
    groups = ensure_groups(root)      # {tool_name: band label}
"""

from .embedder import EmbeddingUnavailable, embed_texts
from .groups import ensure_groups, load_groups
from .build import build_groups, DEFAULT_K

__all__ = [
    "EmbeddingUnavailable",
    "embed_texts",
    "ensure_groups",
    "load_groups",
    "build_groups",
    "DEFAULT_K",
]
