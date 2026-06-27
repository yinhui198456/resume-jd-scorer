#!/usr/bin/env python3
"""recipe_review_gate.py v1.0 — SOP 1.5 自动审核门（纯规则检查，硬拦截）

输入：JSON 格式的 3 套方案（通过 stdin 或 --input 参数）
输出：PASS / FAIL + 详细问题列表

纯规则检查（不依赖 LLM），覆盖：
- 结构检查：每套必须 2大荤+1素/小荤+1汤+1主食
- 主料撞车：同套方案内主食材（归一化后）不可重复
- 辣味拦截：任何菜含辣/麻/藤椒/花椒等 → FAIL
- 苦瓜拦截：任何菜含苦瓜 → FAIL
- 素菜纯度：标【素】的菜不能含荤料（蛋=荤，皮蛋=蛋=荤）
- 时间检查：单道菜 ≤30分钟（并行前提下）
- 库存标注：每道菜必须有【匹配库存】或【需采购】标注
- 当季创意：每套至少1份当季菜 + 1份特色菜（技法/仪式感/食材组合有亮点，非普通家常菜）
- 30天排重：菜名和主材不在黑名单内
- 同套做法去重：核心技法不可重复

退出码：0=PASS, 1=FAIL
"""

import argparse
import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime, timedelta

# ─── 归一化映射（与 recipe_preflight.py 保持一致） ───
MAIN_INGREDIENT_MAP = {
    "焖鸡": "鸡肉", "豉油鸡": "鸡肉", "白切鸡": "鸡肉", "盐焗鸡": "鸡肉",
    "手撕鸡": "鸡肉", "烧鸡": "鸡肉", "炒鸡": "鸡肉", "烤鸡": "鸡肉",
    "炖鸡": "鸡肉", "蒸鸡": "鸡肉", "三杯鸡": "鸡肉",
    "烧鸭": "鸭肉", "烤鸭": "鸭肉", "卤鸭": "鸭肉",
    "鸽子汤": "鸽子", "党参鸽子汤": "鸽子", "盐焗乳鸽": "鸽子", "乳鸽": "鸽子",
    "红烧肉": "猪肉", "红烧排骨": "猪肉", "糖醋排骨": "猪肉", "粉蒸肉": "猪肉",
    "回锅肉": "猪肉", "小炒肉": "猪肉", "同安封肉": "猪肉",
    "冬瓜丸子汤": "猪肉",
    "炒牛肉": "牛肉", "炖牛肉": "牛肉", "红烧牛肉": "牛肉", "清炖牛肋条": "牛肉",
    "盐葱牛小排": "牛肉",
    "咖喱牛肉": "牛肉", "咖喱牛腩": "牛肉",
    "清蒸": "鱼", "红烧鱼": "鱼", "煎鱼": "鱼", "蒸鱼": "鱼",
    "鲈鱼": "鱼", "鳜鱼": "鱼", "多宝鱼": "鱼", "青花鱼": "鱼", "带鱼": "鱼",
    "白灼鲜虾": "虾", "白灼虾": "虾", "炒虾仁": "虾", "毛豆炒虾仁": "虾",
    "蒜蓉粉丝蒸扇贝": "扇贝", "白炒鲜贝": "鲜贝",
    "爆炒蛏子": "蛏子", "葱油茭白蛏子": "蛏子",
    "黄鳝": "黄鳝", "响油鳝丝": "黄鳝", "毛豆烧黄鳝": "黄鳝", "红烧黄鳝": "黄鳝",
    "鳝丝": "黄鳝", "鳝鱼": "黄鳝",
    "小龙虾": "小龙虾", "蒜蓉小龙虾": "小龙虾", "冰醉小龙虾": "小龙虾",
    "六月黄": "蟹", "红烧六月黄": "蟹",
    "炒蛋": "蛋", "蒸蛋": "蛋", "蛋花汤": "蛋", "番茄蛋花汤": "蛋", "紫菜蛋花汤": "蛋",
    "豆腐": "豆腐", "锅塌豆腐": "豆腐", "虾仁蒸豆腐": "豆腐",
    "拍黄瓜": "黄瓜", "蒜蓉炒苋菜": "苋菜", "上汤苋菜": "苋菜",
    "蒜蓉空心菜": "空心菜", "腐乳炒空心菜": "空心菜",
    "油焖茭白": "茭白", "茭白炒肉丝": "茭白",
    "干煸豆角": "豆角", "肉末豇豆": "豇豆",
    "丝瓜炒蛋": "丝瓜", "丝瓜虾仁汤": "丝瓜", "蒜蓉蒸丝瓜": "丝瓜",
    "毛豆烧鸡": "鸡肉", "毛豆烧黄鳝": "黄鳝",
    "葱油蚕豆": "蚕豆", "蚕豆炒蛋": "蚕豆",
    "芦笋炒牛肉": "芦笋",
    "烤蔬菜拼盘": "蔬菜拼盘",
    "豌豆焖饭": "豌豆", "杂粮饭": "杂粮", "白米饭": "大米",
}

