from discord import File
from pathlib import Path

RESOURCES = Path(__file__).resolve().parent / "resources"

def get_mascot(name: str) -> File:
    assert name.isalpha()
    return File(RESOURCES / "mascots" / f"{name.lower()}.png")

def get_feedback_graphic() -> File:
    return File(RESOURCES / "kowalcritique.png")

def get_forum_header() -> str:
    return (RESOURCES / "forum_header.txt").read_text()

def get_sub_header() -> str:
    return (RESOURCES / "submission_header.txt").read_text()