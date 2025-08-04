class Dispatching:
    @classmethod
    def dispatch_jobs(cls, job_ids: list[str]) -> None:
        from robust_queue.models.job import Job

        jobs = Job.objects.filter(id__in=job_ids)

        for dispatched_job_id in Job.dispatch_all(jobs):
            job_ids = Job.objects.filter(job_id=dispatched_job_id).values_list(
                "id", flat=True
            )
            Job.objects.filter(id__in=job_ids).delete()

        # TODO: check return
        return len(jobs)
