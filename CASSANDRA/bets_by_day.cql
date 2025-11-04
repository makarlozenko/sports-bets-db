CREATE TABLE IF NOT EXISTS sportsbook.bets_by_day (
    event_date date,
    bet_id text,
    user_id text,
    user_email text,
    event_team1 text,
    event_team2 text,
    event_type text,
    bet_choice text,
    bet_team text,
    bet_score_team1 int,
    bet_score_team2 int,
    stake decimal,
    bet_created_at timestamp,
    status text,
    created_at timestamp,
    PRIMARY KEY (event_date, bet_id)
);