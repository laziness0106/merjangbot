# 브라우저로 모비라이프 랭킹을 검색하고 결과를 파싱하여 잠시 캐시합니다.
import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


class RankingAccessError(RuntimeError):
    pass


def ranking_url(name):
    return "https://mabimobi.life/ranking?" + urlencode(
        {"character_name": name, "sort_by": "combat", "sort_order": "desc"}
    )


@dataclass(frozen=True)
class Ranking:
    name: str
    server: str
    klass: str
    global_rank: int | None
    server_rank: int | None
    combat: int
    charm: int
    life: int
    total: int


def parse_rankings(html):
    soup = BeautifulSoup(html, "html.parser")
    expected = ["통합", "서버", "캐릭터", "서버", "직업", "전투력", "매력", "생활력", "종합"]
    for table in soup.select("table"):
        if [x.get_text(strip=True) for x in table.select("th")] != expected:
            continue
        results = []
        for row in table.select("tbody tr"):
            cells = row.select("td")
            if len(cells) != 9:
                raise ValueError("랭킹 표의 열 구성이 변경되었습니다.")
            values = [x.get_text(strip=True) for x in cells]

            def rank(index):
                if cells[index].select_one("svg.lucide-crown"):
                    return 1
                value = values[index].replace(",", "")
                return int(value) if value.isdecimal() else None

            results.append(Ranking(values[2], values[3], values[4], rank(0), rank(1),
                                   *(int(v.replace(",", "")) for v in values[5:])))
        if results:
            return results
    raise ValueError("랭킹 결과 표를 읽을 수 없습니다.")


class RankingService:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._cache = {}
        self._playwright = None
        self._browser = None

    async def search(self, name):
        name = name.strip()
        if not 2 <= len(name) <= 12:
            raise ValueError("캐릭터 이름은 2~12자로 입력해주세요.")
        # 브라우저와 대기 요청 수를 제한하여 명령어 응답 시간을 보호합니다.
        async with asyncio.timeout(75):
            async with self._lock:
                cached = self._cache.get(name)
                if cached and time.monotonic() - cached[0] < 180:
                    return list(cached[1])
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                if self._browser is None or not self._browser.is_connected():
                    self._browser = await self._playwright.chromium.launch(headless=True)
                page = await self._browser.new_page(viewport={"width": 1440, "height": 900})
                try:
                    response = await page.goto(ranking_url(name), wait_until="domcontentloaded", timeout=30000)
                    if response is not None and response.status in (401, 403, 429):
                        raise RankingAccessError("모비라이프가 자동 조회를 제한하고 있습니다.")
                    if response is None or response.status >= 400:
                        raise RuntimeError("모비라이프 페이지에 접속하지 못했습니다.")
                    ready = page.locator("table tbody tr").or_(
                        page.get_by_text("검색 결과가 없습니다.", exact=True)
                    )
                    await ready.first.wait_for(state="visible", timeout=30000)
                    if await page.get_by_text("검색 결과가 없습니다.", exact=True).is_visible():
                        results = []
                    else:
                        results = parse_rankings(await page.content())
                    results.sort(key=lambda item: (item.name.casefold() != name.casefold(), -item.combat))
                    if len(self._cache) >= 128:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[name] = (time.monotonic(), tuple(results))
                    return results
                finally:
                    await page.close()

    async def close(self):
        async with self._lock:
            try:
                if self._browser is not None:
                    await self._browser.close()
            finally:
                if self._playwright is not None:
                    await self._playwright.stop()
                self._browser = self._playwright = None
