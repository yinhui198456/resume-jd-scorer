#!/usr/bin/env python3
"""recipe_preflight.py v2.4 — SOP 1 数据预检脚本

自动完成：
1. 读取 history.json → 清洗未来日期 → 构建排重黑名单（菜名归一化 + 主食材黑名单）
2. 读取 inventory.json → 自动标记过期食材 → 写回更新后的文件
3. 读取 wishlist.json → 提取意向池
4. 读取 dish_feedback.json → 提取 disliked/loved 列表
5. 生成建议采购清单（基于主材 + 当季补充）
6. 输出 JSON 格式的预检报告（含黑名单、可用食材、过期计数、意向菜品数、feedback、采购建议）

主 agent 解析输出的 JSON 报告，用其中的黑名单和可用食材列表构建候选池。
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# 数据目录：可通过 RECIPE_DATA_DIR 环境变量自定义，默认 ~/.hermes/profiles/life/data/
DATA_DIR = Path(os.environ.get("RECIPE_DATA_DIR", os.path.expanduser("~/.hermes/profiles/life/data")))
HISTORY_FILE = DATA_DIR / "history.json"
INVENTORY_FILE = DATA_DIR / "inventory.json"
WISHLIST_FILE = DATA_DIR / "wishlist.json"
FEEDBACK_FILE = DATA_DIR / "dish_feedback.json"

TODAY = datetime.now().strftime("%Y-%m-%d")
THIRTY_DAYS_AGO = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# 主食材归一化映射：菜名/菜名模式 → 主食材
MAIN_INGREDIENT_MAP = {
    # 鸡肉变体
    "焖鸡": "鸡肉", "豉油鸡": "鸡肉", "白切鸡": "鸡肉", "盐焗鸡": "鸡肉",
    "手撕鸡": "鸡肉", "烧鸡": "鸡肉", "炒鸡": "鸡肉", "烤鸡": "鸡肉",
    "炖鸡": "鸡肉", "蒸鸡": "鸡肉", "三杯鸡": "鸡肉",
    # 鸭肉变体
    "烧鸭": "鸭肉", "烤鸭": "鸭肉", "卤鸭": "鸭肉",
    # 鸽肉
    "鸽子汤": "鸽子", "党参鸽子汤": "鸽子", "盐焗乳鸽": "鸽子", "乳鸽": "鸽子",
    # 猪肉变体
    "红烧肉": "猪肉", "红烧排骨": "猪肉", "糖醋排骨": "猪肉", "粉蒸肉": "猪肉",
    "回锅肉": "猪肉", "小炒肉": "猪肉", "同安封肉": "猪肉",
    "冬瓜丸子汤": "猪肉",
    # 牛肉变体
    "炒牛肉": "牛肉", "炖牛肉": "牛肉", "红烧牛肉": "牛肉", "清炖牛肋条": "牛肉",
    "盐葱牛小排": "牛肉",
    "咖喱牛肉": "牛肉", "咖喱牛腩": "牛肉",
    # 鱼/海鲜变体
    "清蒸": "鱼", "红烧鱼": "鱼", "煎鱼": "鱼", "蒸鱼": "鱼",
    "鲈鱼": "鱼", "鳜鱼": "鱼", "多宝鱼": "鱼", "青花鱼": "鱼", "带鱼": "鱼",
    "白灼鲜虾": "虾", "白灼虾": "虾", "炒虾仁": "虾", "毛豆炒虾仁": "虾",
    "蒜蓉粉丝蒸扇贝": "扇贝", "白炒鲜贝": "鲜贝",
    "爆炒蛏子": "蛏子", "葱油茭白蛏子": "蛏子",
    # 黄鳝变体
    "黄鳝": "黄鳝", "响油鳝丝": "黄鳝", "毛豆烧黄鳝": "黄鳝", "红烧黄鳝": "黄鳝",
    "鳝丝": "黄鳝", "鳝鱼": "黄鳝",
    # 小龙虾
    "小龙虾": "小龙虾", "蒜蓉小龙虾": "小龙虾", "冰醉小龙虾": "小龙虾",
    # 蟹
    "六月黄": "蟹", "红烧六月黄": "蟹",
    # 蛋
    "炒蛋": "蛋", "蒸蛋": "蛋", "蛋花汤": "蛋", "番茄蛋花汤": "蛋", "紫菜蛋花汤": "蛋",
    # 豆腐
    "豆腐": "豆腐", "锅塌豆腐": "豆腐", "虾仁蒸豆腐": "豆腐",
    # 蔬菜/其他
    "拍黄瓜": "黄瓜", "蒜蓉炒苋菜": "苋菜", "上汤苋菜": "苋菜",
    "蒜蓉空心菜": "空心菜", "腐乳炒空心菜": "空心菜",
    "油焖茭白": "茭白", "茭白炒肉丝": "茭白",
    "干煸豆角": "豆角", "肉末豇豆": "豇豆",
    "丝瓜炒蛋": "丝瓜", "丝瓜虾仁汤": "丝瓜", "蒜蓉蒸丝瓜": "丝瓜",
    # 毛豆烧鸡 → 鸡肉是主材，毛豆是配菜。毛豆烧黄鳝 → 黄鳝是主材
    "毛豆烧鸡": "鸡肉", "毛豆烧黄鳝": "黄鳝",
    "葱油蚕豆": "蚕豆", "蚕豆炒蛋": "蚕豆",
    "芦笋炒牛肉": "芦笋",
    "烤蔬菜拼盘": "蔬菜拼盘",
    "豌豆焖饭": "豌豆",
    "杂粮饭": "杂粮",
    "白米饭": "大米",
}


def load_json(filepath):
    """加载 JSON 文件，文件不存在时返回空数组。"""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    """保存 JSON 文件。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_ingredient(dish_name):
    """从菜名提取主食材（归一化）。"""
    # 精确匹配
    if dish_name in MAIN_INGREDIENT_MAP:
        return MAIN_INGREDIENT_MAP[dish_name]
    # 模糊匹配：菜名包含关键词
    for key, ingredient in MAIN_INGREDIENT_MAP.items():
        if key in dish_name:
            return ingredient
    # 烹饪方法变体：烧X/炒X/烤X/炖X/蒸X/煎X
    import re
    m = re.match(r"^(红烧|爆炒|清炒|干煸|油焖|葱油|蒜蓉|清蒸|盐焗|白灼|白炒|酱爆|葱爆)(.*)", dish_name)
    if m:
        method, main = m.groups()
        # 如果 main 本身能被归一化
        for key, ingredient in MAIN_INGREDIENT_MAP.items():
            if key in main:
                return ingredient
        # main 不在 MAP 中，继续走 fallback（不直接返回 main）

    # ─── 泛化 fallback：正则提取食材关键词（P2⑥ 新增） ───
    # 当精确匹配和模糊匹配都失败时，尝试从菜名中提取食材关键词
    INGREDIENT_KEYWORDS = {
        # 肉类
        r"猪": "猪肉", r"肋排": "猪肉", r"五花": "猪肉", r"蹄": "猪肉", r"肠": "猪肉",
        r"牛": "牛肉", r"腩": "牛肉",
        r"羊": "羊肉",
        r"鸡": "鸡肉", r"翅": "鸡肉", r"腿": "鸡肉", r"胸": "鸡肉",
        r"鸭": "鸭肉", r"鹅": "鹅肉",
        r"鸽": "鸽子", r"乳鸽": "鸽子",
        # 水产
        r"鳝": "黄鳝", r"鳅": "黄鳝",
        r"虾": "虾", r"蟹": "蟹",
        r"蛏": "蛏子", r"蛤": "蛤蜊", r"螺": "螺",
        r"鱼": "鱼", r"鲈": "鱼", r"鳜": "鱼", r"鲤": "鱼", r"鲫": "鱼", r"鲳": "鱼", r"带": "鱼",
        r"贝": "鲜贝", r"扇贝": "扇贝", r"鲍": "鲍鱼",
        # 蛋/豆/蔬菜
        r"蛋": "蛋", r"豆腐": "豆腐", r"豆干": "豆腐",
        r"苋": "苋菜", r"丝瓜": "丝瓜", r"冬瓜": "冬瓜", r"南瓜": "南瓜",
        r"空心": "空心菜", r"茭白": "茭白", r"毛豆": "毛豆", r"蚕豆": "蚕豆",
        r"豇豆": "豇豆", r"豆角": "豆角", r"茄子": "茄子", r"秋葵": "秋葵",
    }
    for pattern, ingredient in INGREDIENT_KEYWORDS.items():
        if re.search(pattern, dish_name):
            return ingredient

    return dish_name


