"""Contains all the views for interacting with Jobs.

Views:
    JobListView: for interacting with the enabled jobs.
"""
import textwrap
import typing as t

import discord as d

from .. import scheduler as sch


class JobListView(d.ui.View):
    """View for showing and deleting scheduled job.

    This class handles the ui and the logic for showing a list of
    scheduled jobs in a discord message.
    """
    _job_select: d.ui.Select

    def __init__(self, jobs: t.List[sch.Job]):
        """Initializes the view with a selection list

        Args:
            jobs: list of jobs for initializing the selection list
        """
        super().__init__()
        self._job_select = self._create_select(jobs)
        self.add_item(self._job_select)

    def _create_select(self, jobs: t.List[sch.Job]) -> d.ui.Select:
        """Returns a selection list for the jobs.

        Args:
            jobs: the list of jobs that will be options.

        Returns:
            The newly created selection list
        """
        async def callback(interaction: d.Interaction):
            """Executes when a Job is selected.

            Hides the selection list and asks if the user wants to
            remove the selected job.
            """
            self.remove_item(self._job_select)
            self.add_item(self._create_remove())
            self.add_item(self._create_cancel())
            job = sch.get(self._job_select.values[0])
            await interaction.response.edit_message(
                content=textwrap.dedent(
                    f"""\
                    Create event
                    {job.message}\n\nDo you want to remove this schedule?
                    """),
                view=self,
            )
        select = d.ui.Select(placeholder="Select a schedule job",
                             row=0,
                             options=[_select_option(job) for job in jobs])
        select.callback = callback
        return select

    def _create_remove(self) -> d.ui.Button:
        """Returns the remove button."""
        async def callback(interaction: d.Interaction):
            """Un-schedules the selected job."""
            self.clear_items()
            selected_id = self._job_select.values[0]
            sch.remove(selected_id)
            await interaction.response.edit_message(content="Job removed",
                                                    view=self)
        btn = d.ui.Button(style=d.ButtonStyle.danger, label="Remove", row=0)
        btn.callback = callback
        return btn

    def _create_cancel(self) -> d.ui.Button:
        """Returns the cancel button."""
        async def callback(interaction: d.Interaction):
            """Clears the buttons and the selection."""
            self.clear_items()
            self.add_item(self._job_select)
            await interaction.response.edit_message(
                content="No job was removed",
                view=self,
            )
        btn = d.ui.Button(style=d.ButtonStyle.grey, label='Cancel', row=0)
        btn.callback = callback
        return btn


def _select_option(job: sch.Job) -> d.SelectOption:
    """Returns a discord select option representing a job."""
    return d.SelectOption(label=job.name, value=job.id,
                          description=job.description())
