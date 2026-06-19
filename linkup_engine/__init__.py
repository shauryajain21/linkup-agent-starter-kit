"""
linkup_engine — the shared core every agent in this kit is built on.

    from linkup_engine import Linkup, get_llm

Linkup is the engine (fresh facts from the live web); the LLM is the reasoning
layer on top. Keep that split and your agents stay simple and swappable.
"""

from .client import Depth, Linkup, LinkupError, OutputType, ReasoningDepth, ResearchMode
from .llm import LLM, get_llm

__all__ = [
    "Linkup",
    "LinkupError",
    "Depth",
    "OutputType",
    "ResearchMode",
    "ReasoningDepth",
    "LLM",
    "get_llm",
]
