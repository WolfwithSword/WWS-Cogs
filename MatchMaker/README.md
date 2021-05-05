# Discord Python Red Bot Cog for basic MatchMaking, Ranking, etc.

===============================================================
### PIP INSTALLS:

pip install sqlalchemy      |    (latest)
pip install tabulate        |    (latest)

===============================================================
### ROLES:

Server Owner -> Can open the settings folder

Administrator privileges -> Can do basically any command

*Configurable Role Names, 3=Max level, 2=Developer level, 1=Moderator level*

BotCommander (3) -> Can do basically every command. This means bot commander can wipe the server stats

BotDev (2) -> Can do *almost* any command, but not wipe server. They can prune though. They have access to all Dev commands.

BotModerator (1) -> Can do most commands such as creating lobbies etc.

No Role -> Can only register, stats, leaderboard, join, leave, etc nothing changeable.

===============================================================

### SETTINGS

You can configure role names under ROLES

Max players indicates how many players per lobby

MAPS is for keeping sets of maps. Currently "Default" is hard-coded

===============================================================

### Add Cog

Add Repo: `[p]repo add WWS-Cogs https://github.com/WolfwithSword/WWS-Cogs/`

Add Cog: `[p]cog install WWS-Cogs MatchMaker`

Load Cog:  `[p]load MatchMaker`

Use Cog: `[p]mm ???`


===============================================================

### COMMANDS

===============================================================

[p]mm

View the top level commands

===============================================================

[p]mm dev

Shameless self promo of the dev

===============================================================

[p]mm leaderboard

View the top 25 registered members by their win rate (Wins / Games Played)

===============================================================

[p]mm stats

View your own stats and rank, or ping someone else to find out theirs

===============================================================

[p]mm maps

View all the maps and which map set they belong to. Map sets are currently config-only things and at the moment there is no way in the bot to switch between them. Yet.

Also - likely chance I forgot to code in message breakups if it is too large

===============================================================

[p]mm register

Register as a user of the bot which can then participate in lobbies and keep track of rank

===============================================================

[p]mm lobby

Top level for Lobby Commands

===============================================================

[p]mm lobby cancel

Cancel the active lobby for this channel

===============================================================

[p]mm lobby end [1,2]

End the current game in the lobby and select a victor. Either team 1 or 2.

===============================================================

[p]mm lobby info

View info about the lobby in the current channel if one is active

===============================================================

[p]mm lobby join

Join the current lobby if one is active in the channel and you are registered, and the lobby isn't full or in progress

===============================================================

[p]mm lobby leave

Leave the current active lobby if it has not started yet

===============================================================

[p]mm lobby players

View the players in the current lobby

===============================================================

[p]mm lobby setup

Setup the random distribution of teams for the lobby. Currently it does two randomized teams of equal size

===============================================================

[p]mm lobby start

Start the lobby and games once all players have joined. Note: You must have a full roster of players

===============================================================

[p]mm mod

Top level command for moderator/developer commands

===============================================================

[p]mm mod blacklist

Blacklist the *current* channel from creating lobbies

===============================================================

[p]mm mod whitelist

Remove the blacklist of the *current* channel for making lobbies

===============================================================

[p]mm mod getDBGuilds

Meant to be a dev only command, it gets a list of all servers the cog is active in

===============================================================

[p]mm mod prune

Removes old inactive data from the database, such as cancelled lobbies and games. Keeps stats

===============================================================

[p]mm mod reload

Reload the settings.json file into the cog. Useful for changing mapset data and max player counts, as well as some additional role names

===============================================================

[p]mm mod settings

Only used by the server owner, as it opens up the local directory of the settings.json file on the machine the bot runs on...

I didn't want to make it configurable via commands yet.

===============================================================

[p]mm mod users

View all users registered to mm in the current server

===============================================================

[p]mm mod wipe

Delete all database data for this server, including stats

===============================================================