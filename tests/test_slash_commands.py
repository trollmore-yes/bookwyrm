import asyncio
import importlib.util
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
                self.channel = SimpleNamespace(id=777)
                self.deferred = False
                self.followup = FakeFollowup()

            async def defer(self):
                self.deferred = True

        async def run_command():
            ctx = FakeContext()
            attachment = FakeAttachment()
            signup_calls = []

            class FakeSignupManager:
                def __init__(self):
                    self._model = {
                        "group_timestamp": 1700000000,
                        "users": [{"timestamp": 1700000000, "name": "alice"}],
                        "groups": [{"name": "griffins", "members": [{"name": "alice"}]}],
                    }

                def process(self, input_path="source.csv", output_path=None, model_output_path=None):
                    assert output_path is not None
                    Path(output_path).write_text("report", encoding="utf-8")
                    return output_path

                def build_model_payload(self):
                    return self._model

            original_loader = getattr(module, "_load_parse_sheet_module")
            original_save_signups = module.data_manager.save_signups_to_db
            setattr(module, "_load_parse_sheet_module", lambda: SimpleNamespace(SignupManager=FakeSignupManager))

            def fake_save_signups(timestamp, guild_id, users, naughty_list, db_path=None):
                signup_calls.append((timestamp, guild_id, users, naughty_list, db_path))

            module.data_manager.save_signups_to_db = fake_save_signups
            try:
                await module.parse_signup_sheet(ctx, attachment)
            finally:
                setattr(module, "_load_parse_sheet_module", original_loader)
                module.data_manager.save_signups_to_db = original_save_signups

            for pending in module.PENDING_MODEL_REVIEWS.values():
                timeout_task = pending.get("timeout_task")
                if timeout_task is not None and not timeout_task.done():
                    timeout_task.cancel()
            module.PENDING_MODEL_REVIEWS.clear()

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

        class FakeThread:
            def __init__(self, thread_id):
                self.id = thread_id

        fake_channel = FakeChannel()

        module.PENDING_MODEL_REVIEWS.clear()
        module.PENDING_MODEL_REVIEWS[555] = {
            "invoker_id": 123,
            "guild_id": 987,
            "channel_id": 1,
            "timestamp": 42,
            "model": {
                "users": [{"timestamp": 1234, "name": "alice"}],
                "groups": [{"name": "dragons", "members": [{"name": "alice"}]}],
            },
            "saved": False,
            "timeout_task": SimpleNamespace(done=lambda: True, cancel=lambda: None),
        }

        module.bot.get_channel = lambda _channel_id: fake_channel

        saved_calls = []

        original_init_database = module.data_manager.init_database
        original_save_groups = module.data_manager.save_groups_to_db
        original_build_group_threads = module.cm.build_group_threads
        module.data_manager.init_database = lambda db_path=None: None

        async def fake_build_group_threads(name="", guild=None):
            return FakeThread(31415), FakeThread(27182)

        def fake_save_groups(timestamp, guild_id, groups, db_path=None):
            saved_calls.append((timestamp, guild_id, groups, db_path))

        module.data_manager.save_groups_to_db = fake_save_groups
        module.cm.build_group_threads = fake_build_group_threads

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
            module.cm.build_group_threads = original_build_group_threads

        self.assertEqual(len(saved_calls), 1)
        self.assertEqual(saved_calls[0][2][0]["thread_id"], 31415)
        self.assertNotIn(555, module.PENDING_MODEL_REVIEWS)
        self.assertTrue(any("Saved parsed groups" in message for message in fake_channel.messages))

    def test_red_x_moves_model_to_editable_memory(self):
        module = self._load_module()

        class FakeEmoji:
            def __str__(self):
                return module.REJECT_EMOJI

        class FakeChannel:
            def __init__(self):
                self.messages = []
                self.guild = SimpleNamespace(id=987)

            async def send(self, content):
                self.messages.append(content)

        fake_channel = FakeChannel()
        module.bot.get_channel = lambda _channel_id: fake_channel

        module.PENDING_MODEL_REVIEWS.clear()
        module.EDITABLE_MODELS.clear()
        pending_model = {
            "users": [{"timestamp": 1234, "name": "alice"}],
            "groups": [{"name": "dragons", "members": [{"name": "alice"}]}],
        }
        module.PENDING_MODEL_REVIEWS[777] = {
            "invoker_id": 123,
            "guild_id": 987,
            "channel_id": 1,
            "timestamp": 42,
            "model": pending_model,
            "saved": False,
            "timeout_task": SimpleNamespace(done=lambda: True, cancel=lambda: None),
        }

        payload = SimpleNamespace(
            message_id=777,
            user_id=123,
            channel_id=1,
            emoji=FakeEmoji(),
        )

        async def run_event():
            await module.on_raw_reaction_add(payload)

        asyncio.run(run_event())

        self.assertNotIn(777, module.PENDING_MODEL_REVIEWS)
        self.assertEqual(module.EDITABLE_MODELS[(987, 123)], pending_model)

    def test_edit_groups_uses_rejected_model(self):
        module = self._load_module()

        class FakeFollowup:
            def __init__(self):
                self.messages = []

            async def send(self, *args, **kwargs):
                self.messages.append((args, kwargs))
                return None

        class FakeContext:
            def __init__(self):
                self.guild = SimpleNamespace(id=987)
                self.author = SimpleNamespace(id=123)
                self.channel = SimpleNamespace(id=1)
                self.deferred = False
                self.followup = FakeFollowup()

            async def defer(self):
                self.deferred = True

        module.EDITABLE_MODELS.clear()
        module.EDITABLE_MODELS[(987, 123)] = {
            "group_timestamp": 1234,
            "users": [{"timestamp": 1234, "name": "alice"}],
            "groups": [{"name": "oldgroup", "members": [{"name": "alice"}]}],
        }

        sent_models = []
        original_parse_groups = getattr(module, "_parse_groups_list")
        original_rebuild = getattr(module, "_rebuild_model_from_groups")
        original_render = getattr(module, "_render_report_text")
        original_send_review = getattr(module, "_send_review_response")

        setattr(module, "_parse_groups_list", lambda _text: [{"name": "dragons", "members": [{"name": "alice"}]}])
        setattr(module, "_rebuild_model_from_groups", lambda _base, _groups: {
            "group_timestamp": 1234,
            "users": [{"timestamp": 1234, "name": "alice"}],
            "groups": [{"name": "dragons", "members": [{"name": "alice"}]}],
        })
        setattr(module, "_render_report_text", lambda _model: "GROUPS:\n - dragons: alice\n")

        async def fake_send_review(ctx, model_payload, report_path):
            sent_models.append((ctx, model_payload, report_path))

        setattr(module, "_send_review_response", fake_send_review)

        async def run_command():
            ctx = FakeContext()
            await module.edit_groups(ctx, "GROUPS: - dragons: alice;")
            return ctx

        try:
            ctx = asyncio.run(run_command())
        finally:
            setattr(module, "_parse_groups_list", original_parse_groups)
            setattr(module, "_rebuild_model_from_groups", original_rebuild)
            setattr(module, "_render_report_text", original_render)
            setattr(module, "_send_review_response", original_send_review)

        self.assertTrue(ctx.deferred)
        self.assertEqual(len(sent_models), 1)
        self.assertEqual(sent_models[0][1]["groups"][0]["name"], "dragons")

    def test_parse_groups_list_accepts_semicolons(self):
        module = self._load_module()
        parsed = module._parse_groups_list("GROUPS: - dragons: alice, bob; - lions: cara")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "dragons")
        self.assertEqual(parsed[0]["members"][0]["name"], "alice")
        self.assertEqual(parsed[1]["name"], "lions")


if __name__ == "__main__":
    unittest.main()
