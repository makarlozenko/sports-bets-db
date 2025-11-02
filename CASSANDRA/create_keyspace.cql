CREATE KEYSPACE IF NOT EXISTS sportsbook
WITH REPLICATION = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

-- pasirenkam keyspace (nebūtina, bet patogu)
USE sportsbook;
