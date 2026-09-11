# /랭킹 명령어로 캐릭터를 검색하고 결과 카드 또는 서버 선택 메뉴를 보냅니다.
import logging

import discord

from discord_bot.presenters.ranking import build_ranking_embed
from discord_bot.views.ranking import RankingView
from sites.moblife.ranking import RankingAccessError, ranking_url

logger = logging.getLogger(__name__)


def register(bot):
    @bot.tree.command(name="랭킹", description="모비라이프에서 캐릭터의 순위와 능력치를 조회합니다.")
    @discord.app_commands.describe(캐릭터="검색할 캐릭터 이름")
    async def ranking_command(interaction: discord.Interaction, 캐릭터: str):
        name = 캐릭터.strip()
        if not 2 <= len(name) <= 12:
            await interaction.response.send_message("캐릭터 이름은 2~12자로 입력해주세요.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        try:
            items = await bot.ranking.search(name)
            if not items:
                await interaction.followup.send("해당 이름의 캐릭터를 찾지 못했어요.")
                return
            view = RankingView(items, interaction.user.id)
            view.message = await interaction.followup.send(
                content=f"검색 결과 {len(items)}개가 있어요. 캐릭터를 선택해주세요." if len(items) > 1 else None,
                embed=build_ranking_embed(items[0]) if len(items) == 1 else None,
                view=view, wait=True,
            )
        except RankingAccessError:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="모비라이프에서 직접 확인", url=ranking_url(name)))
            await interaction.followup.send(
                "모비라이프에서 봇의 조회를 제한하고 있어요. 아래 링크에서 검색 결과를 확인해주세요.", view=view
            )
        except Exception:
            logger.exception("랭킹 조회 실패")
            await interaction.followup.send("랭킹을 불러오지 못했어요. 잠시 후 다시 시도해주세요.")
