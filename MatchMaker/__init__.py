from .matchmaker import MatchMaker

def setup(bot):
    bot.add_cog(MatchMaker(bot))