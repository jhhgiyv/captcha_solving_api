from fastapi import FastAPI
from starlette.background import BackgroundTasks

from captcha_solving_api.captcha_solving import CaptchaSolvingTask, tasks
from captcha_solving_api.model import CreateTask, CreateTaskResponse, GetTaskResult, GetTaskResultResponse, \
    TaskResultStatus
from captcha_solving_api.utils.proxy_bridge import proxy_adapter
from config import settings

app = FastAPI()


@app.post("/createTask")
async def create_task(task: CreateTask, background_tasks: BackgroundTasks) -> CreateTaskResponse:
    if task.clientKey != settings.client_key:
        return CreateTaskResponse(errorId=1, errorCode="ERROR_KEY_DOES_NOT_EXIST",
                                  errorDescription="请检查你的clientKey密钥是否正确", taskId="")
    captcha_solving_task = CaptchaSolvingTask(task.task)
    task.task.proxy = proxy_adapter(task.task.proxy)

    background_tasks.add_task(captcha_solving_task.init)
    return await captcha_solving_task.get_CreateTaskResponse()


@app.post("/getTaskResult", response_model=GetTaskResultResponse, response_model_exclude_unset=True)
async def get_task_result(task: GetTaskResult) \
        -> GetTaskResultResponse:
    if task.clientKey != settings.client_key:
        return GetTaskResultResponse(errorId=1, errorCode="ERROR_KEY_DOES_NOT_EXIST",
                                     errorDescription="请检查你的clientKey密钥是否正确", status=TaskResultStatus.error)
    task = tasks.get(task.taskId)
    if task is None:
        return GetTaskResultResponse(errorId=1, errorCode="ERROR_TASKID_INVALID",
                                     errorDescription="任务ID不存在或已失效", status=TaskResultStatus.error)
    return await task.get_task_result()
