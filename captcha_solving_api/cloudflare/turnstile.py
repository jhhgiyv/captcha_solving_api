import asyncio
import random
from typing import Optional

from loguru import logger
from playwright.async_api import Browser, async_playwright

from captcha_solving_api.model import CaptchaSolving, GetTaskResultResponse, Task, TaskResultStatus, Solution
from captcha_solving_api.utils.proxy import proxy2dict
from config import settings


class TurnstileSolver(CaptchaSolving):
    _browser: Optional[Browser] = None
    _html_content: Optional[str] = None

    @classmethod
    async def create_task(cls, task: Task) -> 'CaptchaSolving':
        if not cls._browser:
            playwright = await async_playwright().__aenter__()
            cls._browser = await playwright.firefox.launch(headless=settings.headless)
            with open("captcha_solving_api/cloudflare/page.html") as f:
                cls._html_content = f.read()
        return cls(task)

    async def get_task_result(self) -> GetTaskResultResponse:
        if self.output == "failed":
            return GetTaskResultResponse(errorId=1, status=TaskResultStatus.error)
        if self.output is None:
            return GetTaskResultResponse(status=TaskResultStatus.processing)
        return GetTaskResultResponse(solution=Solution(token=self.output), status=TaskResultStatus.ready)

    async def finalize(self):
        await self.terminate()

    async def init(self):
        await self.start_browser()
        await self.solve(self.task.websiteURL, self.task.websiteKey, self.task.isInvisible)

    def __init__(self, task: Task):
        self.task = task
        self.ctx: Optional[Browser] = None
        self.output: Optional[str] = None

    async def terminate(self):
        await self.ctx.close()

    def build_page_data(self):
        # this builds a custom page with the sitekey so we do not have to load the actual page, taking less bandwidth
        stub = f"<div class=\"cf-turnstile\" data-sitekey=\"{self.sitekey}\"></div>"
        self.page_data = self._html_content.replace("<!-- cf turnstile -->", stub)

    def get_mouse_path(self, x1, y1, x2, y2):
        # calculate the path to x2 and y2 from x1 and y1
        path = []
        x = x1
        y = y1
        while abs(x - x2) > 3 or abs(y - y2) > 3:
            diff = abs(x - x2) + abs(y - y2)
            speed = random.randint(1, 2)
            if diff < 20:
                speed = random.randint(1, 3)
            else:
                speed *= diff / 45

            if abs(x - x2) > 3:
                if x < x2:
                    x += speed
                elif x > x2:
                    x -= speed
            if abs(y - y2) > 3:
                if y < y2:
                    y += speed
                elif y > y2:
                    y -= speed
            path.append((x, y))

        return path

    async def move_to(self, x, y):
        for path in self.get_mouse_path(self.current_x, self.current_y, x, y):
            await self.page.mouse.move(path[0], path[1])
            if random.randint(0, 100) > 15:
                await asyncio.sleep(random.randint(1, 5) / random.randint(400, 600))

    async def solve_invisible(self):
        iterations = 0

        while iterations < 10:
            self.random_x = random.randint(0, self.window_width)
            self.random_y = random.randint(0, self.window_height)
            iterations += 1

            await self.move_to(self.random_x, self.random_y)
            self.current_x = self.random_x
            self.current_y = self.random_y
            elem = await self.page.query_selector("[name=cf-turnstile-response]")
            if elem:
                if await elem.get_attribute("value"):
                    return await elem.get_attribute("value")
            await asyncio.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"

    async def solve_visible(self):
        await self.page.wait_for_selector("iframe")
        iframe = await self.page.query_selector("iframe")
        while not iframe:
            iframe = await self.page.query_selector("iframe")
            await asyncio.sleep(0.1)
        while not await iframe.bounding_box():
            await asyncio.sleep(0.1)

        x = (await iframe.bounding_box())["x"] + random.randint(5, 12)
        y = (await iframe.bounding_box())["y"] + random.randint(5, 12)
        await self.move_to(x, y)
        self.current_x = x
        self.current_y = y
        framepage = await iframe.content_frame()
        logger.info("iframe found", framepage.url)
        checkbox = await framepage.query_selector("input")

        while not checkbox:
            checkbox = await framepage.query_selector("input")
            await asyncio.sleep(0.1)

        width = (await checkbox.bounding_box())["width"]
        height = (await checkbox.bounding_box())["height"]

        x = (await checkbox.bounding_box())["x"] + width / 5 + random.randint(int(width / 5), int(width - width / 5))
        y = (await checkbox.bounding_box())["y"] + height / 5 + random.randint(int(height / 5),
                                                                               int(height - height / 5))

        await self.move_to(x, y)

        self.current_x = x
        self.current_y = y

        await asyncio.sleep(random.randint(1, 5) / random.randint(400, 600))
        await self.page.mouse.click(x, y)

        iterations = 0

        while iterations < 10:
            self.random_x = random.randint(0, self.window_width)
            self.random_y = random.randint(0, self.window_height)
            iterations += 1

            await self.move_to(self.random_x, self.random_y)
            self.current_x = self.random_x
            self.current_y = self.random_y
            elem = await self.page.query_selector("[name=cf-turnstile-response]")
            if elem:
                if await elem.get_attribute("value"):
                    return await elem.get_attribute("value")
            await asyncio.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"

    async def solve(self, url, sitekey, invisible=False):
        self.url = url + "/" if not url.endswith("/") else url
        self.sitekey = sitekey
        self.invisible = invisible
        self.page = await self.ctx.new_page()

        self.build_page_data()

        await self.page.route(self.url, lambda route: route.fulfill(body=self.page_data, status=200))
        await self.page.goto(self.url)
        output = "failed"
        self.current_x = 0
        self.current_y = 0

        self.window_width = await self.page.evaluate("window.innerWidth")
        self.window_height = await self.page.evaluate("window.innerHeight")
        if self.invisible:
            output = await self.solve_invisible()
        else:
            output = await self.solve_visible()

        self.output = output

    async def start_browser(self):
        if self.task.proxy:
            self.ctx = await self._browser.new_context(proxy=proxy2dict(self.task.proxy))
        else:
            self.ctx = await self._browser.new_context()
