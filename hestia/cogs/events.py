"""Contains all the commands about discord events handling

Commands:
    create_event_schedule: schedule a job for automatically creating events
    schedules: see a list of currently scheduled jobs
"""
import os
import datetime as dt

import discord as d
from discord.ext import commands
from loguru import logger

from .. import scheduler as sch
from .. import utils
from ..views.job import JobListView

SERVER_IDS = os.getenv("HESTIA_DISCORD_SERVER_IDS").replace(" ", "").split(",")


class Events(commands.Cog):
    """Commands for interacting with discord events."""

    def __init__(self, bot: d.Bot):
        """Initializes this Cog."""
        self.bot = bot

    @d.slash_command(
        description="Schedule an event",
        guild_ids=SERVER_IDS,
    )
    @commands.check(utils.can_manage_events)
    async def create_event_schedule(
        self,
        ctx: d.ApplicationContext,
        name: d.Option(str, description="Event name"),    # noqa: F722
        start_datetime: d.Option(
            utils.DateConverter,
            description="Date and time of first event: YYYY-MM-DD HH:mm"# noqa
        ),
        repeat: d.Option(
            str,
            description="How often should we repeat this event",  # noqa: F722
            choices=[e.value for e in sch.JobFrequency]
        ),
        hours_before: d.Option(
            int,
            description="How many hours before start date",      # noqa: F722
        ),
        stage_loc: d.Option(
            d.StageChannel,
            description="Stage Channel. Only one 'loc' arg accepted",  # noqa
            default=None,
        ),
        voice_loc: d.Option(
            d.VoiceChannel,
            description="Voice Channel. Only one 'loc' arg accepted",  # noqa
            default=None,
        ),
        offline_loc: d.Option(
            str,
            description="Address. Only one 'loc' arg accepted",  # noqa: F722
            default=None,
        ),
        end_datetime: d.Option(
            utils.DateConverter,
            description="Date and time to end event: YYYY-MM-DD HH:mm",  # noqa
            default=None
        ),
    ) -> None:
        """Creates a job for creating events in discord."""
        locs = [stage_loc, voice_loc, offline_loc]
        locs = [loc for loc in locs if loc is not None]
        if 1 != len(locs):
            await ctx.respond("Please provide exactly one location",
                              ephemeral=True)
            return
        location = locs[0]
        if location is offline_loc:
            if end_datetime is None:
                await ctx.respond("Offline locations need a end datetime",
                                  ephemeral=True)
                return
        else:
            end_datetime = None
        user_id = str(ctx.user.id)
        job_id = f"{ctx.guild_id}_{user_id}_{ctx.interaction.id}"
        event_kwargs = {
            "guild_id": ctx.guild_id,
            "event_name": name,
            "location": location,
        }
        freq = sch.JobFrequency(repeat)
        if (sch.JobFrequency.ONCE == freq):
            run_date = start_datetime - dt.timedelta(hours=hours_before)
            event_kwargs["start_datetime"] = start_datetime
            event_kwargs["end_datetime"] = end_datetime
            sch.create_oneoff(
                self._create_single_event,
                job_id=job_id,
                run_date=max(run_date, utils.now()),
                kwargs=event_kwargs,
            )
        elif (freq.is_interval):
            job = sch.Job(
                id=job_id,
                name=f"Create event '{name}'",
                freq=freq,
                guild_id=str(ctx.guild_id),
                user_id=user_id,
                username=ctx.author.name,
            )
            start_date = start_datetime - dt.timedelta(hours=hours_before)
            event_kwargs["first_start"] = start_datetime
            event_kwargs["first_end"] = end_datetime
            event_kwargs["hours_until"] = hours_before
            sch.create_interval(
                self._create_event,
                job,
                start_date=start_date,
                next_run_time=max(start_date, utils.now()),
                kwargs=event_kwargs
            )
        await ctx.respond("Successfully created schedule", ephemeral=True)

    @create_event_schedule.error
    async def create_event_schedule_error(
        self,
        ctx: d.ApplicationContext,
        error: commands.CommandError,
    ) -> None:
        """Handles any error raised by the create_event_schedule command."""
        if isinstance(error, commands.BadArgument):
            await ctx.respond(str(error), ephemeral=True)
        elif (isinstance(error, d.ApplicationCommandInvokeError)
                and isinstance(error.__cause__, d.HTTPException)
                and 400 == error.__cause__.status):
            await ctx.respond(error.__cause__.text, ephemeral=True)
        else:
            logger.exception("create_event_schedule_error:")
            await ctx.respond("Internal Error.", ephemeral=True)

    @d.slash_command(
        description="Get list of your scheduled jobs",
        guild_ids=SERVER_IDS,
    )
    @commands.check(utils.can_manage_events)
    async def schedules(self, ctx: d.ApplicationContext) -> None:
        """Command for interacting with scheduled jobs."""
        if ctx.author.guild_permissions.administrator:
            jobs = sch.get_all(str(ctx.guild_id))
        else:
            jobs = sch.find(str(ctx.guild_id), str(ctx.user.id))
        if len(jobs) == 0:
            await ctx.respond("These are no scheduled jobs", ephemeral=True)
        else:
            await ctx.respond("These are the scheduled jobs",
                              view=JobListView(jobs), ephemeral=True)

    async def _create_single_event(
        self,
        guild_id: int,
        event_name: str,
        location: d.ScheduledEventLocation,
        start_datetime: dt.datetime,
        end_datetime: dt.datetime,
    ) -> None:
        """Creates an event in discord.

        Args:
            guild_id: id of the guild where we will create the event.
            event_name: name of the event.
            location: can be a string, a voice channel or a stage channel.
            start_datetime: start of the event
            end_datetime: end ot the event
        """
        guild = self.bot.get_guild(guild_id)
        if end_datetime is None:
            await guild.create_scheduled_event(name=event_name,
                                               start_time=start_datetime,
                                               location=location)
        else:
            await guild.create_scheduled_event(name=event_name,
                                               start_time=start_datetime,
                                               end_time=end_datetime,
                                               location=location)

    async def _create_event(
        self,
        guild_id: int,
        event_name: str,
        location: d.ScheduledEventLocation,
        first_start: dt.datetime,
        first_end: dt.datetime,
        hours_until: int,
    ) -> None:
        """Creates an event in discord in the context of a scheduled job.

        This function is aware that it can be called multiple times, and
        takes that into consideration

        Args:
            guild_id: id of the guild where we will create the event.
            event_name: name of the event.
            location: can be a string, a voice channel or a stage channel.
            first_start: when will the first event start.
            firs_end: when will gthe first event end.
            hours_until: how many hours from now will the event start
        """
        now = utils.now()
        if now < first_start:
            start_date = first_start
            end_date = first_end
        else:
            start_date = now + dt.timedelta(hours=hours_until)
            start_date.replace(
                hour=first_start.hour,
                minute=first_start.minute,
                second=first_start.second,
            )
            end_date = (start_date + (first_end - first_start)
                        if first_end is not None else None)
        await self._create_single_event(guild_id, event_name, location,
                                        start_date, end_date)


def setup(bot: d.Bot) -> None:
    """Integrates this cog into the bot"""
    bot.add_cog(Events(bot))
