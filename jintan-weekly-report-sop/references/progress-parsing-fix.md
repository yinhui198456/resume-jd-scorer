# 进度解析补丁：处理含 `%` 符号的进度值

## 问题
在线文档中进度列可能为 `"40%"`、`"60%"` 等字符串，引擎默认 `float(progress)` 会返回 0.0。

## 补丁位置
`scripts/report_engine_v9.py` 中 3 处 `float(progress)` 调用需统一修改。

### 位置 1：协调事务识别（~L327）
```python
# Before
prog_val = float(progress) if progress else 0

# After
if progress:
    p_str = progress.replace('%', '').strip()
    prog_val = float(p_str)
    if '%' in progress:
        prog_val /= 100.0
else:
    prog_val = 0
```

### 位置 2：本周任务进度展示（~L272）
```python
# Before
v = float(prog)

# After
p_str = prog.replace('%', '').strip()
v = float(p_str)
if '%' in prog:
    v /= 100.0
```

### 位置 3：下周任务行动后缀（~L290）
```python
# Before
pv = float(prog)

# After
pv_str = prog.replace('%', '').strip()
pv = float(pv_str)
if '%' in prog:
    pv /= 100.0
```

## 验证
补丁后 `"40%"` → `0.4` → 显示为 `40%`，`"0.6"` → `0.6` → 显示为 `60%`。
