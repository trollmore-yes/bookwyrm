from resource_manager import ResourceManager

class ChannelManager():
    def __init__(self, rm : ResourceManager):
        self.discussion_forum = None
        self.submission_forum = None
        self.guild_id = None
        self.rm = rm

    def set_channels(self, disc, sub):
        self.discussion_forum = disc
        self.submission_forum = sub

    async def build_discussion_thread(self, name="HippoHammer", sub_thread=None):
        mascot = self.rm.get_mascot(name)
        feedback_guide = self.rm.get_feedback_graphic()

        forum_header = self.rm.get_forum_header()

        if sub_thread:
            forum_header += "\n\nYour submission thread is here:"
            forum_header += f"\n\nhttps://discord.com/channels/{self.guild_id}/{sub_thread.id}"

        return await self.discussion_forum.create_thread(name=name, content=forum_header, files=[mascot, feedback_guide])

    async def build_submission_thread(self, name="HippoHammer"):
        mascot = self.rm.get_mascot(name)
        return await self.submission_forum.create_thread(name=name, content=self.rm.get_sub_header(), file=mascot)

    async def build_group_threads(self, name="HippoHammer"):
        try:
            sub_thread = await self.build_submission_thread(name=name)
            disc_thread = await self.build_discussion_thread(name=name, sub_thread=sub_thread)
            return disc_thread, sub_thread
        except ValueError:
            print(f"could not find mascot image for '{name}")