# 当季食材列表（6月/盛夏）
SEASONAL_INGREDIENTS = [
    "苋菜", "空心菜", "丝瓜", "豆角", "豇豆", "毛豆", "蚕豆",
    "茄子", "秋葵", "茭白", "南瓜藤", "南瓜尖",
    "六月黄", "黄鳝", "小龙虾", "蛏子",
    "杨梅", "水蜜桃", "西瓜",
]

# 辣味关键词
SPICY_KEYWORDS = [
    "辣", "麻", "藤椒", "花椒", "红油", "辣子", "小炒",
    "麻辣", "香辣", "酸辣", "剁椒", "泡椒", "干锅",
    "辣椒", "辣酱", "豆瓣酱", "老干妈",
]

# 核心技法前缀
COOKING_TECHNIQUES = [
    "红烧", "清蒸", "清炒", "爆炒", "干煸", "油焖", "葱油",
    "蒜蓉", "盐焗", "白灼", "白炒", "酱爆", "葱爆", "糖醋",
    "煎", "炸", "烤", "炖", "焖", "蒸", "焗", "煮", "拌",
]

# 荤料关键词（用于素菜纯度检查）
MEAT_KEYWORDS = [
    "猪", "牛", "羊", "鸡", "鸭", "鹅", "鸽", "鱼", "虾", "蟹",
    "贝", "蛏", "蛤", "螺", "鳝", "鳅", "肉", "蛋", "皮蛋",
    "咸蛋", "腊", "培根", "火腿",
]


def normalize_ingredient(dish_name):
    """从菜名提取主食材（归一化）。"""
    if dish_name in MAIN_INGREDIENT_MAP:
        return MAIN_INGREDIENT_MAP[dish_name]
    for key, ingredient in MAIN_INGREDIENT_MAP.items():
        if key in dish_name:
            return ingredient
    m = re.match(r"^(红烧|爆炒|清炒|干煸|油焖|葱油|蒜蓉|清蒸|盐焗|白灼|白炒|酱爆|葱爆)(.*)", dish_name)
    if m:
        method, main = m.groups()
        for key, ingredient in MAIN_INGREDIENT_MAP.items():
            if key in main:
                return ingredient
        if main:
            return main
    return dish_name


def extract_technique(dish_name):
    """提取菜品核心技法。"""
    for tech in COOKING_TECHNIQUES:
        if dish_name.startswith(tech):
            return tech
    # 单字技法：煎/炸/烤/炖/焖/蒸/焗/煮/拌
    for tech in ["煎", "炸", "烤", "炖", "焖", "蒸", "焗", "煮", "拌"]:
        if dish_name.startswith(tech):
            return tech
    return "未知技法"


def normalized_meal_type(entry):
    return entry.get("meal_type", "lunch")


