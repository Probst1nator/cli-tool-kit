"""Group tools by the capability word they advertise. No network, no model.

The last tier of the grouping chain, and the only one that works on a host with
no API key and no local embedding server — which is every host but this fleet's,
since the key is read from the repo's own .env. A distributed checkout gets its
bands from the committed data/tool_groups.json; this is what happens when
someone then adds a tool of their own.

Two modes. With an existing grouping it is *incremental*: the stored bands and
their names are kept exactly as they are, and only tools missing from them are
filed, next to whichever band already holds their capability. Without one it
builds the bands from DEFAULT_BANDS below.
"""

from typing import Dict, List, Optional, Sequence, Tuple

# Every word in validate_structure.CAPABILITY_VOCAB has a home here. A tool
# whose capability is missing or outside the vocabulary lands in the smallest
# band, which is the honest answer: nothing about it says where it belongs.
DEFAULT_BANDS: Dict[str, Tuple[str, ...]] = {
    "AI & Chat": ("agent", "llm-chat", "chat"),
    "Audio & Speech": ("tts", "stt", "audio-visualizer"),
    "Vision & Creation": ("image-gen", "image-edit", "ocr", "vision-search"),
    "Media & Publishing": (
        "scrape", "summarize", "download", "media-launcher", "publish",
        "pdf-extract",
    ),
    "Developer Tools": (
        "commit-gen", "dep-check", "forge", "repo-hygiene", "finetune",
    ),
    "System & Context": ("smarthome", "vnc-display", "context-picker"),
}

_BAND_OF_CAPABILITY = {
    capability: band
    for band, capabilities in DEFAULT_BANDS.items()
    for capability in capabilities
}


def _smallest(labels: Dict[str, List[str]]) -> str:
    """Name of the least populated band, ties broken alphabetically."""
    return min(labels, key=lambda band: (len(labels[band]), band))


def capability_groups(
    capabilities: Dict[str, str],
    existing: Optional[Dict[str, Sequence[str]]] = None,
) -> Dict[str, List[str]]:
    """Band name -> members, decided by each tool's capability word.

    ``existing`` is a stored grouping to extend rather than replace: its band
    names survive untouched, tools that no longer exist are dropped, and only
    the newcomers are placed.
    """
    if not capabilities:
        return {}

    if existing:
        labels = {
            band: [tool for tool in members if tool in capabilities]
            for band, members in existing.items()
        }
        labels = {band: members for band, members in labels.items() if members}
    else:
        labels = {}

    if not labels:
        for tool, capability in capabilities.items():
            band = _BAND_OF_CAPABILITY.get(capability)
            if band:
                labels.setdefault(band, []).append(tool)
        if not labels:
            labels = {"AI & Chat": []}

    # Which band already holds each capability, and each family of related
    # capabilities, by weight of numbers.
    home: Dict[str, Dict[str, int]] = {}
    family: Dict[str, Dict[str, int]] = {}

    def _record(capability: str, band: str) -> None:
        if not capability:
            return
        home.setdefault(capability, {})
        home[capability][band] = home[capability].get(band, 0) + 1
        default = _BAND_OF_CAPABILITY.get(capability)
        if default:
            family.setdefault(default, {})
            family[default][band] = family[default].get(band, 0) + 1

    for band, members in labels.items():
        for tool in members:
            _record(capabilities.get(tool, ""), band)

    def _pick(counts: Dict[str, int]) -> str:
        return max(counts, key=lambda band: (counts[band], band))

    for tool in sorted(capabilities):
        if any(tool in members for members in labels.values()):
            continue
        capability = capabilities[tool]
        default = _BAND_OF_CAPABILITY.get(capability)
        if home.get(capability):
            # A band already holds this exact capability.
            band = _pick(home[capability])
        elif default and family.get(default):
            # No exact match, but a band holds its siblings: stt joins tts.
            band = _pick(family[default])
        elif default in labels:
            band = default
        else:
            band = _smallest(labels)
        labels[band].append(tool)
        _record(capability, band)

    return {band: sorted(members) for band, members in labels.items() if members}
