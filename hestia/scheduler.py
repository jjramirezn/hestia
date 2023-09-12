"""Handles all logic pertaining to scheduling jobs

Only this module should interact direclty with the apscheduler.
This module also mantains a friendlier cache of the currently existing
jobs and can be asked about them.

Typical usage example:

    job_id = "..."
    user_id = "..."
    job = Job(id=job_id, user_id=user_id, ...)
    create_interval(func, job, ...)
    ...
    remove(job_id, user_id)
"""
from dataclasses import dataclass
import datetime as dt
import enum
from itertools import chain
import typing as t
import zoneinfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler


_scheduler = AsyncIOScheduler()
_scheduler.start()
TZ_ARGENTINA = zoneinfo.ZoneInfo("America/Buenos_Aires")
_USER_JOBS = {}
_GUILD_USERS_JOBS = {}


class JobFrequency(enum.StrEnum):
    """Frequency of execution for jobs."""
    ONCE = enum.auto()
    WEEKLY = enum.auto()
    DAILY = enum.auto()

    def days(self) -> int:
        """Returns how many days between job execution"""
        return 1 if self is JobFrequency.DAILY else 0

    def weeks(self) -> int:
        """Returns how many months between job execution"""
        return 1 if self is JobFrequency.WEEKLY else 0

    def is_interval(self) -> bool:
        """Returns True if the trigger will be of interval type."""
        return self in [JobFrequency.DAILY, JobFrequency.WEEKLY]


@dataclass
class Job:
    """Represents a job.

    Attributes:
        id: uniquely identifies a job.
        name: frienldy name for the job.
        freq: the frequency of execution.
        guild_id: id of the server of the job
        user_id: who requested the job.
        username: name of the user that requested the job
        message: to print when seeing the job as an unit
        create_date: when was the job created.
    """
    id: str
    name: str
    freq: JobFrequency
    guild_id: str
    user_id: str
    username: str
    message: str
    create_date: dt.datetime = dt.datetime.now(TZ_ARGENTINA)

    def description(self) -> str:
        return f"Frequency: {self.freq.value} -- User: {self.username}"


def get_all(guild_id: str) -> t.List[Job]:
    """Return all the scheduled jobs."""
    users_jobs = _GUILD_USERS_JOBS.get(guild_id)
    return (list(chain.from_iterable(users_jobs.values()))
            if users_jobs is not None else [])


def get(id: str) -> Job:
    """Return a Job if it exists"""
    [guild_id, user_id] = id.split('_')[:2]
    jobs = find(guild_id, user_id)
    if 0 < len(jobs):
        try:
            return next(j for j in jobs if id == j.id)
        except StopIteration:
            pass
    return None


def find(guild_id: str, user_id: str) -> t.List[Job]:
    """Returns the jobs scheduled by an user."""
    users_jobs = _GUILD_USERS_JOBS.get(guild_id)
    return users_jobs.get(user_id) or [] if users_jobs is not None else []


def create_oneoff(
    func: t.Callable[..., t.Awaitable[None]],
    job_id: str,
    run_date: dt.datetime,
    kwargs: dict,
) -> None:
    """Schedules a job to run once at a given time.

    Args:
        func: async function to be ran each time the job fires.
        job_id: to identify the job.
        run_date: when to run tunc.
        kwargs: kwargs that will be passed to func.
    """
    _scheduler.add_job(func, "date", kwargs=kwargs, id=job_id,
                       run_date=run_date)


def create_interval(
    func: t.Callable[..., t.Awaitable[None]],
    job: Job,
    start_date: dt.datetime,
    next_run_time: dt.datetime,
    kwargs: dict,
) -> None:
    """Schedules a job to run indefinetly with a given frequency.

    This function creates a job with the apscheduler and also adds
    it to the internal cache.

    Args:
        func: async function to be ran each time the job fires.
        job: information about the job.
        start_date: datetime to start counting the interval from.
        next_run_time: when to run func for the first time.
        kwargs: kwargs that will be passed to func.
    """
    _scheduler.add_job(func, "interval", kwargs=kwargs, id=job.id,
                       weeks=job.freq.weeks(), days=job.freq.days(),
                       start_date=start_date, next_run_time=next_run_time)
    users_jobs = _GUILD_USERS_JOBS.get(job.guild_id)
    if users_jobs is None:
        users_jobs = {}
        users_jobs[job.user_id] = []
    elif users_jobs.get(job.user_id) is None:
        users_jobs[job.user_id] = []
    users_jobs[job.user_id].append(job)
    _GUILD_USERS_JOBS[job.guild_id] = users_jobs


def remove(id: str) -> None:
    """Removes the job from the apscheduler and from internal cache."""
    _scheduler.remove_job(id)
    [guild_id, user_id] = id.split('_')[:2]
    jobs = find(guild_id, user_id)
    _GUILD_USERS_JOBS[guild_id][user_id] = [j for j in jobs if j.id != id]
