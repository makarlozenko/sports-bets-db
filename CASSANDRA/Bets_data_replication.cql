USE sportsbook;

COPY bets (
  bet_id, user_id, user_email, event_team1, event_team2, event_type, event_date,
  bet_choice, bet_team, bet_score_team1, bet_score_team2, stake, bet_created_at, status
) TO 'bets_tmp.csv' WITH HEADER=TRUE;

COPY bets_by_day (
  bet_id, user_id, user_email, event_team1, event_team2, event_type, event_date,
  bet_choice, bet_team, bet_score_team1, bet_score_team2, stake, bet_created_at, status
) FROM 'bets_tmp.csv' WITH HEADER=TRUE;

COPY bets_by_user_day (
  bet_id, user_id, user_email, event_team1, event_team2, event_type, event_date,
  bet_choice, bet_team, bet_score_team1, bet_score_team2, stake, bet_created_at, status
) FROM 'bets_tmp.csv' WITH HEADER=TRUE;

COPY bets_by_match (
  bet_id, user_id, user_email, event_team1, event_team2, event_type, event_date,
  bet_choice, bet_team, bet_score_team1, bet_score_team2, stake, bet_created_at, status
) FROM 'bets_tmp.csv' WITH HEADER=TRUE;