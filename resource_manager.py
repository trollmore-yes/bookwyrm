import discord
from pathlib import Path

class ResourceManager():
    def __init__(self):
        self.forum_header = "forum_header.txt"
        self.sub_header = "submission_header.txt"
        self.feedback_guide = "kowalcritique.png"

    def get_mascot(self, name):
        if ".." in name:
            raise ValueError(f"Inappropriate resource request '{name}'")

        if Path(f'./resources/mascots/{name.lower()}.png').exists():
            with open(f'resources/mascots/{name.lower()}.png', 'rb') as f:
                return discord.File(f)
        else: 
            raise ValueError(f"could not find mascot image '{name}'")

    def get_feedback_graphic(self):
        with open(f'resources/{self.feedback_guide}', 'rb') as f:
            return discord.File(f)

    def get_forum_header(self):
        with open(f'resources/{self.forum_header}', 'r') as f:
            return f.read()

    def get_sub_header(self):
        with open(f'resources/{self.sub_header}', 'r') as f:
            return f.read()
