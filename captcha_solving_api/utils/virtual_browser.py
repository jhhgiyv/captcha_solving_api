import os.path
import queue
import random
from contextlib import contextmanager

from DrissionPage import ChromiumPage, ChromiumOptions
from loguru import logger

from config import settings

workers = queue.Queue()
workers_list = list(range(settings.virtual_browser_worker_start, settings.virtual_browser_worker_end))
random.shuffle(workers_list)
list(map(workers.put, workers_list))
browser_path = os.path.join(os.getenv('LOCALAPPDATA'), r'VirtualBrowser\Application\VirtualBrowser.exe')


@contextmanager
def get_page(proxy, user_agent=None):
    arguments = [
        "-no-first-run",
        "-force-color-profile=srgb",
        "-metrics-recording-only",
        "-password-store=basic",
        "-use-mock-keychain",
        "-export-tagged-pdf",
        "-no-default-browser-check",
        "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
        "-deny-permission-prompts",
        "-disable-gpu",
    ]
    worker = workers.get()
    logger.info(f"Worker {worker} is assigned to the task.")
    userdata_path = os.path.join(os.getenv('LOCALAPPDATA'), rf'VirtualBrowser\Workers\{worker}')
    co = ChromiumOptions().set_browser_path(browser_path).set_user_data_path(userdata_path).auto_port()
    co.set_argument('--worker-id', str(worker)).set_argument("--lang", "en-US").set_argument("--tz", "America/New_York")
    if user_agent:
        co.set_argument("--user-agent", user_agent)
    if settings.drission_page_headless:
        co.headless()
    co.incognito(True)
    co.set_proxy(proxy)
    page = ChromiumPage(co)
    for argument in arguments:
        co.set_argument(argument)
    if settings.debug_screen:
        page.screencast.set_save_path(os.path.join("debug", "screenshots"))
        page.screencast.set_mode.video_mode()
        page.screencast.start()

    try:
        yield page
    finally:
        page.screencast.stop()
        page.close()
        page.quit(5, True)
        workers.put(worker)
