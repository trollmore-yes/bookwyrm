class ChannelManager():
    def __init__(self, rm : ResourceManager):
        self.discussion_forum = None
        self.submission_forum = None
        self.rm = rm

    def set_channels(self, disc, sub):
        self.discussion_forum = disc
        self.submission_forum = sub

    def build_discussion_thread(self, name="HippoHammer"):
        

        return await self.discussion_forum.create_thread(name=name, content="test thread")
