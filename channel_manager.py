from resource_manager import ResourceManager
from datetime import datetime

class ChannelManager():
    def __init__(self, rm : ResourceManager):
        self.discussion_forum = None
        self.submission_forum = None
        self.guild_id = None
        self.rm = rm

    def set_channels(self, disc, sub):
        """
        Sets the discussion thread and submission thread to the given values
        returns: None
        """
        self.discussion_forum = disc
        self.submission_forum = sub

    def get_thread_link_from_obj(self, thread):
        """
        Given a thread object, constructs and returns a URL using the 
        guild_id value in the channel manager.
        Raises an exception if guild_id isn't set.
        """
        return self.get_thread_link_from_id(thread.id)

    def get_thread_link_from_id(self, id):
        """
        Given a thread id, constructs and returns a URL using the
        guild_id value in the channel manager.
        Raises an exception if guild_id isn't set.
        """
        if not self.guild_id:
            raise Exception("Need to set ids")
        return f"https://discord.com/channels/{self.guild_id}/{id}"

    async def build_discussion_thread(self, name="HippoHammer", sub_thread=None):
        """
        Creates a thread in the Channel Manager's discussion channel:
            - Uses the Resource Manager to pull mascot, infographic, and forum header
            - Appends link to submission thread if supplied
            - Names thread with provided name and current month/year

        Returns: the created thread  
        """
        mascot = self.rm.get_mascot(name)
        feedback_guide = self.rm.get_feedback_graphic()
        forum_header = self.rm.get_forum_header()

        if sub_thread:
            forum_header += "\n\nYour submission thread is here:"
            forum_header += f"\n\n{self.get_thread_link_from_id(sub_thread.id)}"

        now = datetime.now()
        month = now.month
        year = now.year

        thread_name = f"{name} Discussion {month}/{year}"

        return await self.discussion_forum.create_thread(name=thread_name, content=forum_header, files=[mascot, feedback_guide])

    async def build_submission_thread(self, name="HippoHammer"):
        """
        Creates a thread in the Channel Manager's submission channel:
            - Uses the Resource Manager to pull mascot and forum header
            - Names thread with provided name and current month/year

        Returns: the created thread  
        """
        mascot = self.rm.get_mascot(name)
        now = datetime.now()
        month = now.month
        year = now.year
        thread_name = f"{name} Submissions {month}/{year}"
        return await self.submission_forum.create_thread(name=thread_name, content=self.rm.get_sub_header(), file=mascot)

    async def build_group_threads(self, name="HippoHammer"):
        """
        Builds and returns discussion and submission threads for the given group.
        """

        try:
            sub_thread = await self.build_submission_thread(name=name)
            disc_thread = await self.build_discussion_thread(name=name, sub_thread=sub_thread)
            return disc_thread, sub_thread
        except ValueError:
            print(f"could not find mascot image for '{name}")