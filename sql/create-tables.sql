CREATE TABLE IF NOT EXISTS pain_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL DEFAULT 'naver_kin',
    source_url TEXT UNIQUE,
    keyword TEXT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    pain_summary TEXT,
    pain_score INTEGER DEFAULT 0,
    solution_hint TEXT,
    is_actionable BOOLEAN DEFAULT 0,
    collected_at TEXT,
    classified_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE,
    total_collected INTEGER DEFAULT 0,
    total_actionable INTEGER DEFAULT 0,
    top_categories TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pain_category ON pain_points(category);
CREATE INDEX IF NOT EXISTS idx_pain_score ON pain_points(pain_score DESC);
CREATE INDEX IF NOT EXISTS idx_pain_date ON pain_points(collected_at);
CREATE INDEX IF NOT EXISTS idx_pain_actionable ON pain_points(is_actionable);
