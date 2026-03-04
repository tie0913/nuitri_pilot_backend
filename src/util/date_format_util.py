def format_time(dt):
    day = dt.day

    # 计算序数后缀
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    return dt.strftime(f"%b {day}{suffix}, %Y %H:%M")