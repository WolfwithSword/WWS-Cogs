import discord
import os
import webbrowser

from redbot.core import commands
from redbot.core import data_manager

from random import shuffle, choice, randrange
import json
import traceback

from sqlalchemy import create_engine, inspect, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy import any_

from tabulate import tabulate

# Dev: https://github.com/WolfwithSword

from .models import *
from .enums import *

class MatchMaker(commands.Cog):
    """Match Maker"""

    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        engine = create_engine('sqlite:///'+str(data_manager.bundled_data_path(self)) +'\\matchmaker-bot.db', echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()

        self.GROUP = "mm"

        self.SETTINGS = {}

        # If table doesn't exist, Create the database
        if not inspect(engine).has_table('guild'):
            Base.metadata.create_all(engine)


        self.loadSettings()

        print("---MatchMaker Teams Started---")
        all_guilds = self.bot.guilds
        for gd in all_guilds:
            g = self.session.query(Guild).filter(int(gd.id) == Guild.id).one_or_none()
            if g is None:
                g = Guild(id=int(gd.id))
                self.session.add(g)
            self.session.commit()
        ## ROLES ARE NOT INITIALIZED AND NEED TO BE CONFIGURED
        ## Will instead do checks for has admin rights, as well as add a list of roles?
        ## And also server owner for the settings folder open

    def __del__(self):
        if(self.session):
            self.session.commit()
            self.session.close()

    @commands.Cog.listener()
    async def on_shutdown(self):
        if(self.session):
            self.session.commit()
            self.session.close()

    def loadSettings(self):
        with open(str(data_manager.bundled_data_path(self)) + "\\settings.json") as f:
            self.SETTINGS = json.load(f)

        self.MAX_PLAYERS = self.SETTINGS['max_players']
        self.ROLES = self.SETTINGS['ROLES']
        self.MAPS = self.SETTINGS['MAPS']

        unique_maps = set([m for x in self.MAPS for m in self.MAPS[x]])
        for _map in unique_maps:
            instance = self.session.query(Map).filter(Map.Name == _map).one_or_none()
            if instance is None:
                self.session.add(Map(Name=_map))
                self.session.commit()

        self.session.commit()

        for mode in self.MAPS:
            mode_instance = self.session.query(MapSet).filter(MapSet.Name == mode).one_or_none()
            is_new_mode = False
            if mode_instance is None:
                self.session.add(MapSet(Name=mode))
                is_new_mode = True

            _maps = self.MAPS[mode]
            if (is_new_mode):
                for _map in _maps:
                    self.session.add(MapInfo(Set=mode, _Map=_map))
                self.session.commit()
            else:
                for _map in _maps:
                    instance = self.session.query(MapInfo).filter(MapInfo.Set == mode,
                                                                  MapInfo._Map == _map).one_or_none()
                    if instance is None:
                        self.session.add(MapInfo(Set=mode, _Map=_map))
            self.session.commit()

    @commands.group()
    async def mm(self, ctx):
        """MatchMaker Teams commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("This is not a valid subcommand. Use {}help {}".format(ctx.clean_prefix, self.GROUP))

    @mm.group(description="Moderator/Dev commands", brief="Mod/Dev Commands")
    async def mod(self, ctx: commands.Context):
        allowed = False
        allowed_roles = []
        caller_roles = [r.name for r in ctx.author.roles]
        if (ctx.author.guild_permissions.administrator):
            allowed = True

        if not allowed:
            for k in self.ROLES:
                allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command set")
            return
        if ctx.invoked_subcommand is None:
            pass

    async def getGuildNameByID(self, id):
        name = await self.bot.fetch_guild(id)
        return name

    @mod.command(name="reload", brief="Reload Settings")
    @commands.guild_only()
    async def reload(self, ctx):
        self.loadSettings()
        await ctx.send("Reloading Settings")

    @mod.command(name="getDBGuilds", brief="DEV - Get All Guilds")
    @commands.guild_only()
    async def getDBGuilds(self, ctx):
        # Doing DB Query instead of bot api call
        # To help monitor health of DB

        guilds = self.session.query(Guild).all()
        headers = ['Name','ID']
        rows = [ (await self.getGuildNameByID(g.id), g.id) for g in guilds]
        table = tabulate(rows, headers)
        await ctx.send('Current Guilds In DB:\n```\n'+table+'```')

    @mm.command(brief="List all Map Sets and available Maps", aliases=['mapsets','listmapsets','listMaps'],
                 description="View all map sets and associated maps")
    @commands.guild_only()
    async def maps(self, ctx):
        try:
            # Based on settings file, not database, to be up to date and support legacy data
            map_sets = self.MAPS.keys()

            headers = ['Set', 'Maps']
            sets = set(self.MAPS.keys())
            rows = [(m, ',\n'.join([y for y in self.MAPS[m]])) for m in sets]

            table = tabulate(rows, headers)
            await ctx.send('```\n' + table + '```')
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)

    @mm.command(brief="Register as a User", aliases=['signup'],
                 description="Register as a new user on the server")
    @commands.guild_only()
    async def register(self, ctx):
        discordID = ctx.author.id
        guild = ctx.message.guild
        try:
            result = await self.registerUser(discordID, guild)
            await ctx.send(result)
        except Exception as e:
            await ctx.send('Could not complete your command')
            print(e)
    
    async def getUsernameFromID(self, discordID):
        name = await self.bot.fetch_user(discordID)
        return name
    
    async def registerUser(self, discordID, guild):
        msg = ""
        username = await self.getUsernameFromID(discordID);
        user = self.session.query(User).filter(User.UserID == discordID, User.GuildID == guild.id).one_or_none()
        if user is not None:
            user.Username = username;
            msg = "{} is already registered in server {}!".format(username, guild.name)
        else:
            user = User(UserID=discordID, GuildID=guild.id);
            score = Score(UserID = user.UserID, GuildID = user.GuildID)
            self.session.add_all([user, score])
            
            msg = "Registering new user {} for server {}".format(username, guild.name)

        self.session.commit()
        return msg

    @mm.group(name="lobby",description="Lobby Commands", brief="Lobby Commands")
    async def lobby(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            activeLobby = self.checkActiveLobby(ctx.channel.id, ctx.guild.id);
            if activeLobby is not None:
                await self.sayLobbyInfo(ctx)
            else:
                pass

    @lobby.command(brief='MOD - Make a new Lobby', aliases=['make', 'create'], description="Make a new lobby")
    @commands.guild_only()
    async def start(self, ctx, pick=1):
        caller_roles = [r.name for r in ctx.author.roles]
        allowed_roles = []
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True

        if not allowed:
            for k in self.ROLES:
                if self.ROLES[k] != 2: #not dev
                    allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return

        try:
            await ctx.send("There will be one match with {} players, separated into two teams. Maps are random.".format(self.MAX_PLAYERS))
            channelID = ctx.message.channel.id
            guildID = ctx.message.guild.id
            bl = self.session.query(BlacklistChannel).filter(BlacklistChannel.id == channelID, BlacklistChannel.GuildID == guildID).one_or_none()
            if bl is not None:
                await ctx.send("This channel is blacklisted from creating lobbies")
                return
            activeLobby = self.checkActiveLobby(channelID, guildID)
            if activeLobby is not None:
                await ctx.send("There is already an active lobby in this channel")
                return

            pick = PickMode(pick).value

            try:
                self.createEmptyLobby(channelID, guildID, pick)
                await ctx.send("Lobby created! Join using {}lobby join. Up to {} players can join.\n"
                               .format(ctx.clean_prefix + self.GROUP + " ", self.MAX_PLAYERS))
                await self.sayLobbyInfo(ctx)
            except Exception as e:
                await ctx.send("Error creating lobby")
                traceback.print_exc()
                print("\n\nERROR CREATING LOBBY\n")
                print(e)
                print("\n\n")
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)


    def checkActiveLobby(self, channelID, guildID):
        activeLobby = self.session.query(Lobby.Active).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
        return activeLobby

    def createEmptyLobby(self, channelID, guildID, pickMode):
        
        lobby = Lobby(ChannelID = channelID, GuildID = guildID, PickMode = pickMode, Games = [], Players = [], UserLimit = self.MAX_PLAYERS)

        self.session.add(lobby)
        self.session.commit()
        
        self.session.refresh(lobby)

        team1 = Team(GuildID = guildID, ChannelID = channelID, Num = 1, LobbyID = lobby.id, Players = [])
        team2 = Team(GuildID = guildID, ChannelID = channelID, Num = 2, LobbyID = lobby.id, Players = [])

        self.session.add_all([team1, team2])

        lobby.Team1 = team1
        lobby.Team2 = team2

        set = "Default" # Hardcoded for now

        available_maps = self.MAPS[set]
        shuffle(available_maps)

        game1 = Game(LobbyID = lobby.id, IsPickingTeams=False, Active=True, Completed=False,
                     Set=set, _Map=choice(available_maps), GuildID = guildID,
                     ChannelID = channelID)

        self.session.add_all([game1])
        lobby.Games.append(game1)
        lobby.Active = True
        self.session.commit()


    async def sayLobbyInfo(self, ctx):
        try:
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == ctx.message.channel.id,
                                                     Lobby.GuildID == ctx.message.guild.id, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with {}lobby start!"
                               .format(ctx.clean_prefix + self.GROUP + " "))
                return

            channelName = ctx.message.channel.name
            guildName = ctx.message.guild.name

            msg = "Active Lobby for {}\n".format(channelName)

            if(lobby.Games is not None):
                msg += "Game Completed: {}/1\n".format(sum(g.Completed for g in lobby.Games))

                current = [g for g in lobby.Games if g.Active]
                if( len(current) > 0):
                    currentGame = current[0]
                    msg += "Current Game: {} - **{}**\n".format(currentGame.Set, currentGame._Map)
            else:
                msg+="\n```\n"
            msg2 = ""

            T1Players = lobby.Team1.Players
            T2Players = lobby.Team2.Players

            if not lobby.IsPlaying:
                msg2 += "```No Teams Made\n```"
            elif len(T1Players) > 0 and len(T2Players) > 0:
                headers = ["Team 1","Team 2"]
                rows = []
                for x in range(self.MAX_PLAYERS//2):
                    t1N = await self.getUsernameFromID(T1Players[x].UserID)
                    t1Name = t1N.name
                    t2N = await self.getUsernameFromID(T2Players[x].UserID)
                    t2Name = t2N.name

                    row = [t1Name, t2Name]
                    rows.append(row)

                msg2 += "```\n"
                table = tabulate(rows, headers)
                msg2 += table
                msg2 += "\n```\n"

            if(len(msg) + len(msg2) > 2000):
                await ctx.send(msg)
                await ctx.send(msg2)
            else:
                await ctx.send(msg + msg2)
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)     

    @lobby.command(brief="View current Lobby's Information", aliases=['information'],
                 description="View information on the currently active lobby")
    @commands.guild_only()
    async def info(self, ctx):
        await self.sayLobbyInfo(ctx)
            

    @mm.command(brief="View user stats", aliases=['rank'],
                 description="View statistics on a user. Defaults to yourself, but you may ping another user to know their stats")
    @commands.guild_only()
    async def stats(self, ctx):
        try:
            msg_user = ctx.message.author
            if len(ctx.message.mentions) > 0:
                msg_user = ctx.message.mentions[0]

            user = self.session.query(User).filter(User.UserID == msg_user.id, User.GuildID == ctx.message.guild.id).one_or_none()
            if user is None:
                await ctx.send("User {} has not registered in this server! Type {}register to start!".format(msg_user.name, ctx.clean_prefix + self.GROUP + " "))
                return
            headers = ["Rank", "User", "Wins/Losses", "Games Played", "Win Rate"]
            all_ranks = self.session.query(Score.UserID).filter(Score.GuildID == ctx.message.guild.id).order_by(desc(Score.WinRate)).all()
            all_ranks = [x[0] for x in all_ranks]
            rank = (all_ranks).index(user.UserID) +1
            rows = [[rank, msg_user.name, "{}/{}".format(user._Score.Wins, user._Score.Losses), user._Score.GamesPlayed, "{0:.2f}".format(user._Score.WinRate * 100) + "%"]]
            table = tabulate(rows, headers)
            await ctx.send("User Info for {} in server: {}\n```\n{}\n```\n".format(msg_user.name, ctx.message.guild.name,table))
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)

    @mm.command(brief="View Top 25", aliases=['top'],
                 description="View the top 25 users by rank! See who has those top points.")
    @commands.guild_only()
    async def leaderboard(self, ctx):
        try:
            guildID = ctx.message.guild.id

            scores = self.session.query(Score).filter(Score.GuildID == guildID).order_by(desc(Score.WinRate)).limit(25).all()
            headers = ["Rank", "User", "Wins/Losses", "Games Played", "Win Rate"]
            rows = [("{}.".format(scores.index(s)+1),
                (self.bot.get_user(s.UserID)).name, "{}/{}".format(s.Wins, s.Losses),
                s.GamesPlayed, "{0:.2f}".format(s.WinRate * 100) + "%") for s in scores]
            table = tabulate(rows, headers)
            await ctx.send("Leaderboard (T25) for {}\n```\n{}\n```\n".format(ctx.message.guild.name, table))
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)    

    @mod.command(brief="DEV - View all users in server", aliases=["allusers"])
    @commands.guild_only()
    async def users(self, ctx):
        try:
            users = self.session.query(User).filter(User.GuildID == ctx.message.guild.id).all()
            headers=['Username', 'ID', 'GuildID', "Games Played"]
            rows = [(await self.getUsernameFromID(u.UserID), u.UserID, u.GuildID, u._Score.GamesPlayed) for u in users]
            table = tabulate(rows, headers)
            await ctx.send('Registered Users:\n```\n'+table+'\n```')
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)
    
    @lobby.command(brief="Leave a lobby before games start", aliases=['quit'],
                 description="Leave a lobby before games start being played. To leave after, you may consider cancelling the lobby")
    @commands.guild_only()
    async def leave(self, ctx):
        channelID = ctx.message.channel.id
        guildID = ctx.message.guild.id
        msg_user = ctx.author

        try:
            msg = ""
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with {}lobby start!".format(ctx.clean_prefix + self.GROUP + " "))
                return
            if lobby.IsPlaying:
                await ctx.send("The games are already in progress. Cannot leave. Please consider remaking the lobby.")
                return
            added_players = [p.UserID for p in lobby.Players]

            if msg_user.id not in added_players:
                await ctx.send("User {} is not in the lobby!".format(msg_user.name))
                return

            t1 = [p.UserID for p in lobby.Team1.Players]
            t2 = [p.UserID for p in lobby.Team2.Players]
            
            for player in lobby.Players:
                if player.UserID == msg_user.id:
                    if player.UserID in t1:
                        lobby.Team1.Players.remove(player)
                    elif player.UserID in t2:
                        lobby.Team2.Players.remove(player)
                    lobby.Players.remove(player)
                    self.session.delete(player)
                    self.session.commit()
                    break
            await ctx.send("Removed user {} from lobby queue".format(msg_user.name))
        except Exception as e:
            await ctx.send("Could not complete your command")
            traceback.print_exc()
            print(e)

    @lobby.command(brief="Join a lobby in the channel", aliases=['play', 'enlist'],
                 description="Join the active lobby for this channel. Can't start unless full")
    @commands.guild_only()
    async def join(self, ctx):
        channelID = ctx.message.channel.id
        guildID = ctx.message.guild.id
        msg_user = ctx.author

        try:
            msg = ""
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with {}lobby start!".format(ctx.clean_prefix + self.GROUP + " "))
                return
            if len(lobby.Players) >= self.MAX_PLAYERS:
                await ctx.send("This lobby has maxed players. Please wait for a new lobby.")
                return
            user = self.session.query(User).filter(User.UserID == msg_user.id, User.GuildID == guildID).one_or_none()
            if user is None:
                await ctx.send("User {} is not registered yet! Please register first.".format(msg_user.name))
                return
            if lobby.IsPlaying:
                await ctx.send("Games are in progress! Cannot join.")
                return
            added_players = [p.UserID for p in lobby.Players]
            if msg_user.id in added_players:
                await ctx.send("User {} is already in the lobby!".format(msg_user.name))
                return
            
            player = Player(UserID = msg_user.id, GuildID = guildID, LobbyID = lobby.id)
            lobby.Players.append(player)
            
            self.session.add(player)
            self.session.commit()
            self.session.refresh(lobby)
            await ctx.send(msg+"Successfully added player {}".format(msg_user.name))

            if len(lobby.Players) >= self.MAX_PLAYERS:
                await ctx.send("{} players have joined. PickMode = {}. Do `{} lobby setup` to randomize teams.".format(self.MAX_PLAYERS, PickMode(lobby.PickMode).name, ctx.clean_prefix + self.GROUP + " "))
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)

    @lobby.command(brief="MOD - Setup players to teams", aliases=['teams'],
                 description="Start team selection for the current lobby. Done randomly, repeat command to shuffle again.")
    @commands.guild_only()
    async def setup(self, ctx):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        channelID = ctx.message.channel.id
        guildID = ctx.message.guild.id
        msg_user = ctx.author
        try:
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with {}lobby start!".format(ctx.clean_prefix + self.GROUP + " "))
                return
            if( len(lobby.Players) < self.MAX_PLAYERS):
                await ctx.send("You do not have enough players to setup teams. Currently have {}/{}".format(len(lobby.Players), self.MAX_PLAYERS))
                return
            if(lobby.IsPickingTeams):
                await ctx.send("Teams are currently being setup")
                return
            if(PickMode(lobby.PickMode).name == "Random"):
                team1 = lobby.Team1
                team2 = lobby.Team2
                players = [p for p in lobby.Players]
                shuffle(players)

                x = 0

                while (len(players) > 0):
                    p = players.pop()
                    if x % 2 == 0:
                        p.TeamID == team1.id
                        team1.Players.append(p)
                    else:
                        p.TeamID == team2.id
                        team2.Players.append(p)
                    x+=1
            
            lobby.Games[0].IsPickingTeams = False
            lobby.IsPlaying = True
            self.session.commit()
            msg = "Teams have been chosen! Please start playing.\n\n"
            msg += "- There is 1 round.\n"
            msg += "- When a game is over, a BotModerator must perform {}lobby end (1/2 for winning team)\n".format(ctx.clean_prefix + self.GROUP + " ")
            msg += "- To cancel a lobby prematurely, a BotModerator must perform the `lobby cancel` command\n"
            msg += "- To view lobby information and the maps you will be playing, use {}lobby info\n".format(ctx.clean_prefix + self.GROUP + " ")
            await ctx.send(msg)
            await self.sayLobbyInfo(ctx)
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)
    
    @lobby.command(brief="Current Players in Active Lobby",
                 description="View the current players in the active lobby for this channel")
    @commands.guild_only()
    async def players(self, ctx):
        channelID = ctx.message.channel.id
        guildID =ctx.message.guild.id
        try:
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with "+ ctx.clean_prefix + self.GROUP + " "+"lobby start!")
                return
            players = [ (self.bot.get_user(p.UserID)).name for p in lobby.Players]
            msg = "```\n"
            msg += "Player Count: {}/{}\n\nPlayers:\n".format(len(lobby.Players), self.MAX_PLAYERS)
            msg += "\n".join(players)
            msg += "\n```\n"
            await ctx.send(msg)
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)
            

    @lobby.command(brief="MOD - End Current Game (not lobby). Param Victor -> The winning team #", aliases=['finish'],
                 description="End an active game inside the active lobby.\nParameter Victor must be the winning team number (1 or 2)")
    async def end(self, ctx, victor: int):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        if victor not in [1,2]:
            await ctx.send("Please specify which team won. 1 or 2.")
            return
        channelID = ctx.message.channel.id
        guildID = ctx.message.guild.id
        try: 
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with {}lobby start!".format(ctx.clean_prefix + self.GROUP + " "))
                return
            if not lobby.IsPlaying:
                await ctx.send("This lobby has not started any games yet!")
                return
            team1_ids = [p.UserID for p in lobby.Team1.Players]
            team2_ids = [p.UserID for p in lobby.Team2.Players]

            t1Scores = self.session.query(Score).filter(Score.UserID.in_(team1_ids), Score.GuildID == guildID).all()
            t2Scores = self.session.query(Score).filter(Score.UserID.in_(team2_ids), Score.GuildID == guildID).all()
            
            
            for score in t1Scores:
                score.GamesPlayed += 1
                if victor == 1:
                    score.Wins += 1
                else:
                    score.Losses += 1
            for score in t2Scores:
                score.GamesPlayed += 1
                if victor == 2:
                    score.Wins += 1
                else:
                    score.Losses += 1
            numCompleted = sum(g.Completed for g in lobby.Games)
            if numCompleted < 1:
                lobby.Games[numCompleted].Completed = True
                lobby.Games[numCompleted].Active = False

            await self.sayLobbyInfo(ctx)
            await ctx.send("**Winner: Team {}!**".format(victor))

            if lobby.Games[0].Completed:
                # no more games, lobby closed
                
                await ctx.send("All games have been completed for this lobby. Make a new lobby to play again!\n\nThanks for playing!")
                lobby.Active = False
            else:
                await ctx.send("Game Completed! Next game starts now: {} - {}".format(lobby.Games[numCompleted+1].Set,lobby.Games[numCompleted+1]._Map))
            lobby.GamesPlayed += 1                
            self.session.commit()
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)
            
    @lobby.command(brief="MOD - Cancel Lobby Prematurely",
                 description="BotModerator +. Cancel a lobby in progress")
    @commands.guild_only()
    async def cancel(self, ctx):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        try:
            channelID = ctx.message.channel.id
            guildID = ctx.message.guild.id
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is None:
                await ctx.send("There is no active lobby in this channel. Start one with "+ctx.clean_prefix + self.GROUP + " "+"lobby start!")
                return
            for g in lobby.Games:
                g.Active = False
            lobby.Active = False
            self.session.commit()
            await ctx.send("Lobby has been cancelled successfully")
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)

    @mod.command(brief="Add Losses to a User (in case of missed or lost data)", aliases=['addlosses', 'addloss', 'addLoss'])
    @commands.guild_only()
    async def addLosses(self, ctx, user: discord.Member, amt:int):
        if amt is None:
            await ctx.send("Must enter in a valid number for losses to add to the user. Negative values are permitted unless it brings losses below 0")
            return
        if user is None or len(ctx.message.mentions) != 1:
            await ctx.send("Please mention a single valid user")
        try:

            user = self.session.query(User).filter(User.GuildID == ctx.message.guild.id, User.UserID == int(ctx.message.mentions[0].id)).one_or_none()
            if user is None:
                await ctx.send("User {} has not registered yet!".format(ctx.message.mentions[0].name))
                return
            if(user._Score.GamesPlayed + amt < 0 or user._Score.Losses + amt < 0):
                await ctx.send("Could not add losses as they would make total games played or losses negative")
                return
            user._Score.GamesPlayed += amt
            user._Score.Losses += amt
            self.session.commit()
            await ctx.send("Successfully added losses to {}.".format(ctx.message.mentions[0].name))
        except Exception as e:
            await ctx.send("Could not complete your command")
            traceback.print_exc()
            print(e)

    @mod.command(brief="Force-Register as a User",
                 description="Force Register a user on the server")
    @commands.guild_only()
    async def forceregister(self, ctx, user: discord.Member):
        discordID = user.id
        guild = ctx.message.guild
        try:
            result = await self.registerUser(discordID, guild)
            await ctx.send(result)
        except Exception as e:
            await ctx.send('Could not complete your command')
            print(e)

    @mod.command(brief="Add Wins to a User (in case of missed or lost data)", aliases=['addwins', 'addwin', 'addWin'])
    @commands.guild_only()
    async def addWins(self, ctx, user: discord.Member, amt:int):
        if amt is None:
            await ctx.send("Must enter in a valid number for wins to add to the user. Negative values are permitted unless it brings wins below 0")
            return
        if user is None or len(ctx.message.mentions) != 1:
            await ctx.send("Please mention a single valid user")
        try:

            user = self.session.query(User).filter(User.GuildID == ctx.message.guild.id, User.UserID == int(ctx.message.mentions[0].id)).one_or_none()
            if user is None:
                await ctx.send("User {} has not registered yet!".format(ctx.message.mentions[0].name))
                return
            if(user._Score.GamesPlayed + amt < 0 or user._Score.Wins + amt < 0):
                await ctx.send("Could not add wins as they would make total games played or wins negative")
                return
            user._Score.GamesPlayed += amt
            user._Score.Wins += amt
            self.session.commit()
            await ctx.send("Successfully added wins to {}.".format(ctx.message.mentions[0].name))
        except Exception as e:
            await ctx.send("Could not complete your command")
            traceback.print_exc()
            print(e)

    @mod.command(brief="COM - Reset server stats, games, lobbies.",
                 description="BotCommander only. Prunes all guild related data and resets player stats. It keeps blacklisted channels. Players will need to re-register.")
    @commands.guild_only()
    async def wipe(self, ctx):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                if self.ROLES[k] == 3: # ONLY COMMANDER
                    allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        try:
            guildID = ctx.message.guild.id
            query = Game.__table__.delete().where(Game.GuildID == guildID)
            self.session.execute(query)
            query = Team.__table__.delete().where(Team.GuildID == guildID)
            self.session.execute(query)
            query = Player.__table__.delete().where(Player.GuildID == guildID)
            self.session.execute(query)
            query = Lobby.__table__.delete().where(Lobby.GuildID == guildID)
            self.session.execute(query)
            query = Score.__table__.delete().where(Score.GuildID == guildID)
            self.session.execute(query)
            query = User.__table__.delete().where(User.GuildID == guildID)
            self.session.execute(query)

            self.session.commit()
            await ctx.send("Wipe Complete")
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)

    @mod.command(brief="COM - Prune old, inactive data for OCD",
                 description="BotCommander and Dev roles only. This prunes old data from the db where the associated lobby for this guild is inactive.")
    @commands.guild_only()
    async def prune(self, ctx):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                if self.ROLES[k] >=2: #Dev and Commander
                    allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        try:
            guildID = ctx.message.guild.id
            inactive_lobbies = self.session.query(Lobby.id).filter(Lobby.Active == False, Lobby.GuildID == guildID)

            query = Game.__table__.delete().where(Game.LobbyID.in_(inactive_lobbies))
            self.session.execute(query)
            query = Team.__table__.delete().where(Team.LobbyID.in_(inactive_lobbies))
            self.session.execute(query)
            query = Player.__table__.delete().where(Player.LobbyID.in_(inactive_lobbies))
            self.session.execute(query)
            query = Lobby.__table__.delete().where(Lobby.id.in_(inactive_lobbies))
            self.session.execute(query)

            self.session.commit()
            await ctx.send("Pruned Old Data")
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)        

    @mod.command(brief="Blacklist current channel from creating lobbies",
                 description="Blacklist the current channel from creating lobbies")
    @commands.guild_only()
    async def blacklist(self, ctx):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        try:
            
            channelID = ctx.message.channel.id
            guildID = ctx.message.guild.id
            lobby = self.session.query(Lobby).filter(Lobby.ChannelID == channelID, Lobby.GuildID == guildID, Lobby.Active == True).one_or_none()
            if lobby is not None:
                lobby.Active = False
                await ctx.send("Cancelling active lobby in this channel...")

            bl = self.session.query(BlacklistChannel).filter(BlacklistChannel.GuildID == guildID, BlacklistChannel.id == channelID).one_or_none()
            if bl is not None:
                await ctx.send("Channel is already blacklisted from creating lobbies!")
                return
            bl = BlacklistChannel(id = channelID, GuildID = guildID)
            self.session.add(bl)
            self.session.commit()
            await ctx.send("Channel is now blacklisted")
            
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)      
                          
    @mod.command(brief="Remove current channel from the blacklist",
                 description="Remove the current channel from the blacklist")
    @commands.guild_only()
    async def whitelist(self, ctx):
        allowed = False
        if (ctx.author.guild_permissions.administrator):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return
        try:
            
            channelID = ctx.message.channel.id
            guildID = ctx.message.guild.id
            bl = self.session.query(BlacklistChannel).filter(BlacklistChannel.GuildID == guildID, BlacklistChannel.id == channelID).one_or_none()
            if bl is None:
                await ctx.send("Channel was not blacklisted!")
                return
            self.session.delete(bl)
            self.session.commit()
            await ctx.send("Channel has been removed from the blacklist")
        except Exception as e:
            await ctx.send('Could not complete your command')
            traceback.print_exc()
            print(e)  

    @mm.command(brief="MatchMaker Extension made by WolfwithSword#0001")
    async def dev(self, ctx):
        msg = "MatchMaking Cog for Onward specifically, modified from a CoD 10 man's bot also made by the same idiot who made this...\n"
        msg += "was made by WolfwithSword#0001\n"
        msg += "https://github.com/WolfwithSword\n"
        msg += "Annoy him when this breaks"
        await ctx.send(msg)

    @mod.command(brief="Open up settings folder for configuration. Only works on the machine running the bot.")
    async def settings(self, ctx):
        allowed = False
        if (ctx.author.id == ctx.guild.owner.id):
            allowed = True
        else:
            caller_roles = [r.name for r in ctx.author.roles]
            allowed_roles = []
            for k in self.ROLES:
                if(self.ROLES[k] == 3):
                    allowed_roles.append(k)
            allowed = False
            for role in allowed_roles:
                if not allowed and role in caller_roles:
                    allowed = True
                    break
        if not allowed:
            await ctx.send("You do not have permission for this command")
            return

        path = os.path.realpath(str(data_manager.bundled_data_path(self)))
        print("\n" + path + "\\settings.json\n")
        await ctx.send("Opening folder with settings.json")
        webbrowser.open(path)
