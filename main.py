
import os
import discord
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option, create_choice

import datetime
import json
from typing import Tuple, Union


class Voter:
    def __init__(self, name: str, opinion: str, option: str):
        self.name: str = name
        self.opinion: str = opinion
        self.option: str = option

    def repr(self, anonymous: bool = False) -> Tuple[str, str]:  # title and body
        print(self.opinion)
        title = f"""{self.name if not anonymous else "Anonymous"} {f'voted "{self.option}"' if self.option.lower() in 
                ("yes", "no") else "absented"} and {"said:" if self.opinion != "" else '''didn't say nothing'''}"""
        body = self.opinion + "..."
        return title, body

class Log:
    def __init__(self, title: str, text: str, name:str):
        self.abstract = {
            "name": name,
            "type": "log",
            "title": title,
            "text": text,
            "time written [gmt]": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def repr(self):
        return


class Vote:
    def __init__(self, name: str, description: str = "", anonymous: bool = False) -> None:
        self.haveVoted: set[str] = set([])
        self.voters: set[Voter] = set([])
        self.isAnonymous = anonymous
        self.abstract = {
            "name": name,
            "type": "voting",
            "description": description,
            "time started [gmt]": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "time closed [gmt]": None,
            "yes": 0,
            "abstain": 0,
            "no": 0,
            "ended": False
        }

    def addVote(self, voter: Voter) -> None:
        if voter.name not in self.haveVoted:
            self.haveVoted.update({voter.name})
            self.voters.update({voter})
            self.abstract[voter.option] += 1

    def removeVote(self, voter: Voter) -> bool:
        if voter.name in self.haveVoted:
            self.haveVoted.discard(voter.name)
            self.voters.discard(voter)
            self.abstract[voter.option] -= 1
            return True
        return False

    def getVoters(self):
        return f"""```json\n{json.dumps({"voters": list(self.haveVoted)}, indent=4)}\n```"""

    def endVote(self):
        self.abstract["ended"] = True
        self.abstract["time closed [gmt]"] = datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%Z")

    def value(self) -> str:
        return f"""```json\n{json.dumps(self.abstract, indent=4)}\n```"""

    def result(self) -> Tuple[str, bool]:
        result: int = max(self.abstract["yes"], self.abstract["no"])

        if not self.abstract["ended"]:
            if result == self.abstract["yes"] and result != 0:
                return f"{self.abstract['name']} is winning", True
            else:
                return f"{self.abstract['name']} is losing", False
        else:
            if result == self.abstract["yes"] and result != 0:
                return f"{self.abstract['name']} won", True
            else:
                return f"{self.abstract['name']} lost", False

    def votingResults(self) -> Union[list[tuple[str, str]], None]:
        if self.abstract["ended"]:
            return [x.repr(self.isAnonymous) for x in self.voters]

    def __repr__(self):
        return json.dumps(self.abstract, indent=4)


client = discord.Client()
slash = SlashCommand(client, sync_commands=True)

server_id = [751187212502302880]

logs: dict[str, Vote] = {}
openVotes: set[str] = set()
openVotesOption = [create_choice(name=x, value=x) for x in openVotes]


@client.event
async def on_ready():
    print('pog')


@slash.slash(name="create", guild_ids=server_id, description="create a new pool", options=[
    create_option(
        name="pool_name",
        description="the desired pool name",
        option_type=3,
        required=True,
    ),
    create_option(
        name="description",
        description="the meaning of the pool",
        option_type=3,
        required=True,
    ),
    create_option(
        name="anonymous",
        description="describe if the pool is anonymous or not",
        option_type=5,
        required=False,
    )
])
async def createNewPool(ctx, pool_name: str, description: str = "", anonymous: bool = False):
    logs.update({pool_name.strip(): Vote(pool_name.strip(), description, anonymous)})
    openVotes.update({pool_name.strip()})
    print(openVotes)
    global openVotesOption
    openVotesOption = [create_choice(name=x, value=x) for x in openVotes]
    print(openVotesOption)
    await ctx.send(f"created vote \"{pool_name.strip()}\"")


@slash.slash(name="result", guild_ids=server_id, description="get the result of the desired pool", options=[
    create_option(
        name="pool",
        description="the desired pool to get the result",
        option_type=3,
        required=True,
        choices=openVotesOption
    )
])
async def send_result(ctx, pool: str):
    print(pool)
    print(logs[pool.strip()].result())
    try:
        color = 0x00ff00 if logs[pool.strip()].result()[1] else 0xff0000
        embed = discord.Embed(title=f"results of \"{logs[pool].abstract['name']}\"", description="", color=color)
        embed.add_field(name="data", value=logs[pool].value(), inline=False)
        embed.add_field(name="abstract", value=logs[pool].result()[0], inline=False)
        await ctx.send(embed=embed)
    except KeyError:
        await ctx.send(f"pool \"{pool}\" does not exist")


@slash.slash(name="vote", guild_ids=server_id,
             description="vote on a pool",
             options=[
                 create_option(
                     name="vote",
                     description="your vote",
                     option_type=3,
                     required=True,
                     choices=[
                         create_choice(
                             name="yes",
                             value="yes"
                         ),
                         create_choice(
                             name="no",
                             value="no"
                         ),
                         create_choice(
                             name="absent",
                             value="absent"
                         )
                     ]
                 ),
                 create_option(
                     name="pool",
                     description="pool to vote",
                     option_type=3,
                     required=True,
                     choices=openVotesOption
                 ),
                 create_option(
                     name="name",
                     description="your name",
                     option_type=3,
                     required=True
                 ),
                 create_option(
                     name="description",
                     description="describe your vote if you think its necessary",
                     option_type=3,
                     required=False
                 )
             ])
async def test(ctx, vote: str, pool: str, name: str, description: str = ""):
    voter: Voter = Voter(name, description, vote)
    print(test.__dict__)
    print(openVotes)
    print(logs)
    print(voter.repr())
    logs[pool.strip()].addVote(voter=voter)

    await ctx.send("vote successfully registered")


@slash.slash(name="end", guild_ids=server_id, description="end the desired pool", options=[
    create_option(
        name="pool",
        description="the desired pool to end",
        option_type=3,
        required=True,
        choices=openVotesOption
    )
])
async def endVote(ctx, pool: str):
    logs[pool.strip()].endVote()
    await ctx.send("vote successfully ended")


@slash.slash(name="voters", guild_ids=server_id, description="get all people that voted on the desired vote", options=[
    create_option(
        name="pool",
        description="the desired pool to get the result",
        option_type=3,
        required=True,
        choices=openVotesOption
    )
])
async def getVoters(ctx, pool: str):
    embed = discord.Embed(title="voters", description="they were:", color=0x696969)
    embed.add_field(name="list", value=logs[pool.strip()].getVoters())
    await ctx.send(embed=embed)


@slash.slash(name="help", description="get help", guild_ids=server_id)
async def get_help(ctx):
    embed = discord.Embed(title="botmont-v2 help", description="commands:", color=0x696969)
    embed.add_field(name="`/create`", value="creates a new vote")
    embed.add_field(name="`!vote`", value="votes on a new pool")
    embed.add_field(name="`!voteAbs [vote name]`", value="abstain  to the specified vote")
    embed.add_field(name="`!voteYes [vote name]`", value="vote no to the specified vote")
    embed.add_field(name="`!voteEnd [vote name]`", value="ends the votes to the specified vote")
    embed.add_field(name="`!result [vote name]`", value="shows the result of the election")
    embed.add_field(name="remember that after you vote there is no going back", value="vote with care!")
    await ctx.send(embed=embed)


@slash.slash(name="openPools", description="get open pools", guild_ids=server_id)
async def getPools(ctx):
    embed = discord.Embed(title="open pools", description="listed here", color=0x00ff00)
    allClosed = True
    for pool in logs:
        if not logs[pool.strip()].abstract["ended"]:
            allClosed = False
            embed.add_field(name=f'{logs[pool.strip()].abstract["name"]}  is open', value='your time to vote')

    if allClosed:
        embed = discord.Embed(title="open pools", description="there are no pools open", color=0xff0000)

    await ctx.send(embed=embed)


@slash.slash(name="opinions", guild_ids=server_id, description="get all the opinions from voters", options=[
    create_option(
        name="pool",
        description="the desired pool to get the result",
        option_type=3,
        required=True,
        choices=openVotesOption
    )
])
async def getOpinions(ctx, pool: str):
    result = logs[pool.strip()].votingResults()
    if result is None:
        await ctx.send("you can't get the opinions on a vote if the vote isn't closed")
        return
    embed = discord.Embed(title="open pools", description="listed here", color=0x7f7f7f)
    [embed.add_field(name=x, value=y) for x, y in result]
    await ctx.send(embed=embed)


@slash.slash(name="dumpall", guild_ids=server_id, description="dumps all votes")
async def getOpinions(ctx):
    await ctx.send(f"""```js\n{repr(logs)}\n```""")


@slash.slash(name="log", guild_ids=server_id, description="log a message", options=[
    create_option(
        name="title",
        description="the resume of your log",
        option_type=3,
        required=True,
        choices=openVotesOption
    ),
    create_option(
        name="text",
        description="the full log",
        option_type=3,
        required=True,
        choices=openVotesOption
    ),
    create_option(
        name="signature",
        description="your signature",
        option_type=3,
        required=True,
        choices=openVotesOption
    )
])
async def logSomething(ctx, title: str, text: str, signature: str):
    ...

Token = ""

with open('.env', 'r') as f:
    Token = f.read()

client.run(Token)
