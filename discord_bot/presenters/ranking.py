# 캐릭터의 서버·직업·전투력 순위와 능력치를 디스코드 카드로 표시합니다.
import discord


def build_ranking_embed(item):
    def rank(value):
        return f"{value:,}위" if value is not None else "정보 없음"

    embed = discord.Embed(title=f"🏆 {item.name}", color=0xE8B44A,
                          description=f"**{item.server} 서버 · {item.klass}**")
    embed.add_field(name="전투력 순위", value=f"전체 **{rank(item.global_rank)}** · 서버 **{rank(item.server_rank)}**", inline=False)
    for label, value in (("⚔️ 전투력", item.combat), ("✨ 매력", item.charm),
                         ("🌿 생활력", item.life), ("📊 종합", item.total)):
        embed.add_field(name=label, value=f"{value:,}", inline=True)
    embed.set_footer(text="출처: 모비라이프 · 전투력 기준 · 조회 결과 최대 3분 캐시")
    return embed
