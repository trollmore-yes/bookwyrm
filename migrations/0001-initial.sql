CREATE TABLE guilds (
    guild_id INTEGER PRIMARY KEY,
    discussion_channel_id INTEGER NOT NULL,
    submission_channel_id INTEGER NOT NULL
) STRICT;

CREATE TABLE roles (
    guild_id INTEGER NOT NULL,
    mascot TEXT NOT NULL,
    role INTEGER NOT NULL UNIQUE,
    PRIMARY KEY (guild_id, mascot)
) STRICT;

CREATE TABLE signups (
    timestamp INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    genres JSONB NOT NULL,
    preferred_size TEXT NOT NULL CHECK (preferred_size IN ('small', 'medium', 'large')),
    PRIMARY KEY (timestamp, guild_id, user_id)
) STRICT;

CREATE TABLE groups (
    timestamp INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    mascot TEXT NOT NULL,
    thread_id INTEGER NOT NULL UNIQUE,
    member_ids JSONB NOT NULL,
    PRIMARY KEY (timestamp, guild_id, mascot),
) STRICT;
