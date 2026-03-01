import json, os
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
data_dir = "/Users/twinssn/Projects/dailypain/data"
cls_path = f"{data_dir}/{today}-classified.json"

with open(cls_path, encoding="utf-8") as f:
    data = json.load(f)

def esc(s):
    return str(s).replace("'", "''")[:200] if s else ""

lines = []
for item in data[:50]:
    sql = (
        f"INSERT OR IGNORE INTO pain_points (date, source, source_url, keyword, title, description, "
        f"category, pain_summary, pain_score, solution_hint, is_actionable, collected_at, classified_at) "
        f"VALUES ('{today}', 'naver_kin', '{esc(item.get('link',''))}', '{esc(item.get('keyword',''))}', "
        f"'{esc(item.get('title',''))}', '{esc(item.get('description',''))}', "
        f"'{esc(item.get('category',''))}', '{esc(item.get('pain_summary',''))}', "
        f"{item.get('pain_score', 0)}, '{esc(item.get('solution_hint',''))}', "
        f"1, '{item.get('collected_at','')}', '{datetime.now().isoformat()}');"
    )
    lines.append(sql)

sql_path = f"{data_dir}/{today}-upload.sql"
with open(sql_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"SQL 파일 생성: {sql_path}")
print(f"총 {len(lines)}개 INSERT문")