def load_history_blacklist(meal_type="lunch"):
    """从 history.json 加载 30 天黑名单。"""
    data_dir = os.environ.get("RECIPE_DATA_DIR", "/root/.hermes/profiles/life/data")
    history_file = Path(data_dir) / "history.json"
    if not history_file.exists():
        return {"dish_names": [], "main_ingredients": []}

    today = datetime.now().strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    # 清洗未来日期
    cleaned = [h for h in history if h.get("date", "9999") <= today]
    recent = [
        h for h in cleaned
        if h.get("date", "0") >= thirty_days_ago and normalized_meal_type(h) == meal_type
    ]

    dish_names = set()
    main_ingredients = set()
    for entry in recent:
        for dish in entry.get("dishes", []):
            dish_names.add(dish)
            ingredient = normalize_ingredient(dish)
            main_ingredients.add(ingredient)

    return {"dish_names": sorted(dish_names), "main_ingredients": sorted(main_ingredients)}


# ─── 检查项 ───

def check_structure(plan_label, dishes):
    """结构检查：2大荤+1素/小荤+1汤+1主食。"""
    issues = []
    categories = {"大荤": 0, "素/小荤": 0, "汤": 0, "主食": 0}

    for dish in dishes:
        cat = dish.get("category", "")
        if "大荤" in cat:
            categories["大荤"] += 1
        elif "素" in cat or "小荤" in cat:
            categories["素/小荤"] += 1
        elif "汤" in cat:
            categories["汤"] += 1
        elif "主食" in cat:
            categories["主食"] += 1

    if categories["大荤"] < 2:
        issues.append(f"【{plan_label}】大荤不足 {categories['大荤']}/2")
    if categories["素/小荤"] < 1:
        issues.append(f"【{plan_label}】素/小荤不足 {categories['素/小荤']}/1")
    if categories["汤"] < 1:
        issues.append(f"【{plan_label}】汤不足 {categories['汤']}/1")
    if categories["主食"] < 1:
        issues.append(f"【{plan_label}】主食不足 {categories['主食']}/1")

    return issues


def check_breakfast_structure(plan_label, dishes):
    """早餐结构检查：1主食+1蛋白+1饮品+1果蔬。"""
    issues = []
    categories = {"主食": 0, "蛋白": 0, "饮品": 0, "果蔬": 0}

    for dish in dishes:
        cat = dish.get("category", "")
        if "主食" in cat:
            categories["主食"] += 1
        elif "蛋白" in cat or "鸡蛋" in cat or "肉蛋" in cat:
            categories["蛋白"] += 1
        elif "饮品" in cat or "奶" in cat or "豆浆" in cat or "米糊" in cat:
            categories["饮品"] += 1
        elif "果蔬" in cat or "水果" in cat or "蔬菜" in cat:
            categories["果蔬"] += 1

    for category, count in categories.items():
        if count < 1:
            issues.append(f"【{plan_label}】早餐{category}不足 {count}/1")

    return issues


def check_main_ingredient_clash(plan_label, dishes):
    """同套方案内主食材去重。"""
    issues = []
    seen = {}
    for dish in dishes:
        name = dish.get("name", "")
        if dish.get("category") == "主食":
            continue  # 主食不参与主材去重
        ingredient = normalize_ingredient(name)
        if ingredient in seen:
            issues.append(f"【{plan_label}】主材撞车：{name} 和 {seen[ingredient]} 都以「{ingredient}」为主材")
        else:
            seen[ingredient] = name
    return issues


def check_spicy(plan_label, dishes):
    """辣味拦截。"""
    issues = []
    for dish in dishes:
        name = dish.get("name", "")
        desc = dish.get("description", "") + dish.get("note", "")
        combined = name + desc
        for kw in SPICY_KEYWORDS:
            if kw in combined:
                issues.append(f"【{plan_label}】辣味命中：{name} 含「{kw}」")
                break
    return issues


def check_bitter_melon(plan_label, dishes):
    """苦瓜拦截。"""
    issues = []
    for dish in dishes:
        name = dish.get("name", "")
        desc = dish.get("description", "") + dish.get("note", "")
        if "苦瓜" in name or "苦瓜" in desc:
            issues.append(f"【{plan_label}】苦瓜命中：{name}")
    return issues


def check_vegetarian_purity(plan_label, dishes):
    """素菜纯度：标【素】的菜不能含荤料。"""
    issues = []
    for dish in dishes:
        name = dish.get("name", "")
        cat = dish.get("category", "")
        if "【素】" in cat or cat == "素":
            desc = dish.get("description", "") + dish.get("note", "") + name
            for meat in MEAT_KEYWORDS:
                # 排除"素肉"等特殊情况
                if meat in desc and "素" + meat not in desc:
                    issues.append(f"【{plan_label}】素菜不纯：{name} 标【素】但含荤料「{meat}」")
                    break
    return issues


