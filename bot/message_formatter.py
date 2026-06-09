from datetime import datetime
import discord


def format_template(template: str, **kwargs) -> str:
    if not template:
        return ""

    user = kwargs.get("user")
    mod = kwargs.get("mod")
    server = kwargs.get("server")
    channel = kwargs.get("channel")
    ts = kwargs.get("timestamp") or datetime.utcnow()

    def _str(v):
        return str(v) if v is not None else "N/A"

    def _attr(obj, attr, default="N/A"):
        val = getattr(obj, attr, None)
        return str(val) if val is not None else default

    replacements = {
        "{user}": _str(user),
        "{user.mention}": _attr(user, "mention", f"<@{_attr(user, 'id')}>"),
        "{user.id}": _attr(user, "id"),
        "{user.name}": _attr(user, "name") if _attr(user, "name") != "N/A" else _attr(user, "display_name"),
        "{user.avatar}": str(getattr(user, "avatar", None) or "N/A"),
        "{user.created_at}": _attr(user, "created_at"),
        "{user.joined_at}": _attr(user, "joined_at"),
        "{mod}": _str(mod),
        "{mod.mention}": _attr(mod, "mention", f"<@{_attr(mod, 'id')}>"),
        "{mod.id}": _attr(mod, "id"),
        "{mod.name}": _attr(mod, "name") if _attr(mod, "name") != "N/A" else _attr(mod, "display_name"),
        "{server}": _attr(server, "name") if server else "N/A",
        "{server.id}": _attr(server, "id"),
        "{server.icon}": str(getattr(server, "icon", None) or "N/A"),
        "{server.member_count}": _attr(server, "member_count"),
        "{reason}": _str(kwargs.get("reason")) if kwargs.get("reason") else "No reason provided",
        "{duration}": _str(kwargs.get("duration")) if kwargs.get("duration") else "permanent",
        "{case_id}": _str(kwargs.get("case_id")),
        "{action}": _str(kwargs.get("action")),
        "{channel}": _attr(channel, "name") if channel else "N/A",
        "{channel.mention}": _attr(channel, "mention") if channel else "N/A",
        "{count}": _str(kwargs.get("count")),
        "{expires_at}": _str(kwargs.get("expires_at")),
        "{new_reason}": _str(kwargs.get("new_reason")),
        "{new_duration}": _str(kwargs.get("new_duration")),
        "{case_type}": _str(kwargs.get("case_type")),
        "{trigger}": _str(kwargs.get("trigger")),
        "{rule}": _str(kwargs.get("rule")),
        "{timestamp}": str(ts),
        "{timestamp.date}": str(ts.date()) if hasattr(ts, "date") else "N/A",
        "{timestamp.time}": str(ts.time()) if hasattr(ts, "time") else "N/A",
        "{success_count}": _str(kwargs.get("success_count")),
        "{fail_count}": _str(kwargs.get("fail_count")),
        "{total}": _str(kwargs.get("total")),
        "{reminder_message}": _str(kwargs.get("reminder_message")),
        "{reminder_set_at}": _str(kwargs.get("reminder_set_at")),
        "{ordinal}": _str(kwargs.get("ordinal")),
        "{image}": _str(kwargs.get("image")),
        "{content}": _str(kwargs.get("content")),
        "{message_link}": _str(kwargs.get("message_link")),
        "{star_count}": _str(kwargs.get("star_count")),
        "{emoji}": _str(kwargs.get("emoji")) if kwargs.get("emoji") else "⭐",
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(key, value if value is not None else "N/A")
    return result


def build_embed(embed_cfg: dict, **kwargs) -> discord.Embed:
    color = embed_cfg.get("color", 0x5865F2)
    if isinstance(color, str) and color.startswith("#"):
        try:
            color = int(color[1:], 16)
        except ValueError:
            color = 0x5865F2

    embed = discord.Embed(color=color)

    if "title" in embed_cfg:
        embed.title = format_template(str(embed_cfg["title"]), **kwargs)
    if "description" in embed_cfg:
        embed.description = format_template(str(embed_cfg["description"]), **kwargs)
    if "footer" in embed_cfg:
        embed.set_footer(text=format_template(str(embed_cfg["footer"]), **kwargs))
    if "thumbnail" in embed_cfg:
        url = format_template(str(embed_cfg["thumbnail"]), **kwargs)
        if url and url != "N/A":
            embed.set_thumbnail(url=url)
    if "image" in embed_cfg:
        url = format_template(str(embed_cfg["image"]), **kwargs)
        if url and url != "N/A":
            embed.set_image(url=url)
    if "fields" in embed_cfg:
        for f in embed_cfg["fields"]:
            name = format_template(str(f.get("name", "")), **kwargs)
            value = format_template(str(f.get("value", "")), **kwargs)
            if name and value:
                embed.add_field(name=name, value=value, inline=f.get("inline", False))

    return embed


async def send_msg(dest, cfg, **kwargs):
    """Send a message using a YAML message config value or plain string."""
    if cfg is None:
        return
    content = None
    embed = None

    if isinstance(cfg, str):
        content = format_template(cfg, **kwargs)
    elif isinstance(cfg, dict):
        if "content" in cfg:
            content = format_template(str(cfg["content"]), **kwargs)
        if "embed" in cfg:
            embed = build_embed(cfg["embed"], **kwargs)
    
    if not content and not embed:
        return
    try:
        await dest.send(content=content, embed=embed)
    except Exception:
        pass


async def send_dm(user, cfg, **kwargs):
    """Send a DM, silently failing."""
    if cfg is None:
        return
    try:
        dm = await user.create_dm()
        await send_msg(dm, cfg, **kwargs)
    except Exception:
        pass
