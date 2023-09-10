import datetime as dt
import os
import zoneinfo

import discord as d
from discord.ext import commands

TIMEZONE = zoneinfo.ZoneInfo(os.getenv("TZ"))


async def can_manage_events(ctx: d.ApplicationContext) -> bool:
    """Returns true if the current user has manage_events."""
    return ctx.author.guild_permissions.manage_events


def now() -> dt.datetime:
    """Returns current datetime timezone aware."""
    return dt.datetime.now(TIMEZONE)


class DateConverter(commands.Converter):
    """Converts from string to datetime.

    Can be used as the input_type of a d.Option
    """

    async def convert(
            self, ctx: d.ApplicationContext, argument: str,) -> dt.datetime:
        """Converts from string to datetime.

        Raises:
            BadArgument: if the datatime conversion failed.
        """
        try:
            return dt.datetime.fromisoformat(argument).astimezone(TIMEZONE)
        except Exception:
            raise commands.BadArgument(
                f"Sorry, I don't understand the date '{argument}'. "
                "Please use the format [YYYY-MM-DD HH:mm]\n"
                "Example: 2009-01-03 14:15"
            )
