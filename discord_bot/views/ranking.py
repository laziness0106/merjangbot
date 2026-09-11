# 검색한 사용자에게 캐릭터 선택과 결과 페이지 이동 및 원본 링크를 제공합니다.
import discord

from discord_bot.presenters.ranking import build_ranking_embed
from sites.moblife.ranking import ranking_url


class RankingView(discord.ui.View):
    def __init__(self, items, user_id):
        super().__init__(timeout=300)
        self.items = items
        self.user_id = user_id
        self.page = 0
        self.message = None
        self.render()

    def render(self, selected=None):
        self.clear_items()
        if len(self.items) > 1:
            start = self.page * 25
            select = discord.ui.Select(placeholder="조회할 캐릭터를 선택해주세요", options=[
                discord.SelectOption(label=f"{x.server} · {x.name}"[:100],
                                     description=x.klass[:100], value=str(i))
                for i, x in enumerate(self.items[start:start + 25], start)
            ])

            async def choose(interaction):
                item = self.items[int(select.values[0])]
                self.render(item)
                await interaction.response.edit_message(content=None, embed=build_ranking_embed(item), view=self)

            select.callback = choose
            self.add_item(select)
            for label, delta in (("이전", -1), ("다음", 1)):
                button = discord.ui.Button(label=label, disabled=not 0 <= self.page + delta <= (len(self.items) - 1) // 25)

                async def move(interaction, step=delta):
                    self.page += step
                    self.render()
                    await interaction.response.edit_message(view=self)

                button.callback = move
                self.add_item(button)
        item = selected or self.items[0]
        self.add_item(discord.ui.Button(label="모비라이프에서 보기", url=ranking_url(item.name)))

    async def interaction_check(self, interaction):
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message("직접 /랭킹 명령어로 조회해주세요.", ephemeral=True)
        return False

    async def on_timeout(self):
        for item in self.children:
            if not isinstance(item, discord.ui.Button) or item.url is None:
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
