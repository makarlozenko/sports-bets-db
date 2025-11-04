CREATE TABLE IF NOT EXISTS sportsbook.bets_by_match (
    bet_id text,
    user_id text,
    user_email text,
    event_team1 text,
    event_team2 text,
    event_type text,
    event_date date,
    bet_choice text,
    bet_team text,
    bet_score_team1 int,
    bet_score_team2 int,
    stake decimal,
    bet_created_at timestamp,
    status text,
    PRIMARY KEY ((event_team1, event_team2), bet_created_at, stake)
) WITH CLUSTERING ORDER BY (bet_created_at DESC, stake DESC);
