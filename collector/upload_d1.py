import json, subprocess, os
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
data_dir = "/Users/twinssn/Projects/dailypain/data"
cls_path = f"{data_dir}/{today}-classified.json"

if not os.path.exists(cls_path):
    print(f"파일 없음: {cls_path}")
    exit(1)

with open(cls_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"총 {len(data)}개 중 상위 50개 업로드\n")

success = 0
for item in data[:50]:
    # SQL 인젝션 방지: 작은따옴표 이스케이프
    def esc(s):
        return str(s).replace("'", "''")[:200] if s else ""

    sql = (
        f"INSERT INTO pain_points (date, source, source_url, keyword, title, description, "
        f"category, pain_summary, pain_score, solution_hint, is_actionable, collected_at, classified_at) "
        f"VALUES ('{today}', 'naver_kin', '{esc(item.get('link',''))}', '{esc(item.get('keyword',''))}', "
        f"'{esc(item.get('title',''))}', '{esc(item.get('description',''))}', "
        f"'{esc(item.get('category',''))}', '{esc(item.get('pain_summary',''))}', "
        f"{item.get('pain_score', 0)}, '{esc(item.get('solution_hint',''))}', "
        f"1, '{item.get('collected_at','')}', '{datetime.now().isoformat()}');"
    )

    result = subprocess.run(
        ["npx", "wrangler", "d1", "execute", "dailypain-db", "--remote", f"--command={sql}"],
        cwd="/Users/twinssn/Projects/dailypain/workers",
        capture_output=True, text=True
    )

    if result.returncode == 0:
        success += 1
        if success % 10 == 0:
            print(f"  {success}개 완료...")
    else:
        print(f"  [오류] {result.stderr[:100]}")

print(f"\n업로드 완료: {success}/50개")
print(f"사이트 확인: https://dailypain.hugh79757.workers.dev")
