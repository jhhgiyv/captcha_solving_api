from typing import Optional

from botright import botright
from botright.playwright_mock import BrowserContext, Page
from loguru import logger
from playwright_recaptcha import recaptchav3

from captcha_solving_api.model import CaptchaSolving, GetTaskResultResponse, Task, TaskResultStatus, Solution


class ReCaptchaV3(CaptchaSolving):
    async def init(self):
        body = self._html_content.replace('6Lc2GbYaAAAAAO7eQ7Xs4uPdEmlz3BD3aAxf94Lw', self.task.websiteKey)
        body = body.replace('action_submit', self.task.pageAction)
        await self.page.route(self.task.websiteURL, lambda route: route.fulfill(
            body=body,
            status=200))

        async with recaptchav3.AsyncSolver(self.page) as solver:
            await self.page.goto(self.task.websiteURL)
            await self.page.click('#submit')
            self.token = await solver.solve_recaptcha()
            logger.success(f'reCaptcha V3 打码结果: {self.token}')

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

    async def finalize(self):
        await self.page.close()
        await self.page.browser.close()

    def __init__(self, page: Page, task: Task):
        self.page = page
        self.task = task
        self.token: Optional[str] = None

    _botright_client: Optional[botright.Botright] = None
    _browser: Optional[BrowserContext] = None
    _html_content: Optional[str] = None
    _html_content_invisible: Optional[str] = None

    @classmethod
    async def class_init(cls):
        if cls._botright_client is None:
            cls._botright_client = await botright.Botright(headless=False)
            cls._browser = await cls._botright_client.new_browser()
            with open('captcha_solving_api/recaptcha/v3-programmatic.html', 'r') as file:
                cls._html_content = file.read()

            await cls._browser.new_page()
