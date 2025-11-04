import subprocess
from datetime import datetime
import time

bet_id = '6904a44flk8c6h59c9942063'
user_id = 'dc4e7k460108e4l2079se68e'
user_email = 'test.user@example.com'
event_team1 = 'Vilnius Wolves'
event_team2 = 'Kaunas Green'
event_type = 'league'
event_date = '2025-11-05'
bet_choice = 'winner'
bet_team = event_team1
bet_score_team1 = 'null'
bet_score_team2 = 'null'
stake = 30.0
bet_created_at = datetime.utcnow().isoformat()
status = 'pending'

insert_cql = f"""
USE sportsbook;
INSERT INTO bets (
    bet_id, user_id, user_email, event_team1, event_team2, event_type, event_date,
    bet_choice, bet_team, bet_score_team1, bet_score_team2, stake, bet_created_at, status
) VALUES (
    '{bet_id}', '{user_id}', '{user_email}', '{event_team1}', '{event_team2}', '{event_type}', '{event_date}',
    '{bet_choice}', '{bet_team}', {bet_score_team1}, {bet_score_team2}, {stake}, '{bet_created_at}', '{status}'
);
"""

subprocess.run(
    ["docker", "exec", "-i", "cassandra", "cqlsh"],
    input=insert_cql.encode()
)

subprocess.run(["docker", "exec", "-i", "cassandra", "cqlsh", "-f", "/Bets_data_replication.cql"])

time.sleep(3)

queries = {
    "bets_by_day": f"SELECT * FROM bets_by_day WHERE event_date = '{event_date}';",
    "bets_by_user_day": f"SELECT * FROM bets_by_user_day WHERE event_date = '{event_date}' AND user_email = '{user_email}';",
    "bets_by_match": f"SELECT * FROM bets_by_match WHERE event_team1 = '{event_team1}' AND event_team2 = '{event_team2}';"
}

for table, query in queries.items():
    print(f"\n-- {table} --")
    subprocess.run(["docker", "exec", "-i", "cassandra", "cqlsh", "-e", f"USE sportsbook; {query}"])

delete_cql = f"""
USE sportsbook;
DELETE FROM bets WHERE bet_id = '{bet_id}';
DELETE FROM bets_by_day 
WHERE event_date = '{event_date}' 
AND bet_created_at = '{bet_created_at}' 
AND stake = {stake}
AND bet_id = '{bet_id}';
DELETE FROM bets_by_user_day 
WHERE event_date = '{event_date}' 
AND user_email = '{user_email}' 
AND bet_created_at = '{bet_created_at}' 
AND stake = {stake}
AND bet_id = '{bet_id}';
DELETE FROM bets_by_match 
WHERE event_team1 = '{event_team1}' 
AND event_team2 = '{event_team2}' 
AND bet_created_at = '{bet_created_at}' 
AND stake = {stake}
AND bet_id = '{bet_id}';
"""

subprocess.run(
    ["docker", "exec", "-i", "cassandra", "cqlsh"],
    input=delete_cql.encode()
)

print("\nTest bet deleted successfully.")
