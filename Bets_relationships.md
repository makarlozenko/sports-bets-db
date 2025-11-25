# Sports Betting Neo4j Integration

## Overview

This integrates **Neo4j** into a sports betting workflow. The goal is to track bets in a graph database for enhanced querying and recommendations, while maintaining the main data in **MongoDB**.

The workflow ensures that:
- Every bet placed in MongoDB creates corresponding nodes and relationships in Neo4j.
- Bets are linked to the correct **User**, **Match**, and optionally a **Team**.
- Deleting a bet in MongoDB removes its relationships in Neo4j.
- Neo4j can be queried independently to verify live data.

---

## Neo4j Graph Structure

- **User** → **Bet** → (**Team** / **Match**)
- Nodes: `User`, `Bet`, `Match`, `Team`
- Relationships:
  - `(:User)-[:PLACED]->(:Bet)`
  - `(:Bet)-[:ON_MATCH]->(:Match)`
  - `(:Bet)-[:ON_TEAM]->(:Team)` (only if the bet is team-specific, e.g., a "winner" bet)

### Example Cases

1. **Team-specific bet (Winner)**
   - User bets on "Kaunas United" to win.
   - Graph nodes created: `User`, `Bet`, `Match`, `Team`
   - Relationships created:
     ```
     User -> Bet
     Bet -> Match
     Bet -> Team
     ```

2. **Score-based bet**
   - User bets on the score of a basketball match.
   - Graph nodes created: `User`, `Bet`, `Match`
   - No team relationship is created.

---

## Functionality Implemented

### 1. Creating Neo4j Nodes & Relationships

Function: `create_bet_relationships(user_email, bet_id, match_id, match_sport=None, team_id=None, team_name=None)`

- Ensures that the **User**, **Bet**, **Match**, and optionally **Team** nodes exist.
- Creates relationships between nodes according to the bet type.
- Works for both team-specific bets and match-only bets.

### 2. Deleting Bets

- When a bet is deleted in MongoDB, its relationships in Neo4j are also removed.
- The `DELETE /bets/<id>` endpoint handles both MongoDB deletion and ensures Neo4j consistency.

### 3. Retrieving User Bets relationships from Neo4j

- Endpoint: `GET /neo4j/by_user/<user_email>/bets`
- Returns all bets and their relationships for a given user in Neo4j.

---

## Scenario File

A Python scenario file `neo4j_bets_relationships_scenario.py` has been created to demonstrate:

1. Posting two different bets for the same user.
2. Printing Neo4j relationships after bet creation.
3. Deleting the bets.
4. Printing Neo4j relationships again to confirm deletion.

This file can be run independently as long as the Flask app is running. It uses `requests` to interact with the endpoints.

---

## Setup Instructions

1. Make sure **MongoDB**, **Redis**, **Cassandra** and **Neo4j** are running.
2. Run Flask app (`main.py`).
3. Run the scenario file:
   ```bash
    neo4j_bets_relationships_scenario.py
   ```
4. Observe the output in the terminal:
   - Neo4j relationships after creation.
   - Neo4j relationships after deletion.

---
