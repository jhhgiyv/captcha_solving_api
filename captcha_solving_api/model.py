from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, TypeVar

from pydantic import BaseModel


class TaskType(Enum):
    NoCaptchaTaskProxyless = 'NoCaptchaTaskProxyless'
    TurnstileTaskS2 = 'TurnstileTaskS2'


class CreateTaskResponse(BaseModel):
    errorId: int
    errorCode: str
    errorDescription: str
    taskId: str


class Task(BaseModel):
    type: TaskType
    websiteURL: Optional[str] = None
    websiteKey: Optional[str] = None
    proxy: Optional[str] = None
    isInvisible: Optional[bool] = False


class SolutionResult(BaseModel):
    pass


class CreateTask(BaseModel):
    clientKey: str
    task: Task


class GetTaskResult(BaseModel):
    clientKey: str
    taskId: str


class TaskResultStatus(Enum):
    processing = 'processing'
    ready = 'ready'
    error = 'error'


class Solution(BaseModel):
    gRecaptchaResponse: Optional[str] = None

    class Config:
        exclude_none = True


class GetTaskResultResponse(BaseModel):
    errorId: int = 0
    errorCode: str = ''
    errorDescription: str = ''
    status: TaskResultStatus
    solution: Optional[Solution] = None


class CaptchaSolving(ABC):
    @classmethod
    @abstractmethod
    async def create_task(cls, task: Task) -> 'CaptchaSolving':
        pass

    @abstractmethod
    async def get_task_result(self) -> GetTaskResultResponse:
        pass

    @abstractmethod
    async def finalize(self):
        pass

    @abstractmethod
    async def init(self):
        pass
