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
        user_id: who requested the job.
        create_date: when was the job created.
    """
    id: str
    name: str
    freq: JobFrequency
    user_id: str
    username: str
    create_date: dt.datetime = dt.datetime.now(TZ_ARGENTINA)

    def description(self) -> str:
        return f"Frequency: {self.freq.value} -- User: {self.username}"


def get_all() -> t.List[Job]:
    """Return all the scheduled jobs."""
    return list(chain.from_iterable(_USER_JOBS.values()))


def find(user_id: str) -> t.List[Job]:
    """Returns the jobs scheduled by an user."""
    return _USER_JOBS.get(user_id)


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
    if _USER_JOBS.get(job.user_id) is None:
        _USER_JOBS[job.user_id] = []
    _USER_JOBS[job.user_id].append(job)


def remove(id: str, user_id: str) -> None:
    """Removes the job from the apscheduler and from internal cache."""
    _scheduler.remove_job(id)
    _USER_JOBS[user_id] = [j for j in _USER_JOBS[user_id] if j.id != id]
