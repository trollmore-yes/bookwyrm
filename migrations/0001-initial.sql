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
    name TEXT NOT NULL,
    words_writing INTEGER NOT NULL,
    words_reading INTEGER NOT NULL,
    genres_writing TEXT NOT NULL,
    genres_reading TEXT NOT NULL,
    cw_writing TEXT NOT NULL,
    cw_veto TEXT NOT NULL,
    size_preference TEXT NOT NULL,
    match_request TEXT,
    match_veto TEXT,
    prev_month_status TEXT,
    prev_group_name TEXT,
    crit_history INTEGER NOT NULL,
    completed_book INTEGER NOT NULL,
    quiz_passed INTEGER NOT NULL,
    chapter_links TEXT,
    PRIMARY KEY (timestamp, guild_id, name)
) STRICT;

CREATE TABLE groups (
    timestamp INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    mascot TEXT NOT NULL,
    thread_id INTEGER NOT NULL UNIQUE,
    member_ids TEXT NOT NULL,
    PRIMARY KEY (timestamp, guild_id, mascot)
) STRICT;