def build_blacklist(history):
    """从 history.json 构建 30 天排重黑名单。"""
    # 清洗未来日期
    cleaned = [h for h in history if h.get("date", "9999") <= TODAY]
    # 清理超过30天的条目
    recent = [h for h in cleaned if h.get("date", "0") >= THIRTY_DAYS_AGO]

    dish_names = set()
    main_ingredients = set()

    for entry in recent:
        for dish in entry.get("dishes", []):
            dish_names.add(dish)
            ingredient = normalize_ingredient(dish)
            main_ingredients.add(ingredient)

    return {
        "dish_names": sorted(dish_names),
        "main_ingredients": sorted(main_ingredients),
        "total_entries": len(recent),
        "cleaned_future_dates": len(history) - len(cleaned),
    }


def check_inventory(inventory):
    """检查库存，标记过期食材，写回更新后的文件。"""
    expired_count = 0
    available_items = []

    for item in inventory:
        expire = item.get("expire_date", "")
        if expire and expire < TODAY and item.get("status") != "expired":
            item["status"] = "expired"
            expired_count += 1
        elif item.get("status") == "available":
            available_items.append(item.get("name", ""))

    save_json(INVENTORY_FILE, inventory)
    return {
        "expired_count": expired_count,
        "available_items": sorted(available_items),
        "total_items": len(inventory),
    }


