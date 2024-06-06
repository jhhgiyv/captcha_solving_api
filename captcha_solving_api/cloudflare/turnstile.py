import random
import time
from typing import Optional

from botright import botright
from botright.playwright_mock import BrowserContext, Page

from captcha_solving_api.model import CaptchaSolving, GetTaskResultResponse, Task, TaskResultStatus, Solution


class TurnstileSolver(CaptchaSolving):
    _botright_client: Optional[botright.Botright] = None
    _browser: Optional[BrowserContext] = None
    _html_content: Optional[str] = None

    @classmethod
    async def create_task(cls, task: Task) -> 'TurnstileSolver':
        await cls.class_init()
        ctx = await cls._botright_client.new_browser(proxy=task.proxy.replace('http://', ''))
        page = await ctx.new_page()
        obj = cls(page, task)
        return obj

    @classmethod
    async def class_init(cls):
        if cls._botright_client is None:
            cls._botright_client = await botright.Botright(headless=False)
            cls._browser = await cls._botright_client.new_browser()
            with open('captcha_solving_api/cloudflare/page.html', 'r') as file:
                cls._html_content = file.read()

    async def get_task_result(self) -> GetTaskResultResponse:
        if self.output:
            return GetTaskResultResponse(errorId=0, errorCode="", errorDescription="",
                                         status=TaskResultStatus.ready,
                                         solution=Solution(token=self.output, userAgent=self.ua))

        return GetTaskResultResponse(errorId=0, errorCode="",
                                     errorDescription="", status=TaskResultStatus.processing)

    async def finalize(self):
        await self.page.browser.close()

    async def init(self):
        await self.solve(self.task.websiteURL, self.task.websiteKey, self.task.isInvisible)

    def __init__(self, page: Page, task: Task):
        self.page = page
        self.task = task
        self.output: Optional[str] = None
        self.ua = ''

    async def build_page_data(self):
        # this builds a custom page with the sitekey so we do not have to load the actual page, taking less bandwidth
        stub = f"<div class=\"cf-turnstile\" data-sitekey=\"{self.sitekey}\"></div>"
        self._html_content = self._html_content.replace("<!-- cf turnstile -->", stub)

    async def get_mouse_path(self, x1, y1, x2, y2):
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
        for path in await self.get_mouse_path(self.current_x, self.current_y, x, y):
            await self.page.mouse.move(path[0], path[1])
            if random.randint(0, 100) > 15:
                time.sleep(random.randint(1, 5) / random.randint(400, 600))

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
                if elem.get_attribute("value"):
                    return elem.get_attribute("value")
            time.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"

    async def solve_visible(self):

        iframe = await self.page.query_selector("iframe")
        while not iframe:
            iframe = await self.page.query_selector("iframe")
            time.sleep(0.1)
        while not await iframe.bounding_box():
            time.sleep(0.1)

        x = await iframe.bounding_box()
        x = x["x"] + random.randint(5, 12)
        y = await iframe.bounding_box()
        y = y["y"] + random.randint(5, 12)
        await self.move_to(x, y)
        self.current_x = x
        self.current_y = y
        framepage = await iframe.content_frame()
        checkbox = framepage.query_selector("input")

        while not checkbox:
            checkbox = await framepage.query_selector("input")
            time.sleep(0.1)

        width = await checkbox.bounding_box()
        width = width["width"]
        height = await checkbox.bounding_box()
        height = height["height"]

        x = await checkbox.bounding_box()
        x = x["x"] + width / 5 + random.randint(int(width / 5), int(width - width / 5))
        y = await checkbox.bounding_box()
        y = y["y"] + height / 5 + random.randint(int(height / 5), int(height - height / 5))

        await self.move_to(x, y)

        self.current_x = x
        self.current_y = y

        time.sleep(random.randint(1, 5) / random.randint(400, 600))
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
                if elem.get_attribute("value"):
                    return elem.get_attribute("value")
            time.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"

    async def solve(self, url, sitekey, invisible=False):
        self.url = url + "/" if not url.endswith("/") else url
        self.sitekey = sitekey
        self.invisible = invisible

        await self.build_page_data()

        await self.page.route(self.url, lambda route: route.fulfill(body=self._html_content, status=200))
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

        self.ua = await self.page.evaluate("() => navigator.userAgent")
        self.output = output
