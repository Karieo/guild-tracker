-- Timestamps are UTC, 'YYYY-MM-DD HH:MM:SS' (same format as CURRENT_TIMESTAMP).

CREATE TABLE users (
    id          INTEGER PRIMARY KEY,
    discord_id  TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    avatar      TEXT,
    role        TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'officer', 'owner')),
    timezone    TEXT NOT NULL DEFAULT 'America/Chicago',
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Game data lives in tables so it can be edited without a code change.
CREATE TABLE game_classes (
    name   TEXT PRIMARY KEY,
    color  TEXT NOT NULL,
    sort   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE races (
    name     TEXT PRIMARY KEY,
    faction  TEXT NOT NULL CHECK (faction IN ('Horde', 'Alliance')),
    sort     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE professions (
    name  TEXT PRIMARY KEY,
    kind  TEXT NOT NULL CHECK (kind IN ('primary', 'secondary')),
    sort  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE characters (
    id                INTEGER PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    class_name        TEXT NOT NULL,
    race              TEXT NOT NULL,
    role              TEXT NOT NULL CHECK (role IN ('Tank', 'Healer', 'DPS')),
    spec_note         TEXT NOT NULL DEFAULT '',
    level             INTEGER NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 60),
    level_updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_main           INTEGER NOT NULL DEFAULT 0 CHECK (is_main IN (0, 1)),
    status            TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'leveling', '60')),
    notes             TEXT NOT NULL DEFAULT ''
);
CREATE INDEX characters_user ON characters(user_id);
-- At most one main per user.
CREATE UNIQUE INDEX characters_one_main ON characters(user_id) WHERE is_main = 1;

CREATE TABLE character_professions (
    id            INTEGER PRIMARY KEY,
    character_id  INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    profession    TEXT NOT NULL REFERENCES professions(name),
    skill         INTEGER NOT NULL DEFAULT 0 CHECK (skill BETWEEN 0 AND 300),
    is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    UNIQUE (character_id, profession)
);

CREATE TABLE polls (
    id            INTEGER PRIMARY KEY,
    question      TEXT NOT NULL,
    created_by    INTEGER NOT NULL REFERENCES users(id),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closes_at     TEXT,
    multi_select  INTEGER NOT NULL DEFAULT 0 CHECK (multi_select IN (0, 1)),
    is_closed     INTEGER NOT NULL DEFAULT 0 CHECK (is_closed IN (0, 1))
);

CREATE TABLE poll_options (
    id       INTEGER PRIMARY KEY,
    poll_id  INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    label    TEXT NOT NULL
);

CREATE TABLE poll_votes (
    id         INTEGER PRIMARY KEY,
    poll_id    INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    option_id  INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (option_id, user_id)
);

-- The option must belong to the poll, and single-choice polls allow one vote per user.
CREATE TRIGGER poll_votes_check BEFORE INSERT ON poll_votes
BEGIN
    SELECT RAISE(ABORT, 'option does not belong to poll')
    WHERE (SELECT poll_id FROM poll_options WHERE id = NEW.option_id) IS NOT NEW.poll_id;

    SELECT RAISE(ABORT, 'single-choice poll allows one vote per user')
    WHERE (SELECT multi_select FROM polls WHERE id = NEW.poll_id) = 0
      AND EXISTS (SELECT 1 FROM poll_votes WHERE poll_id = NEW.poll_id AND user_id = NEW.user_id);
END;

-- `block` is the label of a time block from settings.availability_blocks.
CREATE TABLE availability (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weekday    INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0 = Monday
    block      TEXT NOT NULL,
    available  INTEGER NOT NULL DEFAULT 0 CHECK (available IN (0, 1)),
    PRIMARY KEY (user_id, weekday, block)
);

CREATE TABLE settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

CREATE TABLE announcements (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    posted_by  INTEGER NOT NULL REFERENCES users(id),
    posted_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE role_changes (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    old_role    TEXT NOT NULL,
    new_role    TEXT NOT NULL,
    changed_by  INTEGER NOT NULL REFERENCES users(id),
    changed_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