def check_time(plan_label, dishes):
    """时间检查：单道菜 ≤30分钟（并行前提下），总时间 ≤45分钟。"""
    issues = []
    for dish in dishes:
        time_str = dish.get("time", dish.get("预估时间", ""))
        note = dish.get("note", "")
        combined = str(time_str) + note
        # 提取数字
        times = re.findall(r"(\d+)\s*分钟", combined)
        if times:
            max_time = max(int(t) for t in times)
            if max_time > 30:
                issues.append(f"【{plan_label}】单道菜超时：{dish.get('name')} 标注 {max_time}min > 30min")

    # 总时间检查
    total_match = re.search(r"(\d+)\s*分钟", str(dishes[-1].get("total_time", "")) if dishes else "")
    # 如果方案有 total_time 字段
    for dish in dishes:
        if "总制作时间" in str(dish):
            m = re.search(r"(\d+)", str(dish))
            if m and int(m.group(1)) > 45:
                issues.append(f"【{plan_label}】总时间超时：{m.group(1)}min > 45min")

    return issues


def check_inventory_label(plan_label, dishes):
    """库存标注：每道菜必须有【匹配库存】或【需采购】标注。"""
    issues = []
    for dish in dishes:
        note = dish.get("note", "")
        desc = dish.get("description", "")
        combined = note + desc
        if "【匹配库存" not in combined and "【需采购】" not in combined and "匹配库存" not in combined and "需采购" not in combined:
            issues.append(f"【{plan_label}】缺少库存标注：{dish.get('name')}")
    return issues


def check_seasonal_creative(plan_label, dishes):
    """当季创意：每套至少1份当季菜 + 1份特色菜（2026-06-18 更新）"""
    issues = []
    has_seasonal = False
    has_creative = False

    for dish in dishes:
        name = dish.get("name", "")
        desc = dish.get("description", "") + dish.get("note", "")
        combined = name + desc

        # 当季检查
        for ing in SEASONAL_INGREDIENTS:
            if ing in combined:
                has_seasonal = True
                break

        # 特色/创意检查（2026-06-18 扩展：不仅限关键词，还包括技法/仪式感标志）
        creative_keywords = [
            "网红", "新派", "电饭煲版", "空气炸锅", "仪式感", "改良", "创意",
            "响油", "浇", "激香", "铺底", "粉丝", "蒸", "盐葱", "瑶柱",
            "紫苏", "上汤", "豉汁", "蒜蓉粉丝", "葱油拌",
        ]
        for kw in creative_keywords:
            if kw in combined:
                has_creative = True
                break

    if not has_seasonal:
        issues.append(f"【{plan_label}】缺少当季菜（6月当季食材：{', '.join(SEASONAL_INGREDIENTS[:6])}...）")
    if not has_creative:
        issues.append(f"【{plan_label}】缺少创意菜（需含网红/新派/仪式感/改良等关键词）")

    return issues


def check_30day_blacklist(plan_label, dishes, blacklist, explicit_overrides=None):
    """30天排重：菜名和主材不在黑名单内。"""
    issues = []
    dish_blacklist = set(blacklist.get("dish_names", []))
    ingredient_blacklist = set(blacklist.get("main_ingredients", []))
    override_text = "\n".join(explicit_overrides or [])

    for dish in dishes:
        name = dish.get("name", "")
        cat = dish.get("category", "")

        # 主食不参与菜品排重
        if "主食" in cat:
            continue

        ingredient = normalize_ingredient(name)
        if name in override_text or ingredient in override_text:
            continue

        if name in dish_blacklist:
            issues.append(f"【{plan_label}】30天已做：{name}")

        if ingredient in ingredient_blacklist:
            issues.append(f"【{plan_label}】主材30天已用：{name}（主材「{ingredient}」在黑名单）")

    return issues


