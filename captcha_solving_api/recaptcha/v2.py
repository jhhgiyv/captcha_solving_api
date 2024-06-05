import asyncio
from typing import Optional

import botright
from botright.playwright_mock import BrowserContext, Page
from playwright_recaptcha import recaptchav2
from loguru import logger
from captcha_solving_api.model import GetTaskResultResponse, Task, CaptchaSolving, TaskResultStatus, Solution


class ReCaptchaV2(CaptchaSolving):
    async def init(self):

        await self.page.route(self.task.websiteURL, lambda route: route.fulfill(
            body=self._html_content.replace('6LcU-rUaAAAAAHG4SFI_PJfVLtYyuVRuU_DRuIXy', self.task.websiteKey),
            status=200))
        await self.page.goto(self.task.websiteURL)

        async with recaptchav2.AsyncSolver(self.page) as solver:
            self.token = await solver.solve_recaptcha(wait=True, wait_timeout=60)
            logger.success(f'ReCaptcha V2 音频打码结果: {self.token}')

    _botright_client: Optional[botright.Botright] = None
    _browser: Optional[BrowserContext] = None
    _html_content: Optional[str] = None

    async def finalize(self):
        await self.page.close()
        await self.page.browser.close()

    def __init__(self, page: Page, task: Task):
        self.page = page
        self.task = task
        self.token: Optional[str] = None

    @classmethod
    async def class_init(cls):
        if cls._botright_client is None:
            cls._botright_client = await botright.Botright()
            cls._browser = await cls._botright_client.new_browser()
            with open('captcha_solving_api/recaptcha/v2-checkbox-auto-nowww.html', 'r') as file:
                cls._html_content = file.read()

            await cls._browser.new_page()

    @classmethod
    async def create_task(cls, task: Task) -> 'CaptchaSolving':
        await cls.class_init()
        ctx = await cls._botright_client.new_browser(proxy=task.proxy.replace('http://', ''))
        page = await ctx.new_page()
        obj = cls(page, task)
        return obj

    async def get_task_result(self) -> GetTaskResultResponse:
        if self.token:
            return GetTaskResultResponse(errorId=0, errorCode="", errorDescription="",
                                         status=TaskResultStatus.ready,
                                         solution=Solution(gRecaptchaResponse=self.token))

        return GetTaskResultResponse(errorId=0, errorCode="",
                                     errorDescription="", status=TaskResultStatus.processing)
