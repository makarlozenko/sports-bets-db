BEGIN BATCH
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('7fdefe8df5451ce01ef5f6d4', 'football', 'Siauliai Stars', 1654, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('f7b99ba65b07aa9fe0d8e028', 'basketball', 'Klaipeda Mariners', 1723, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('dbb3de051049832dd663e496', 'basketball', 'Kaunas Green', 1746, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('cbf7c1086104519bacad1078', 'football', 'Kaunas United', 1627, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('3c4433abb58be0f4256ae387', 'basketball', 'Vilnius Wolves', 1842, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('345f8e56b998281dd0d48320', 'football', 'Vilnius FC', 19, '2025-10-10T06:59:04.856Z');
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('c2d8953b3b4bd7c921e9ece3', 'football', 'Klaipeda City', 1900, '2025-10-10T11:52:17.374Z');
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('cc49b9d10c0ff25149aaa394', 'football', 'Panevezys Town', 1711, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('3e015d0c80b2ac8a045663d5', 'basketball', 'Siauliai Suns', 1851, NULL);
INSERT INTO sportsbook.teams (team_id, sport, team_name, rating, updated_at)
VALUES ('83b0133727334ebcf2cfb088', 'basketball', 'Panevezys Titans', 1794, NULL);
APPLY BATCH;
