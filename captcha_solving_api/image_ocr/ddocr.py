import base64
from typing import Optional

import ddddocr
from loguru import logger

from captcha_solving_api.model import CaptchaSolving, GetTaskResultResponse, Task, Solution, TaskResultStatus
from config import settings


class DdddOcrModelV1(CaptchaSolving):
    _ocr = ddddocr.DdddOcr(use_gpu=settings.use_gpu, device_id=settings.device_id, show_ad=False)
    _ocr_beat = ddddocr.DdddOcr(use_gpu=settings.use_gpu, device_id=settings.device_id, beta=True,
                                show_ad=False)

    def __init__(self, task: Task):
        self._task = task
        self.text: Optional[str] = None
        self.image = base64.b64decode(task.body)

    @classmethod
    async def create_task(cls, task: Task) -> 'CaptchaSolving':
        return cls(task)

    async def get_task_result(self) -> GetTaskResultResponse:
        if self.text:
            return GetTaskResultResponse(errorId=0, errorCode="", errorDescription="",
                                         status=TaskResultStatus.ready,
                                         solution=Solution(text=self.text))
        return GetTaskResultResponse(errorId=0, errorCode="", errorDescription="", status=TaskResultStatus.processing)

    async def finalize(self):
        self._ocr.set_ranges('')
        self._ocr_beat.set_ranges('')

    async def init(self):
        if not self._task.ddddOcrSettings:
            self.text = self._ocr.classification(self.image)
            logger.success(f'识别结果: {self.text}')
            return
        ocr = self._ocr
        if self._task.ddddOcrSettings.bata:
            ocr = self._ocr_beat
        if self._task.ddddOcrSettings.set_ranges:
            ocr.set_ranges(self._task.ddddOcrSettings.set_ranges)
        self.text = ocr.classification(self.image, self._task.ddddOcrSettings.png_fix)
        logger.success(f'识别结果: {self.text}')
