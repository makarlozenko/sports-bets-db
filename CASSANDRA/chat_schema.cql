USE sportsbook;

CREATE TABLE IF NOT EXISTS chat_messages_by_room (
    match_id text,
    message_id uuid,
    user_id text,
    user_email text,
    message text,
    sent_at timestamp,
    PRIMARY KEY (match_id, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC) AND default_time_to_live = 172800;

CREATE TABLE IF NOT EXISTS chat_messages_by_user_day (
    user_id text,
    day date,
    message_id uuid,
    match_id text,
    message text,
    sent_at timestamp,
    PRIMARY KEY ((user_id, day), message_id)
) WITH CLUSTERING ORDER BY (message_id ASC) AND default_time_to_live = 172800;
