from typing import List, Tuple
from telegram import Bot
from telegram.constants import ParseMode

async def send_long(bot: Bot, chat_id: int, text: str) -> None:
    """Split long text into chunks and send with HTML parsing."""
    lines = text.split("\n")
    part = ""
    for line in lines:
        if len(part) + len(line) + 1 > 4000:
            await bot.send_message(chat_id, part, parse_mode=ParseMode.HTML)
            part = ""
        part += line + "\n"
    if part:
        await bot.send_message(chat_id, part, parse_mode=ParseMode.HTML)

def fmt_table(rows: List[Tuple], headers: List[str]) -> str:
    """Draw ASCII table with HTML pre-formatting."""
    cols = list(zip(headers, *rows))
    widths = [max(len(str(v)) for v in col) for col in cols]
    
    header = " | ".join(f"{headers[i]:^{widths[i]}}" for i in range(len(headers)))
    sep = "-+-".join("-" * w for w in widths)
    
    data_lines = [
        " | ".join(f"{str(row[i]):<{widths[i]}}" for i in range(len(row)))
        for row in rows
    ]
    
    return f"<pre>\n{header}\n{sep}\n{chr(10).join(data_lines)}\n</pre>"
