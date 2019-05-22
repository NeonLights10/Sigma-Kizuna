[![GitHub release](https://img.shields.io/github/release/NeonLights10/Sigma-Kizuna.svg?style=flat-square)](https://github.com/Just-Some-Bots/MusicBot/wiki)

# Sigma and Kizuna AI (v2.0.1)

Sigma is a Discord bot written in [Python](https://www.python.org "Python homepage"). It plays requested songs and if the queue becomes empty it will play through a list of existing songs. It also provides utility commands and administrative commands, such as slowmode and role management.

This bot utilizes the MusicBot framework, but is heavily modified and is not compatible in any way.

### Credits
Artanys for the commands to promote, playnow, repeat, and the thumbnail support.

## Documentation
- %promote - Move a song to the front of the queue
- %playnow - Instaplay a song regardless if there is a queue or not
- %remove - Remove a song from the queue
- %sub - Substitute a song already in the queue with another song. Can do this at any position
- %hello, %hug, %poke, %cuddle, %headpat - Friendly banter between Sigma/Kizuna and users
- %time - Get the current time in UTC or a different timezone
- %tconvert - Convert time from one timezone to another
- %aar - Autoassign a role upon user join
- %purge - Primitive message deleting capabilites (atm)
- %addrole/removerole - Create and remove roles
- %addmember/removemember - Add and remove members from roles
- %stats - Display stats about the bot
- %kick - Kick a user
- %slowmode - Enable slow mode on a server

Sigma/Kizuna keeps track of certain properties and settings for individual servers using MongoDB, meaning that they persist across restarts and updates.

Sigma/Kizuna can now respond to non-bound commands anywhere in the server. This means that music commands will only work in the channels you specify in the config, while other commands will work anywhere. They also respond to mentions!