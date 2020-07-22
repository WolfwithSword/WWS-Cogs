from redbot.core import commands, checks
from redbot.core.config import Config
import discord
import re, random

from .default_players import default_players
from .hungergame import HungerGame
from .enums import ErrorCode

class HungerGames(commands.Cog):

    hungerGame: HungerGame = HungerGame()

    def __init__(self):
        self.config = Config.get_conf(self, identifier=59483726163217890101)

    @commands.group()
    async def hg(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            pass

    @hg.command(name="new")
    @checks.bot_in_a_guild()
    async def new(self, ctx, *, title: str = None):
        """
            Start a new Hunger Games simulation in the current channel.
            Each channel can only have one simulation running at a time.

            title - (Optional) The title of the simulation. Defaults to 'The Hunger Games'
        """

        if title is None or title == "":
            title = "The Hunger Games"
        else:
            title = self.__strip_mentions(ctx.message, title)
            title = self.__sanitize_here_everyone(title)
            title = self.__sanitize_special_chars(title)
        owner = ctx.author
        ret = self.hungerGame.new_game(ctx.channel.id, owner.id, owner.name, title)
        if not await self.__check_errors(ctx, ret):
            return
        await ctx.send(
            "{0} has started {1}! Use `{2}hg add <name>` to add a player or `{2}hg join [-m|-f|-o]` to enter the game yourself!\nOr use `{2}hg fill` to fill remaining slots with bots! There are a max of 24 slots, min of 2.\n\nUse `{2}hg start` to start!"
            .format(owner.mention, title, ctx.clean_prefix))

    @hg.command()
    @checks.bot_in_a_guild()
    async def join(self, ctx, gender: str = None):
        """
        Adds a tribute with your name to a new simulation.

        gender (Optional) - Use `-m`, `-f` or `-o` to set male, female or other gender. Defaults to other.
        """
        name = ctx.author.nick if ctx.author.nick is not None else ctx.author.name
        ret = self.hungerGame.add_player(ctx.channel.id, name, gender=gender, isVolunteer=True)
        if not await self.__check_errors(ctx, ret):
            return
        await ctx.send(ret)

    @hg.command()
    @checks.bot_in_a_guild()
    async def add(self, ctx, *, name: str):
        """
        Add a user to a new game.

        name - The name of the tribute to add. Limit 32 chars. Leading and trailing whitespace will be trimmed.
        Special chars @*_`~ count for two characters each.
        """
        name = self.__strip_mentions(ctx.message, name)
        name = self.__sanitize_here_everyone(name)
        name = self.__sanitize_special_chars(name)

        ret = self.hungerGame.add_player(ctx.channel.id, name, gender="OTHER", isVolunteer=False)
        if not await self.__check_errors(ctx, ret):
            return
        await ctx.send(ret)

    @hg.command()
    @checks.bot_in_a_guild()
    async def remove(self, ctx, *, name: str):
        """
        Remove a user from a new game.
        Only the game's host may use this command.

        name - The name of the tribute to remove.
        """
        name = self.__strip_mentions(ctx.message, name)
        name = self.__sanitize_here_everyone(name)
        name = self.__sanitize_special_chars(name)

        ret = self.hungerGame.remove_player(ctx.channel.id, name)
        if not await self.__check_errors(ctx, ret):
            return
        await ctx.send(ret)

    @hg.command()
    @checks.bot_in_a_guild()
    async def fill(self, ctx: commands.Context, fill_with_members: str = None):
        """
        Pad out empty slots in a new game with default characters.

        fill_with_members (Optional) - If set to anything, empty slots will be filled with random members of the server. Otherwise fills with generic bots.
        """
        group = []
        if fill_with_members is not None:

            members:list  = ctx.guild.members
            for i in range(len(members)):
                m = random.choice(members)
                members.remove(m)
                if m.nick is not None:
                    group.append(m.nick)
                else:
                    group.append(m.name)
        else:
            group = default_players.get("hungergames")

        if (len(group) < 24):
            group2 = default_players.get("hungergames")
            while len(group) < 24:
                bot = random.choice(group2)
                group2.remove(bot)
                group.append(bot)

        ret = self.hungerGame.pad_players(ctx.channel.id, group)
        if not await self.__check_errors(ctx, ret):
            return
        await ctx.send(ret)

    @hg.command()
    @checks.bot_in_a_guild()
    async def status(self, ctx):
        """
        Gets the status for the game in the channel.
        """
        ret = self.hungerGame.status(ctx.channel.id)
        if not await self.__check_errors(ctx, ret):
            return
        embed = discord.Embed(title=ret['title'], description=ret['description'])
        embed.set_footer(text=ret['footer'])
        await ctx.send(embed=embed)

    @hg.command()
    @checks.bot_in_a_guild()
    async def start(self, ctx):
        """
        Starts the pending game in the channel.
        """
        ret = self.hungerGame.start_game(ctx.channel.id, ctx.author.id, ctx.clean_prefix)
        if not await self.__check_errors(ctx, ret):
            return
        embed = discord.Embed(title=ret['title'], description=ret['description'])
        embed.set_footer(text=ret['footer'])
        await ctx.send(embed=embed)

    @hg.command()
    @checks.bot_in_a_guild()
    async def end(self, ctx):
        """
        Cancels the current game in the channel.
        """
        ret = self.hungerGame.end_game(ctx.channel.id, ctx.author.id)
        if not await self.__check_errors(ctx, ret):
            return
        await ctx.send(
            "{0} has been cancelled. Anyone may now start a new game with `{1}hg new`.".format(ret.title, ctx.clean_prefix))

    @hg.command()
    @checks.bot_in_a_guild()
    async def step(self, ctx):
        """
        Steps forward the current game in the channel by one round.
        """
        ret = self.hungerGame.step(ctx.channel.id, ctx.author.id)
        if not await self.__check_errors(ctx, ret):
            return
        embed = discord.Embed(title=ret['title'], color=ret['color'], description=ret['description'])
        if ret['footer'] is not None:
            embed.set_footer(text=ret['footer'])
        await ctx.send(embed=embed)

    async def __check_errors(self, ctx, error_code):
        if type(error_code) is not ErrorCode:
            return True
        if error_code is ErrorCode.NO_GAME:
            await ctx.send("There is no game currently running in this channel.")
            return False
        if error_code is ErrorCode.GAME_EXISTS:
            await ctx.send("A game has already been started in this channel.")
            return False
        if error_code is ErrorCode.GAME_STARTED:
            await ctx.send("This game is already running.")
            return False
        if error_code is ErrorCode.GAME_FULL:
            await ctx.send("This game is already at maximum capacity.")
            return False
        if error_code is ErrorCode.PLAYER_EXISTS:
            await ctx.send("That person is already in this game.")
            return False
        if error_code is ErrorCode.CHAR_LIMIT:
            await ctx.send("That name is too long (max 32 chars).")
            return False
        if error_code is ErrorCode.NOT_OWNER:
            await ctx.send("You are not the owner of this game.")
            return False
        if error_code is ErrorCode.INVALID_GROUP:
            await ctx.send("That is not a valid group. Valid groups are:\n```\n{0}\n```"
                            .format("\n".join(list(default_players.keys()))))
            return False
        if error_code is ErrorCode.NOT_ENOUGH_PLAYERS:
            await ctx.send("There are not enough players to start a game. There must be at least 2.")
            return False
        if error_code is ErrorCode.GAME_NOT_STARTED:
            await ctx.send("This game hasn't been started yet.")
            return False
        if error_code is ErrorCode.PLAYER_DOES_NOT_EXIST:
            await ctx.send("There is no player with that name in this game.")
            return False

    def __strip_mentions(self, message: discord.Message, text):
        members = message.mentions
        channels = message.channel_mentions
        roles = message.role_mentions

        for m in members:
            name = m.nick if m.nick is not None else m.name
            text = re.sub(m.mention, name, text)

        for c in channels:
            text = re.sub(c.mention, c.name, text)

        for r in roles:
            text = re.sub(r.mention, r.name, text)

        return text

    def __sanitize_here_everyone(self, text):
        text = re.sub('@here', '@\u180Ehere', text)
        text = re.sub('@everyone', '@\u180Eeveryone', text)
        return text

    def __sanitize_special_chars(self, text):
        text = re.sub('@', '\\@', text)
        text = re.sub('~~', '\\~\\~', text)
        text = re.sub('\*', '\\*', text)
        text = re.sub('`', '\\`', text)
        text = re.sub('_', '\\_', text)
        return text.strip()
