from django_tasks import task


@task()
def task1():
    print("AAAAAAA")
