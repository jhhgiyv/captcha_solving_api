import uuid
from abc import ABC, abstractmethod
from typing import Optional, Type
from loguru import logger
from captcha_solving_api.model import Task, TaskType, GetTaskResultResponse, TaskResultStatus, CaptchaSolving, \
    CreateTaskResponse
from captcha_solving_api.recaptcha.v2 import ReCaptchaV2

task_types: dict[TaskType, Type[CaptchaSolving]] = {
    TaskType.NoCaptchaTaskProxyless: ReCaptchaV2
}


class CaptchaSolvingTask:
    def __init__(self, task: Task):
        self.task = task
        self.task_id = str(uuid.uuid4())
        tasks[self.task_id] = self
        self.solver: Optional[CaptchaSolving] = None
        self.error: Optional[Exception] = None

    async def init(self):
        try:
            self.solver = await task_types[self.task.type].create_task(self.task)
            await self.solver.init()
        except Exception as e:
            self.error = e
            logger.exception(e)
        finally:
            if self.solver is not None:
                await self.solver.finalize()

    async def get_CreateTaskResponse(self):
        return CreateTaskResponse(errorId=0, errorCode="", errorDescription="", taskId=self.task_id)

    async def get_task_result(self) -> GetTaskResultResponse:
        if self.error:
            return GetTaskResultResponse(errorId=1, errorCode="ERROR_INTERNAL_SERVER_ERROR",
                                         errorDescription=str(self.error), taskId=self.task_id)
        if self.solver is None:
            return GetTaskResultResponse(status=TaskResultStatus.processing)
        result = await self.solver.get_task_result()
        if result.status == TaskResultStatus.ready:
            await self.solver.finalize()
            del tasks[self.task_id]
        return result


tasks: dict[str, CaptchaSolvingTask] = {}
