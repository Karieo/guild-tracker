-- Seed data. Edit these tables directly (or add a new migration) when Forever changes things.

INSERT INTO game_classes (name, color, sort) VALUES
    ('Druid',   '#FF7C0A', 1),
    ('Hunter',  '#AAD372', 2),
    ('Mage',    '#3FC7EB', 3),
    ('Paladin', '#F48CBA', 4),
    ('Priest',  '#FFFFFF', 5),
    ('Rogue',   '#FFF468', 6),
    ('Shaman',  '#0070DD', 7),
    ('Warlock', '#8788EE', 8),
    ('Warrior', '#C69B6D', 9);

-- Alliance races are classic placeholders; fix them if Forever differs.
INSERT INTO races (name, faction, sort) VALUES
    ('Orc',       'Horde', 1),
    ('Undead',    'Horde', 2),
    ('Tauren',    'Horde', 3),
    ('Troll',     'Horde', 4),
    ('Skyborne',  'Horde', 5),
    ('Human',     'Alliance', 1),
    ('Dwarf',     'Alliance', 2),
    ('Night Elf', 'Alliance', 3),
    ('Gnome',     'Alliance', 4);

INSERT INTO professions (name, kind, sort) VALUES
    ('Alchemy',        'primary', 1),
    ('Blacksmithing',  'primary', 2),
    ('Enchanting',     'primary', 3),
    ('Engineering',    'primary', 4),
    ('Herbalism',      'primary', 5),
    ('Leatherworking', 'primary', 6),
    ('Mining',         'primary', 7),
    ('Skinning',       'primary', 8),
    ('Tailoring',      'primary', 9),
    ('Cooking',        'secondary', 10),
    ('First Aid',      'secondary', 11),
    ('Fishing',        'secondary', 12);

INSERT INTO settings (key, value) VALUES
    ('guild_name', 'Our Guild'),
    ('faction', 'Horde'),
    ('webhook_url', ''),
    ('availability_blocks', '["6–8pm", "8–10pm", "10pm–12am"]');
