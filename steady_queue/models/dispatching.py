class Dispatching:
    @classmethod
    def dispatch_jobs(cls, job_ids: list[str]) -> int:
        # TODO: can we pass a Job queryset directly?
        from steady_queue.models.job import Job

        jobs = Job.objects.filter(id__in=job_ids)
        dispatched_jobs = Job.dispatch_all(jobs)

        deleted, _ = cls.objects.filter(
            job_id__in=map(lambda j: j.id, dispatched_jobs)
        ).delete()

        return deleted
