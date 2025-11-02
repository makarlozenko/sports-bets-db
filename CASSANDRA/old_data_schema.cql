
USE sportsbook;

-- Users
CREATE TABLE IF NOT EXISTS sportsbook.users (
  user_id text PRIMARY KEY,
  first_name text,
  last_name text,
  phone text,
  email text,
  birth_date date,
  iban text,
  balance decimal,
  nickname text
);

-- Teams
CREATE TABLE IF NOT EXISTS sportsbook.teams (
  team_id text PRIMARY KEY,
  sport text,
  team_name text,
  rating int,
  updated_at timestamp
);

-- Team coaches (one row per coach)
CREATE TABLE IF NOT EXISTS sportsbook.team_coaches (
  team_id text,
  coach_idx int,
  first_name text,
  last_name text,
  experience_years int,
  coach_type text,
  PRIMARY KEY (team_id, coach_idx)
);

-- Team players (one row per player)
CREATE TABLE IF NOT EXISTS sportsbook.team_players (
  team_id text,
  player_idx int,
  first_name text,
  last_name text,
  role text,
  birth_date date,
  career_goals_or_points int,
  penalties_received int,
  PRIMARY KEY (team_id, player_idx)
);

-- Matches (generic fields for football & basketball)
CREATE TABLE IF NOT EXISTS sportsbook.matches (
  match_id text PRIMARY KEY,
  match_type text,
  sport text,
  date date,
  odds decimal,
  team1_name text,
  team2_name text,
  -- Football stats
  t1_goals_for int,
  t1_goals_against int,
  t1_cards_red int,
  t1_cards_yellow int,
  t2_goals_for int,
  t2_goals_against int,
  t2_cards_red int,
  t2_cards_yellow int,
  -- Basketball stats
  t1_points_one int,
  t1_points_two int,
  t1_points_three int,
  t1_fouls int,
  t2_points_one int,
  t2_points_two int,
  t2_points_three int,
  t2_fouls int
);

-- Bets
CREATE TABLE IF NOT EXISTS sportsbook.bets (
  bet_id text PRIMARY KEY,
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
  created_at timestamp
);