def load_wishlist():
    """加载意向池，按 priority 排序，标记过期项。"""
    wishlist = load_json(WISHLIST_FILE)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    wishlist.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))

    # 标记超过 60 天的 stale 条目
    stale_items = []
    from datetime import datetime, timedelta
    sixty_days_ago = datetime.now() - timedelta(days=60)
    for w in wishlist:
        added = w.get("added_date", "")
        if added:
            try:
                if datetime.strptime(added, "%Y-%m-%d") < sixty_days_ago:
                    w["stale"] = True
                    stale_items.append(w["name"])
            except ValueError:
                pass

    return wishlist, stale_items


def load_feedback():
    """加载 dish_feedback.json，提取 disliked/loved 列表。"""
    feedback = load_json(FEEDBACK_FILE)
    disliked = [f["dish_name"] for f in feedback if f.get("rating") == "dislike"]
    loved = [f["dish_name"] for f in feedback if f.get("rating") == "love"]
    return {
        "disliked_dishes": disliked,
        "loved_dishes": loved,
        "total_entries": len(feedback),
    }


def main():
    history = load_json(HISTORY_FILE)
    inventory = load_json(INVENTORY_FILE)
    wishlist, stale_items = load_wishlist()
    feedback = load_feedback()

    blacklist = build_blacklist(history)
    inv_status = check_inventory(inventory)

    # ─── 生成建议采购清单（增强版：基于主材而非菜名） ───
    # 从 wishlist high priority 菜品提取主材
    restock_from_wishlist = []
    wishlist_ingredients = set()
    for w in wishlist:
        if w.get("priority") == "high" and not w.get("stale", False):
            ingredient = normalize_ingredient(w["name"])
            restock_from_wishlist.append({"dish": w["name"], "ingredient": ingredient})
            wishlist_ingredients.add(ingredient)

    # 当季热门菜补充（wishlist 不足 3 道时）
    SEASONAL_DISHES = [
        ("红烧黄鳝", "黄鳝"), ("蒜蓉炒苋菜", "苋菜"), ("上汤空心菜", "空心菜"),
        ("丝瓜虾仁汤", "丝瓜"), ("毛豆炒肉丝", "毛豆"), ("清炒冬瓜", "冬瓜"),
    ]
    restock_from_seasonal = []
    if len(wishlist_ingredients) < 3:
        for dish, ingredient in SEASONAL_DISHES:
            if ingredient not in wishlist_ingredients and ingredient not in inv_status["available_items"]:
                restock_from_seasonal.append({"dish": dish, "ingredient": ingredient})
                wishlist_ingredients.add(ingredient)
                if len(wishlist_ingredients) >= 3:
                    break

    all_ingredients = sorted(wishlist_ingredients)

    restock_suggestions = {
        "from_wishlist": restock_from_wishlist,
        "from_seasonal": restock_from_seasonal,
        "unique_ingredients": all_ingredients,
        "total_items": len(all_ingredients),
    }

    # 检查库存是否全过期（修复：即使已标记 expired 也要正确判断）
    all_expired = len(inv_status["available_items"]) == 0 and inv_status["total_items"] > 0

    report = {
        "date": TODAY,
        "blacklist": blacklist,
        "inventory": inv_status,
        "all_inventory_expired": all_expired,
        "restock_suggestions": restock_suggestions,
        "feedback": feedback,
        "wishlist": [{"name": w["name"], "priority": w.get("priority", "medium"), "added_date": w.get("added_date", ""), "stale": w.get("stale", False)} for w in wishlist],
        "wishlist_count": len(wishlist),
        "stale_wishlist_items": stale_items,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
