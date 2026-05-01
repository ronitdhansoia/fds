"""MigrantMoney — Python data pipeline.

Stages: ingest -> preprocess -> tci -> stablecoin -> regression -> aggregate -> export.
See the methodology page (§5) for the locked formulas.
"""
from __future__ import annotations

__version__ = "0.1.0"
