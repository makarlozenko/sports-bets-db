# Rivalry Graph API (Neo4j Integration)

This document describes the API endpoints for managing team rivalries stored in Neo4j.
All teams must exist in MongoDB before a rivalry can be created.
The rivalry relationships are stored using (:Team)-[:RIVAL_OF]-(:Team).

## Base URL
http://127.0.0.1:5000

## Endpoints Overview

| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST   | /neo4j/rivalry | Create a rivalry between two MongoDB teams |
| DELETE | /neo4j/rivalry | Delete a rivalry between two teams |
| GET    | /neo4j/team/<team>/rivals | Get direct and indirect rivals |
| DELETE | /neo4j/rivalries/all | Delete all rivalry relationships |
| GET    | /neo4j/by_user/<email>/bets | Get all bets placed by a user in Neo4j |

## 1. Create a Rivalry

POST /neo4j/rivalry

Request Body:
{
  "team1": "Vilnius FC",
  "team2": "Kaunas United"
}

## 2. Delete a Rivalry

DELETE /neo4j/rivalry

Request Body:
{
  "team1": "Vilnius FC",
  "team2": "Kaunas United"
}

## 3. Delete All Rivalries

DELETE /neo4j/rivalries/all

## 4. Get All Rivals of a Team

GET /neo4j/team/<team>/rivals

## 5. Get User Bets

GET /neo4j/by_user/<email>/bets

## Postman Testing Guide

1. DELETE /neo4j/rivalries/all  
2. POST /neo4j/rivalry  
3. GET /neo4j/team/<team>/rivals  
4. DELETE /neo4j/rivalry  
5. GET /neo4j/team/<team>/rivals  
