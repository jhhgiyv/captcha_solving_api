from fastapi import FastAPI
from starlette.background import BackgroundTasks

from captcha_solving_api.captcha_solving import CaptchaSolvingTask, tasks
from captcha_solving_api.model import CreateTask, CreateTaskResponse, GetTaskResult, GetTaskResultResponse, \
    TaskResultStatus

app = FastAPI()


@app.post("/createTask")
async def create_task(task: CreateTask, background_tasks: BackgroundTasks) -> CreateTaskResponse:
    captcha_solving_task = CaptchaSolvingTask(task.task)
    background_tasks.add_task(captcha_solving_task.init)
    return await captcha_solving_task.get_CreateTaskResponse()


@app.post("/getTaskResult")
async def get_task_result(task: GetTaskResult) -> GetTaskResultResponse:
    task = tasks.get(task.taskId)
    if task is None:
        return GetTaskResultResponse(errorId=1, errorCode="ERROR_TASKID_INVALID",
                                     errorDescription="任务ID不存在或已失效", status=TaskResultStatus.error)
    return await task.get_task_result()
