-- ZepBot Database Schema
-- Run with: psql $DATABASE_URL < database.sql

CREATE TABLE IF NOT EXISTS whitelisted_guilds (
  guild_id BIGINT PRIMARY KEY,
  guild_owner_id BIGINT,
  whitelisted_by BIGINT,
  whitelisted_at TIMESTAMP DEFAULT NOW(),
  guild_name TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS config_access (
  guild_id BIGINT,
  user_id BIGINT,
  granted_by BIGINT,
  granted_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS guild_configs (
  guild_id BIGINT PRIMARY KEY,
  config TEXT
);

CREATE TABLE IF NOT EXISTS cases (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  user_id BIGINT,
  moderator_id BIGINT,
  action TEXT,
  reason TEXT,
  duration TEXT,
  expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mutes (
  guild_id BIGINT,
  user_id BIGINT,
  expires_at TIMESTAMP,
  removed_roles BIGINT[],
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS temp_bans (
  guild_id BIGINT,
  user_id BIGINT,
  expires_at TIMESTAMP,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS tags (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  name TEXT,
  content TEXT
);

CREATE TABLE IF NOT EXISTS reminders (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  user_id BIGINT,
  channel_id BIGINT,
  message TEXT,
  remind_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raid_events (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  triggered_at TIMESTAMP DEFAULT NOW(),
  action_taken TEXT,
  members_affected BIGINT[]
);

CREATE TABLE IF NOT EXISTS temp_roles (
  guild_id BIGINT,
  user_id BIGINT,
  role_id BIGINT,
  expires_at TIMESTAMP,
  PRIMARY KEY (guild_id, user_id, role_id)
);

CREATE TABLE IF NOT EXISTS starboard_messages (
  guild_id BIGINT,
  message_id BIGINT,
  starboard_message_id BIGINT,
  channel_id BIGINT,
  author_id BIGINT,
  star_count INT DEFAULT 0,
  posted_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, message_id)
);

CREATE TABLE IF NOT EXISTS ticket_panels (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  channel_id BIGINT,
  message_id BIGINT,
  panel_name TEXT,
  panel_type TEXT,
  description TEXT,
  category_id BIGINT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_categories (
  id SERIAL PRIMARY KEY,
  panel_id INT REFERENCES ticket_panels(id) ON DELETE CASCADE,
  guild_id BIGINT,
  label TEXT,
  description TEXT,
  emoji TEXT,
  support_roles BIGINT[],
  ping_roles BIGINT[],
  welcome_message TEXT,
  name_format TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  channel_id BIGINT,
  user_id BIGINT,
  claimed_by BIGINT,
  panel_id INT,
  category_id INT,
  status TEXT DEFAULT 'open',
  ticket_number INT,
  opened_at TIMESTAMP DEFAULT NOW(),
  closed_at TIMESTAMP,
  deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_blacklist (
  guild_id BIGINT,
  user_id BIGINT,
  reason TEXT,
  moderator_id BIGINT,
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS ticket_participants (
  ticket_id INT REFERENCES tickets(id) ON DELETE CASCADE,
  user_id BIGINT,
  added_by BIGINT,
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (ticket_id, user_id)
);

CREATE TABLE IF NOT EXISTS reaction_role_panels (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  channel_id BIGINT,
  message_id BIGINT,
  panel_name TEXT,
  panel_type TEXT,
  description TEXT,
  max_roles INT DEFAULT 0,
  required_role BIGINT,
  remove_on_reselect BOOL DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reaction_role_entries (
  id SERIAL PRIMARY KEY,
  panel_id INT REFERENCES reaction_role_panels(id) ON DELETE CASCADE,
  guild_id BIGINT,
  role_id BIGINT,
  emoji TEXT,
  label TEXT,
  description TEXT,
  style TEXT DEFAULT 'secondary',
  position INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS auto_replies (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  trigger TEXT,
  response TEXT,
  trigger_type TEXT DEFAULT 'contains',
  match_case BOOL DEFAULT false,
  reply_type TEXT DEFAULT 'message',
  delete_trigger BOOL DEFAULT false,
  delete_after INT DEFAULT null,
  ignore_roles BIGINT[],
  ignore_channels BIGINT[],
  only_channels BIGINT[],
  only_roles BIGINT[],
  cooldown_seconds INT DEFAULT 0,
  enabled BOOL DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auto_reactions (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  trigger TEXT,
  emojis TEXT[],
  trigger_type TEXT DEFAULT 'contains',
  match_case BOOL DEFAULT false,
  ignore_roles BIGINT[],
  ignore_channels BIGINT[],
  only_channels BIGINT[],
  only_roles BIGINT[],
  cooldown_seconds INT DEFAULT 0,
  enabled BOOL DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS autoclean_channels (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  channel_id BIGINT,
  mode TEXT,
  interval_seconds INT,
  keep_count INT,
  max_age_seconds INT,
  delay_seconds INT DEFAULT 0,
  ignore_pinned BOOL DEFAULT true,
  ignore_roles BIGINT[],
  ignore_bots BOOL DEFAULT false,
  enabled BOOL DEFAULT true,
  last_run TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_timezones (
  user_id BIGINT PRIMARY KEY,
  timezone TEXT
);

CREATE TABLE IF NOT EXISTS locked_channels (
  guild_id BIGINT,
  channel_id BIGINT,
  locked_by BIGINT,
  reason TEXT,
  original_permissions JSONB,
  locked_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS nick_locks (
  guild_id BIGINT,
  user_id BIGINT,
  locked_nick TEXT,
  locked_by BIGINT,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS watchlist (
  guild_id BIGINT,
  user_id BIGINT,
  reason TEXT,
  added_by BIGINT,
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS automod_immune (
  guild_id BIGINT,
  user_id BIGINT,
  added_by BIGINT,
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS ignored_users (
  guild_id BIGINT,
  user_id BIGINT,
  expires_at TIMESTAMP,
  added_by BIGINT,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS seen (
  guild_id BIGINT,
  user_id BIGINT,
  last_seen TIMESTAMP,
  last_channel_id BIGINT,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS strikes (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  user_id BIGINT,
  moderator_id BIGINT,
  reason TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS history_events (
  id SERIAL PRIMARY KEY,
  guild_id BIGINT,
  user_id BIGINT,
  event_type TEXT,
  description TEXT,
  moderator_id BIGINT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS duration_role_assignments (
  guild_id BIGINT,
  user_id BIGINT,
  role_id BIGINT,
  assigned_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,
  PRIMARY KEY (guild_id, user_id, role_id)
);

CREATE TABLE IF NOT EXISTS role_bans (
  guild_id BIGINT,
  user_id BIGINT,
  role_id BIGINT,
  reason TEXT,
  moderator_id BIGINT,
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id, role_id)
);
