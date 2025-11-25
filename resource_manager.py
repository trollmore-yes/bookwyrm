import discord

class ResourceManager():
    def __init__(self):
        self.forum_header = "forum_header.txt"
        self.sub_header = "submission_header.txt"
        self.feedback_guide = "kowalcritique.png"

        self.mascot_images = {
            "Aardvarktillery" : "Aardvarktillery_Kerry.png",
            "Axelotl" : "Axelotl_Kerry.png",
            "BadgerPunch" : "BadgerPunch_Kerry.png",
            "BunnyBomb" : "BunnyBomb_Kerry.png",
            "FalchionFish" : "FalchionFish_Kerry.png",
            "FoxSpear" : "FoxSpear_Kerry.png",
            "GatlingGoose" : "GatlingGoose_Kerry.png",
            "GrenadeFly" : "Gadfly_Grenade_Kerry.png",
            "GlockCroc" : "GlockCroc_Kerry.png",
            "GunMouse" : "GunMouse_Kerry.png",
            "HippoHammer" : "HippoHammer_Kerry.png",
            "Newtclear" : "Newtclear_Kerry.png",
            "ScytheSnake" : "ScytheSnake_Kerry.png",
            "ShurikenShark" : "ShurikenShark_Kerry.png",
            "TadPolearm" : "TadPolearm_Kerry.png",
            "WarTurtle" : "Warturtle_Kerry.png"
        }


    def get_mascot(self, name):
        with open(f'resources/{self.mascot_images[name]}', 'rb') as f:
            return discord.File(f)

    def get_feedback_graphic(self):
        with open(f'resources/{self.feedback_guide}', 'rb') as f:
            return discord.File(f)

    def get_forum_header(self):
        with open(f'resources/{self.forum_header}', 'r') as f:
            return f.read()

    def get_sub_header(self):
        with open(f'resources/{self.sub_header}', 'r') as f:
            return f.read()