def check_technique_dup(plan_label, dishes):
    """同套方案内核心技法去重（大荤之间）。"""
    issues = []
    techniques = {}
    for dish in dishes:
        name = dish.get("name", "")
        cat = dish.get("category", "")
        if "大荤" not in cat:
            continue
        tech = extract_technique(name)
        if tech in techniques:
            issues.append(f"【{plan_label}】技法重复：{name} 和 {techniques[tech]} 都用「{tech}」技法")
        else:
            techniques[tech] = name
    return issues


# ─── 主入口 ───

def review_plan(plan_data, blacklist, meal_type="lunch"):
    """对单套方案执行全部检查。"""
    all_issues = []

    label = plan_data.get("label", "未知方案")
    meal_type = plan_data.get("meal_type", meal_type)
    dishes = plan_data.get("dishes", [])
    explicit_overrides = plan_data.get("explicit_overrides", [])

    if meal_type == "breakfast":
        all_issues.extend(check_breakfast_structure(label, dishes))
    else:
        all_issues.extend(check_structure(label, dishes))
    all_issues.extend(check_main_ingredient_clash(label, dishes))
    all_issues.extend(check_spicy(label, dishes))
    all_issues.extend(check_bitter_melon(label, dishes))
    all_issues.extend(check_vegetarian_purity(label, dishes))
    all_issues.extend(check_time(label, dishes))
    all_issues.extend(check_inventory_label(label, dishes))
    if meal_type != "breakfast":
        all_issues.extend(check_seasonal_creative(label, dishes))
    all_issues.extend(check_30day_blacklist(label, dishes, blacklist, explicit_overrides))
    if meal_type != "breakfast":
        all_issues.extend(check_technique_dup(label, dishes))

    return all_issues


def main():
    parser = argparse.ArgumentParser(description="周末家庭餐饮方案自动审核门")
    parser.add_argument("--input", help="方案 JSON 文件；省略时从 stdin 读取")
    parser.add_argument("--meal-type", choices=["breakfast", "lunch"], default="lunch", help="餐次类型，默认 lunch")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"status": "FAIL", "issues": ["无输入数据"]}, ensure_ascii=False))
            sys.exit(1)
        input_data = json.loads(raw)

    # 加载黑名单
    blacklist = load_history_blacklist(args.meal_type)

    # 逐套检查
    all_issues = []
    plan_results = {}

    for key, plan in input_data.items():
        # 兼容两种格式：{label, dishes} 和裸数组
        if isinstance(plan, list):
            plan_data = {"label": key, "dishes": plan}
        else:
            plan_data = plan

        label = plan_data.get("label", key)
        meal_type = plan_data.get("meal_type", args.meal_type)
        issues = review_plan(plan_data, blacklist, meal_type)

        plan_results[label] = "PASS" if not issues else "FAIL"
        all_issues.extend(issues)

    # 输出
    status = "PASS" if not all_issues else "FAIL"
    result = {
        "status": status,
        "plans": plan_results,
        "issues": all_issues,
        "issue_count": len(all_issues),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()

# ─── 新增：跨方案排重检查 ──
def check_cross_plan_dedup(plans):
    """跨方案排重：3套方案的主材不应高度重复。"""
    issues = []
    all_main_ingredients = []
    for plan_label, plan_data in plans.items():
        for dish in plan_data.get("dishes", []):
            note = dish.get("note", "") + dish.get("description", "")
            for main_ing, mapped in MAIN_INGREDIENT_MAP.items():
                if main_ing in dish.get("name", "") or main_ing in note:
                    all_main_ingredients.append((plan_label, mapped))
                    break
    
    # 统计每个主材出现的方案数
    from collections import Counter
    plan_ingredients = {}
    for plan_label, ing in all_main_ingredients:
        if plan_label not in plan_ingredients:
            plan_ingredients[plan_label] = set()
        plan_ingredients[plan_label].add(ing)
    
    # 找出所有方案都用的主材
    if len(plan_ingredients) >= 2:
        common = set.intersection(*plan_ingredients.values())
        if common:
            issues.append(f"【跨方案排重】所有方案都使用主材：{', '.join(common)} — 请确保各方案有差异化主材选择")
    
    return issues
