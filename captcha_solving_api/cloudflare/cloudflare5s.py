import threading
import time

from DrissionPage._pages.chromium_page import ChromiumPage
from DrissionPage.errors import ElementNotFoundError
from loguru import logger

from captcha_solving_api.model import CaptchaSolving, GetTaskResultResponse, Task, TaskResultStatus, Solution
from captcha_solving_api.utils.virtual_browser import get_page


class CloudFlare5s(CaptchaSolving):

    def __init__(self, task: Task):
        self.task = task
        self.ua = ""
        self.cookies = None
        self.content = None
        self.request_headers = None
        self.headers = None

    @classmethod
    async def create_task(cls, task: Task) -> 'CaptchaSolving':
        return cls(task)

    async def get_task_result(self) -> GetTaskResultResponse:
        if self.cookies is None:
            return GetTaskResultResponse(status=TaskResultStatus.processing)
        return GetTaskResultResponse(status=TaskResultStatus.ready,
                                     solution=Solution(user_agent=self.ua, cookies=self.cookies, content=self.content,
                                                       request_headers=self.request_headers, headers=self.headers))

    async def finalize(self):
        pass

    def clickCycle(self, page: ChromiumPage):
        # reach the captcha button and click it
        # if iframe does not exist, it means the page is already bypassed.
        if page.wait.ele_displayed('xpath://div/iframe', timeout=1.5):
            time.sleep(1.5)
            title = page.title.lower()

            if "请稍候" in title:
                page('xpath://div/iframe').ele("确认您是真人", timeout=2.5).click()
            else:
                page('xpath://div/iframe').ele("Verify you are human", timeout=2.5).click()
            # The location of the button may vary time to time. I sometimes check the button's location and update
            # the code.

    def isBypassed(self, page: ChromiumPage):
        title = page.title.lower()
        # If the title does not contain "just a moment", it means the page is bypassed.
        # This is a simple check, you can implement more complex checks.
        return "just a moment" not in title and "请稍候" not in title

    def bypass(self, page):
        if not self.task.waitLoad:
            page.set.load_mode.none()
        i = 0
        while not self.isBypassed(page):
            i += 1
            time.sleep(2)
            # A click may be enough to bypass the captcha, if your IP is clean.
            # I haven't seen a captcha that requires more than 3 clicks.
            logger.debug("Verification page detected.  Trying to bypass...")
            time.sleep(2)
            try:
                self.clickCycle(page)
            except ElementNotFoundError as e:
                if i % 2 == 0:
                    page.refresh()
                logger.debug("ElementNotFoundError: " + str(e))

            if i > 6:
                raise Exception("Failed to bypass the captcha")
        if not self.task.waitLoad:
            page.stop_loading()

    @logger.catch
    def _init(self):
        ua = None
        if self.task.userAgent:
            ua = self.task.userAgent
        with get_page(self.task.proxy, ua) as p:

            self.ua = p.user_agent
            p.listen.start(f'{self.task.websiteURL}.*', is_regex=True)
            p.get(self.task.websiteURL)
            for packet in p.listen.steps(timeout=120):
                self.bypass(p)
                self.cookies = p.cookies(as_dict=True)
                self.content = p.html
                logger.debug(packet.response.headers)
                logger.debug(packet.response.status)
                if packet.response.status == 403:
                    continue
                self.request_headers = packet.request.headers
                self.headers = packet.response.headers
                return

    async def init(self):
        thread = threading.Thread(target=self._init)
        thread.start()
