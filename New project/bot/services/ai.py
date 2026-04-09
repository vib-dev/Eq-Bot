from __future__ import annotations

import re


KEYWORDS = {
    "revenue", "ebitda", "pat", "profit", "order", "capex", "guidance",
    "board", "fund raise", "acquisition", "merger", "expansion", "traffic",
    "passenger", "load factor", "margin", "approval", "contract",
}


class HeuristicSummarizer:
    def summarize(self, title: str, text: str) -> tuple[str, list[str]]:
        cleaned = " ".join((title + ". " + text).split())
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        summary = self._compress(sentences[0] if sentences else title)
        points: list[str] = []
        for sentence in sentences[1:]:
            compact = sentence.strip()
            if not compact:
                continue
            if any(keyword in compact.lower() for keyword in KEYWORDS):
                points.append(self._compress(compact[:220]))
            if len(points) == 5:
                break
        if not points:
            points = [self._compress(segment[:200]) for segment in sentences[1:4] if segment.strip()]
        return summary[:280], points[:5]

    def answer(self, question: str, context: list[str]) -> str:
        if not context:
            return "I do not have matching stored updates yet."
        lead = " ".join(context[:6])
        return f"Based on stored updates: {lead[:900]} Question asked: {question.strip()}"

    def _compress(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"(?i)\b(the company|the board of directors|the board)\b", "", text)
        text = re.sub(r"\s{2,}", " ", text).strip(" .,-")
        return text
