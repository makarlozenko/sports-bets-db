CREATE TABLE IF NOT EXISTS sportsbook.bets_by_user_day (
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
    PRIMARY KEY ((event_date, user_email), bet_created_at, stake, bet_id)
)   WITH CLUSTERING ORDER BY (bet_created_at DESC, stake DESC, bet_id DESC);