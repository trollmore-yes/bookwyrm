import asyncio
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import discord


class TestSlashCommands(unittest.TestCase):
    @staticmethod
    def _load_module():
        original_run = discord.Bot.run
        discord.Bot.run = lambda self, *args, **kwargs: None
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            project_root = Path(__file__).resolve().parent.parent
            sys.path.insert(0, str(project_root))
            spec = importlib.util.spec_from_file_location(
                "bookwyrm_under_test",
                project_root / "bookwyrm.py",
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
        finally:
            asyncio.set_event_loop(None)
            loop.close()
            discord.Bot.run = original_run

    def test_parse_signup_sheet_defers_before_processing(self):
        module = self._load_module()

        class FakeAttachment:
            def __init__(self, filename="source.csv"):
                self.filename = filename

            async def save(self, path):
                Path(path).write_text("test", encoding="utf-8")

        class FakeMessage:
            def __init__(self):
                self.id = 111
                self.reactions = []

            async def add_reaction(self, emoji):
                self.reactions.append(emoji)

        class FakeFollowup:
            def __init__(self):
                self.messages = []
                self.last_message = FakeMessage()

            async def send(self, *args, **kwargs):
                self.messages.append((args, kwargs))
                if "file" in kwargs and hasattr(kwargs["file"], "close"):
                    kwargs["file"].close()
                if "file" in kwargs:
                    return self.last_message
                return None

        class FakeContext:
            def __init__(self):
                self.guild = SimpleNamespace(id=12345)
                self.author = SimpleNamespace(id=99)
                self.deferred = False
                self.followup = FakeFollowup()

            async def defer(self):
                self.deferred = True

        class FakeCompletedProcess:
            def __init__(self, returncode=0):
                self.returncode = returncode
                self.stdout = ""
                self.stderr = ""

        async def run_command():
            ctx = FakeContext()
            attachment = FakeAttachment()
            signup_calls = []

            def fake_run(*args, **kwargs):
                command_args = args[0]
                output_path = Path(command_args[command_args.index("-o") + 1])
                model_path = Path(command_args[command_args.index("--model-output") + 1])
                output_path.write_text("report", encoding="utf-8")
                model_path.write_text(
                    json.dumps(
                        {
                            "group_timestamp": 1700000000,
                            "users": [{"timestamp": 1700000000, "name": "alice"}],
                            "groups": [{"name": "griffins", "members": [{"name": "alice"}]}],
                        }
                    ),
                    encoding="utf-8",
                )
                return FakeCompletedProcess()

            original_run_func = module.subprocess.run
            original_save_signups = module.data_manager.save_signups_to_db
            module.subprocess.run = fake_run

            def fake_save_signups(timestamp, guild_id, users, naughty_list, db_path=None):
                signup_calls.append((timestamp, guild_id, users, naughty_list, db_path))

            module.data_manager.save_signups_to_db = fake_save_signups
            try:
                await module.parse_signup_sheet(ctx, attachment)
            finally:
                module.subprocess.run = original_run_func
                module.data_manager.save_signups_to_db = original_save_signups

            return ctx, signup_calls

        ctx, signup_calls = asyncio.run(run_command())
        self.assertTrue(ctx.deferred)
        self.assertTrue(ctx.followup.messages)
        self.assertEqual(len(signup_calls), 1)
        self.assertEqual(ctx.followup.last_message.reactions, [module.APPROVE_EMOJI, module.REJECT_EMOJI])

    def test_green_check_saves_groups_for_invoker(self):
        module = self._load_module()

        class FakeEmoji:
            def __str__(self):
                return module.APPROVE_EMOJI

        class FakeChannel:
            def __init__(self):
                self.messages = []

            async def send(self, content):
                self.messages.append(content)

        fake_channel = FakeChannel()

        module.PENDING_PARSE_CONFIRMATIONS.clear()
        module.PENDING_PARSE_CONFIRMATIONS[555] = {
            "invoker_id": 123,
            "guild_id": 987,
            "timestamp": 42,
            "model": {
                "users": [{"timestamp": 1234, "name": "alice"}],
                "groups": [{"name": "dragons", "members": [{"name": "alice"}]}],
            },
            "saved": False,
        }

        module.bot.get_channel = lambda _channel_id: fake_channel

        saved_calls = []

        original_init_database = module.data_manager.init_database
        original_save_groups = module.data_manager.save_groups_to_db
        module.data_manager.init_database = lambda db_path=None: None

        def fake_save_groups(timestamp, guild_id, groups, db_path=None):
            saved_calls.append((timestamp, guild_id, groups, db_path))

        module.data_manager.save_groups_to_db = fake_save_groups

        payload = SimpleNamespace(
            message_id=555,
            user_id=123,
            channel_id=1,
            emoji=FakeEmoji(),
        )

        async def run_event():
            await module.on_raw_reaction_add(payload)

        try:
            asyncio.run(run_event())
        finally:
            module.data_manager.init_database = original_init_database
            module.data_manager.save_groups_to_db = original_save_groups

        self.assertEqual(len(saved_calls), 1)
        self.assertNotIn(555, module.PENDING_PARSE_CONFIRMATIONS)
        self.assertTrue(any("Saved parsed groups" in message for message in fake_channel.messages))


if __name__ == "__main__":
    unittest.main()
