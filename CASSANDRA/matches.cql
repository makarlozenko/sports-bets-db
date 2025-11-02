BEGIN BATCH
INSERT INTO sportsbook.matches (
  match_id, match_type, sport, date, odds, team1_name, team2_name,
  t1_goals_for, t1_goals_against, t1_cards_red, t1_cards_yellow,
  t2_goals_for, t2_goals_against, t2_cards_red, t2_cards_yellow,
  t1_points_one, t1_points_two, t1_points_three, t1_fouls,
  t2_points_one, t2_points_two, t2_points_three, t2_fouls
) VALUES (
  '68e7b61ff2656d90ad339dd5', 'league', 'football', '2025-08-29', 2.00, 'Vilnius FC', 'Panevezys Town',
  0, 1, 0, 0,
  1, 0, 2, 0,
  NULL, NULL, NULL, NULL,
  NULL, NULL, NULL, NULL
);
INSERT INTO sportsbook.matches (
  match_id, match_type, sport, date, odds, team1_name, team2_name,
  t1_goals_for, t1_goals_against, t1_cards_red, t1_cards_yellow,
  t2_goals_for, t2_goals_against, t2_cards_red, t2_cards_yellow,
  t1_points_one, t1_points_two, t1_points_three, t1_fouls,
  t2_points_one, t2_points_two, t2_points_three, t2_fouls
) VALUES (
  '68e7b61ff2656d90ad339dd3', 'league', 'football', '2025-08-15', 2.00, 'Vilnius FC', 'Kaunas United',
  0, 0, 1, 1,
  0, 0, 1, 0,
  NULL, NULL, NULL, NULL,
  NULL, NULL, NULL, NULL
);
INSERT INTO sportsbook.matches (
  match_id, match_type, sport, date, odds, team1_name, team2_name,
  t1_goals_for, t1_goals_against, t1_cards_red, t1_cards_yellow,
  t2_goals_for, t2_goals_against, t2_cards_red, t2_cards_yellow,
  t1_points_one, t1_points_two, t1_points_three, t1_fouls,
  t2_points_one, t2_points_two, t2_points_three, t2_fouls
) VALUES (
  '68e7b61ff2656d90ad339de8', 'league', 'basketball', '2025-09-29', 2.00, 'Vilnius Wolves', 'Klaipeda Mariners',
  NULL, NULL, NULL, NULL,
  NULL, NULL, NULL, NULL,
  18, 75, 14, 22,
  18, 12, 14, NULL
);
INSERT INTO sportsbook.matches (
  match_id, match_type, sport, date, odds, team1_name, team2_name,
  t1_goals_for, t1_goals_against, t1_cards_red, t1_cards_yellow,
  t2_goals_for, t2_goals_against, t2_cards_red, t2_cards_yellow,
  t1_points_one, t1_points_two, t1_points_three, t1_fouls,
  t2_points_one, t2_points_two, t2_points_three, t2_fouls
) VALUES (
  '68e7b61ff2656d90ad339de7', 'league', 'basketball', '2025-09-01', 2.00, 'Vilnius Wolves', 'Kaunas Green',
  NULL, NULL, NULL, NULL,
  NULL, NULL, NULL, NULL,
  12, 58, 7, 24,
  20, 60, 7, 31
);
INSERT INTO sportsbook.matches (
  match_id, match_type, sport, date, odds, team1_name, team2_name,
  t1_goals_for, t1_goals_against, t1_cards_red, t1_cards_yellow,
  t2_goals_for, t2_goals_against, t2_cards_red, t2_cards_yellow,
  t1_points_one, t1_points_two, t1_points_three, t1_fouls,
  t2_points_one, t2_points_two, t2_points_three, t2_fouls
) VALUES (
  '68e7b61ff2656d90ad339dd4', 'league', 'football', '2025-08-22', 2.00, 'Vilnius FC', 'Klaipeda City',
  0, 4, 0, 3,
  4, 0, 0, 1,
  NULL, NULL, NULL, NULL,
  NULL, NULL, NULL, NULL
);
INSERT INTO sportsbook.matches (
  match_id, match_type, sport, date, odds, team1_name, team2_name,
  t1_goals_for, t1_goals_against, t1_cards_red, t1_cards_yellow,
  t2_goals_for, t2_goals_against, t2_cards_red, t2_cards_yellow,
  t1_points_one, t1_points_two, t1_points_three, t1_fouls,
  t2_points_one, t2_points_two, t2_points_three, t2_fouls
) VALUES (
  '68e7b61ff2656d90ad339de9', 'league', 'basketball', '2025-10-06', 2.00, 'Vilnius Wolves', 'Panevezys Titans',
  NULL, NULL, NULL, NULL,
  NULL, NULL, NULL, NULL,
  18, 75, 14, 13,
  18, 21, 14, 3
);
APPLY BATCH;
