from resources import get_mascot, get_feedback_graphic, get_forum_header, get_sub_header
from datetime import datetime

# coteh values
# default_discussion_forum = 1201013058412216370 
# default_submission_forum = 1201013167443157132

# test server values
default_discussion_forum_id = 1335404321008779304
default_submission_forum_id = 1335404176381050922

class ChannelManager():
    def __init__(self):
        self.discussion_forum_id = default_discussion_forum_id
        self.submission_forum_id = default_submission_forum_id
        self.discussion_forum = None
        self.submission_forum = None
        self.guild_id = None

    def set_channels(self, disc, sub):
        """
        Sets the discussion thread and submission thread to the given values
        returns: None
        """
        if hasattr(disc, "id"):
            self.discussion_forum = disc
            self.discussion_forum_id = disc.id
        else:
            self.discussion_forum = None
            self.discussion_forum_id = int(disc)

        if hasattr(sub, "id"):
            self.submission_forum = sub
            self.submission_forum_id = sub.id
        else:
            self.submission_forum = None
            self.submission_forum_id = int(sub)

    async def _resolve_forum_channel(self, guild, forum_id, cached_forum, channel_name):
        if cached_forum is not None:
            cached_id = getattr(cached_forum, "id", None)
            if cached_id == forum_id and hasattr(cached_forum, "create_thread"):
                return cached_forum

        if guild is None:
            raise ValueError(
                f"Cannot resolve {channel_name} channel object without guild context. "
                "Use /set_forum_ids first or provide guild when building threads."
            )

        forum_channel = guild.get_channel(forum_id)
        if forum_channel is None:
            forum_channel = await guild.fetch_channel(forum_id)

        if forum_channel is None or not hasattr(forum_channel, "create_thread"):
            raise ValueError(f"Configured {channel_name} channel ({forum_id}) is not a forum channel")

        return forum_channel

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

    async def build_discussion_thread(self, name: str="HippoHammer", sub_thread=None, guild=None):
        """
        Creates a thread in the Channel Manager's discussion channel:
            - Uses the Resource Manager to pull mascot, infographic, and forum header
            - Appends link to submission thread if supplied
            - Names thread with provided name and current month/year

        Returns: the created thread  
        """
        if guild is not None:
            self.guild_id = guild.id

        self.discussion_forum = await self._resolve_forum_channel(
            guild,
            self.discussion_forum_id,
            self.discussion_forum,
            "discussion forum",
        )

        mascot = get_mascot(name)
        feedback_guide = get_feedback_graphic()
        forum_header = get_forum_header()

        if sub_thread:
            forum_header += "\n\nYour submission thread is here:"
            forum_header += f"\n\n{self.get_thread_link_from_id(sub_thread.id)}"

        now = datetime.now()
        month = now.month
        year = f"{now.year}"[2:]


        thread_name = f"{name} Discussion {month}/{year}"

        return await self.discussion_forum.create_thread(name=thread_name, content=forum_header, files=[mascot, feedback_guide])

    async def build_submission_thread(self, name: str="HippoHammer", guild=None):
        """
        Creates a thread in the Channel Manager's submission channel:
            - Uses the Resource Manager to pull mascot and forum header
            - Names thread with provided name and current month/year

        Returns: the created thread  
        """
        if guild is not None:
            self.guild_id = guild.id

        self.submission_forum = await self._resolve_forum_channel(
            guild,
            self.submission_forum_id,
            self.submission_forum,
            "submission forum",
        )

        mascot = get_mascot(name)
        now = datetime.now()
        month = now.month
        year = f"{now.year}"[2:]
        thread_name = f"{name} Submissions {month}/{year}"
        return await self.submission_forum.create_thread(name=thread_name, content=get_sub_header(), files=[mascot])

    async def build_group_threads(self, name="HippoHammer", guild=None):
        """
        Builds and returns discussion and submission threads for the given group.
        """

        try:
            if guild is not None:
                self.guild_id = guild.id

            sub_thread = await self.build_submission_thread(name=name, guild=guild)
            disc_thread = await self.build_discussion_thread(name=name, sub_thread=sub_thread, guild=guild)
            return disc_thread, sub_thread
        except ValueError:
            raise ValueError(f"could not find mascot image for '{name}")
