from sqlalchemy import Column, ForeignKey, UniqueConstraint, CheckConstraint, case, func, cast
from sqlalchemy.orm import relationship, backref, column_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN, FLOAT
from sqlalchemy.ext.hybrid import hybrid_property, Comparator
from enum import Enum
from .enums import *

Base = declarative_base()

class MapInfo(Base):
    __tablename__ = 'mapinfo'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    Set = Column(TEXT, ForeignKey('mapset.Name'))
    _Map = Column(TEXT, ForeignKey('map.Name'))
    UniqueConstraint('Set','_Map', name='uix_1')

class MapSet(Base):
    __tablename__ = 'mapset'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    Name = Column(TEXT, nullable=False, unique=True)  

class Map(Base):
    __tablename__ = 'map'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    Name = Column(TEXT, nullable=False, unique=True)

class Game(Base):
    __tablename__ = 'game'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    LobbyID = Column(INTEGER, ForeignKey('lobby.id', ondelete="CASCADE"), nullable=False)
    IsPickingTeams = Column(BOOLEAN, default=False)
    Active = Column(BOOLEAN, default=True)
    Completed = Column(BOOLEAN, default=False)
    Set = Column(TEXT, ForeignKey('mapset.Name'), nullable=False)
    _Map = Column(TEXT, ForeignKey('map.Name'), nullable=False)
    GuildID = Column(INTEGER, ForeignKey('lobby.GuildID'), nullable=False)
    ChannelID = Column(INTEGER, ForeignKey('lobby.ChannelID'), nullable=False)

class Team(Base):
    __tablename__ = 'team'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    GuildID = Column(INTEGER, ForeignKey('guild.id'), nullable=False)
    Num = Column(INTEGER, nullable=False)
    ChannelID = Column(INTEGER, nullable=False)
    LobbyID = Column(INTEGER, ForeignKey('lobby.id'), nullable=False)
    Players = relationship("Player", collection_class=list)
    __table_args__ = (
        CheckConstraint(Num <= 2, name="check_team_num"),
        CheckConstraint(Num >= 1, name="check_team_num2"),
        {'sqlite_autoincrement': True})

class Player(Base):
    __tablename__ = 'player'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    UserID = Column(INTEGER, ForeignKey('user.UserID'), nullable=False)
    GuildID = Column(INTEGER, ForeignKey('user.GuildID'), nullable=False)
    LobbyID = Column(INTEGER, ForeignKey('lobby.id'), nullable=False)
    TeamID = Column(INTEGER, ForeignKey('team.id'), nullable=True)
    
class Lobby(Base):
    __tablename__ = 'lobby'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    GuildID = Column(INTEGER, ForeignKey("guild.id"), nullable=False)
    ChannelID = Column(INTEGER, nullable=False)
    UserLimit = Column(INTEGER, default=10)
    GamesPlayed = Column(INTEGER, default=0)
    Games = relationship("Game", collection_class=list, cascade="all,delete", backref="lobby", passive_deletes=True,
                        primaryjoin="and_(Lobby.id == Game.LobbyID)")
    IsPickingTeams = Column(BOOLEAN, default=False)
    Team1 = relationship("Team", uselist=False, primaryjoin="and_(Lobby.id == Team.LobbyID, Team.Num == 1)",
                         backref="lobby", overlaps="Team2, lobby")
    Team2 = relationship("Team", uselist=False, primaryjoin="and_(Lobby.id == Team.LobbyID, Team.Num == 2)",
                         overlaps="Team2, lobby")
    
    PickMode = Column(INTEGER, default=PickMode.Random.value)
    IsPlaying = Column(BOOLEAN, default=False)
    Active = Column(BOOLEAN,default=True);
    Players = relationship("Player", primaryjoin="and_(Lobby.id == Player.LobbyID)")

class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    UserID = Column(INTEGER, nullable=False)
    GuildID = Column(INTEGER, ForeignKey('guild.id'), nullable=False)
    _Score = relationship("Score",
                          primaryjoin="and_(User.UserID == Score.UserID,User.GuildID == Score.GuildID)",
                          back_populates="_User", uselist=False)
    UniqueConstraint('UserID','GuildID', name='uix_2')


class Score(Base):
    __tablename__ = 'score'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    UserID = Column(INTEGER, ForeignKey("user.UserID"), nullable=False)
    GuildID = Column(INTEGER, ForeignKey("user.GuildID"), nullable=False)
    _User = relationship("User", back_populates="_Score",
                         primaryjoin="and_(User.UserID == Score.UserID,User.GuildID == Score.GuildID)")
    Wins = Column(INTEGER, default=0)
    Losses = Column(INTEGER, default=0)
    GamesPlayed = Column(INTEGER, default=0)
    WinRate = Column("WinRate", FLOAT, default=0.0)

    @hybrid_property
    def WinRate(self):
        if self.GamesPlayed == 0:
            return 0.0
        else:
            return float(self.Wins) / float(self.GamesPlayed)

    @WinRate.expression
    def WinRate(cls):
        return case([(cls.GamesPlayed > 0, cast(cls.Wins, FLOAT) / cast(cls.GamesPlayed, FLOAT))], else_ = 0.0)

    @WinRate.comparator
    def WinRate(cls):
        return WinRateComparator( cast(cls.Wins, FLOAT) / cast(cls.GamesPlayed, FLOAT) * 100.00)

class WinRateComparator(Comparator):

    def __eq__(self, other):
        return self.__clause_element__() == other

    def __gt__(self, other):
        return self.__clause_element__() > other

    def __lt__(self, other):
        return self.__clause_element__() < other

class Guild(Base):
    __tablename__ = 'guild'
    id = Column(INTEGER, primary_key=True, nullable=False, unique=True)
    _Blacklist = relationship("BlacklistChannel", back_populates="_Guild",
                              primaryjoin="and_(Guild.id == BlacklistChannel.GuildID)")
                          
class BlacklistChannel(Base):
    __tablename__ = 'blacklistchannel'
    id = Column(INTEGER, primary_key=True, nullable=False, unique=True)
    GuildID = Column(INTEGER, ForeignKey('guild.id'), nullable=False)
    _Guild = relationship("Guild", back_populates="_Blacklist",
                         primaryjoin="and_(Guild.id == BlacklistChannel.GuildID)")
