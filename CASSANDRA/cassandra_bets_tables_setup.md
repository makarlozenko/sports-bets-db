# Cassandra Bet Tables

> **Note:** All steps in this guide assume that the main tables in the `sportsbook` keyspace have already been created and loaded. Before proceeding, make sure to execute the following commands:

```bash
docker cp CASSANDRA/create_keyspace.cql cassandra:/create_keyspace.cql
docker exec -it cassandra cqlsh -f /create_keyspace.cql

docker cp CASSANDRA/old_data_schema.cql cassandra:/old_data_schema.cql
docker cp CASSANDRA/teams.cql cassandra:/teams.cql
docker cp CASSANDRA/users.cql cassandra:/users.cql
docker cp CASSANDRA/team_players.cql cassandra:/team_players.cql
docker cp CASSANDRA/team_coaches.cql cassandra:/team_coaches.cql
docker cp CASSANDRA/matches.cql cassandra:/matches.cql
docker cp CASSANDRA/bets.cql cassandra:/bets.cql

docker exec -it cassandra cqlsh -f /old_data_schema.cql
docker exec -it cassandra cqlsh -f /teams.cql
docker exec -it cassandra cqlsh -f /users.cql
docker exec -it cassandra cqlsh -f /team_players.cql
docker exec -it cassandra cqlsh -f /team_coaches.cql
docker exec -it cassandra cqlsh -f /matches.cql
docker exec -it cassandra cqlsh -f /bets.cql
```

---

## 1. Copy and Create Bet Tables

Copy the new bet tables (`bets_by_day`, `bets_by_user_day`, `bets_by_match`) to the Cassandra container:

```bash
docker cp CASSANDRA/bets_by_day.cql cassandra:/bets_by_day.cql
docker cp CASSANDRA/bets_by_user_day.cql cassandra:/bets_by_user_day.cql
docker cp CASSANDRA/bets_by_match.cql cassandra:/bets_by_match.cql
```

Create the tables in the `sportsbook` keyspace:

```bash
docker exec -it cassandra cqlsh -f /bets_by_day.cql
docker exec -it cassandra cqlsh -f /bets_by_user_day.cql
docker exec -it cassandra cqlsh -f /bets_by_match.cql
```

---

## 2. Replicate Existing Bets Data

Use the replication CQL file to copy all data from `bets` to the other bets tables:

```bash
docker cp CASSANDRA/Bets_data_replication.cql cassandra:/Bets_data_replication.cql
docker exec -it cassandra cqlsh -f /Bets_data_replication.cql
```

---

## 3. Checking how tables work

Connect to the `sportsbook` keyspace and check how tables work. In this case, bets_by_day -
event_date as a primary key and bet_created_at, stake, bet_id as clustering keys in descending order;
bets_by_user_day - same clustering keys as bets_by_day, only the primary key is now a combination
of event_date and user_email; bets_by_match - same clustering keys as in previous tables and the
primary key is a combination of event_team1 and event_team2.

```bash
docker exec -it cassandra cqlsh
USE sportsbook;
DESCRIBE TABLES;

SELECT * FROM bets_by_day WHERE event_date = '2025-09-01';
SELECT * FROM bets_by_user_day WHERE event_date = '2025-08-29' AND user_email = 'dovydas.sakalauskas5@gmail.com';
SELECT * FROM bets_by_match WHERE event_team1 = 'Vilnius Wolves' AND event_team2 = 'Kaunas Green';
```

---

## 4. Modify Partitioning or Clustering (Optional)

If you need to change partition keys or clustering keys, you must drop the tables first and recreate them:

```bash
DROP TABLE bets_by_day;
DROP TABLE bets_by_user_day;
DROP TABLE bets_by_match;
```

Then, repeat **Step 1** to recreate the tables with updated keys.

## 5. Scenario of a new bet being added

There is a file called Bets_Cassandra_Scenario.py, which creates a new bet into the bets table,
then replicates that new bet into other bet related tables (bets_by_day, bets_by_user_day, bets_by_match). After
that, the bet tables are checked with the previously mentioned SELECT commands to see
if the new bet appeared there. After checking, the test bet that was added is deleted from all tables.
