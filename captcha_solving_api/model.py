from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TaskType(Enum):
    NoCaptchaTaskProxyless = 'NoCaptchaTaskProxyless'
    TurnstileTaskS2 = 'TurnstileTaskS2'
    RecaptchaV3TaskProxyless = 'RecaptchaV3TaskProxyless'
    ImageToTextTaskM1 = 'ImageToTextTaskM1'
    FunCaptchaClassification = 'FunCaptchaClassification'


class CreateTaskResponse(BaseModel):
    errorId: int
    errorCode: str
    errorDescription: str
    taskId: str


class DdddOcrSettings(BaseModel):
    bata: Optional[bool] = False
    set_ranges: Optional[str | int] = None
    png_fix: Optional[bool] = False


class Task(BaseModel):
    type: TaskType
    websiteURL: Optional[str] = None
    websiteKey: Optional[str] = None
    proxy: Optional[str] = None
    isInvisible: Optional[bool] = False
    pageAction: Optional[str] = None
    body: Optional[str] = None
    ddddOcrSettings: Optional[DdddOcrSettings] = None
    question: Optional[str] = None
    image: Optional[str] = None


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
    token: Optional[str] = None
    userAgent: Optional[str] = None
    text: Optional[str] = None
    objects: Optional[list[int]] = None
    labels: Optional[list[str]] = None


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
