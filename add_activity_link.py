import os

pages_dir = "frontend/pages"
pages = [
    "dashboard.html", "analytics.html", "dishes.html", "customers.html",
    "finance.html", "foodcost.html", "integrations.html", "insights.html",
    "notifications.html", "reports.html", "settings.html", "team.html",
    "kitchens.html", "upload.html"
]

audit_link = '''<a href="activity.html" class="kiq-nav-link"><i class="fa-solid fa-clock-rotate-left"></i><span>Activity</span></a>'''

updated = 0
for fname in pages:
    path = os.path.join(pages_dir, fname)
    if not os.path.exists(path):
        continue

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if 'href="activity.html"' in content:
        continue

    # Add before settings.html link
    if '<a href="settings.html"' in content:
        # Find the exact line
        import re
        pattern = re.compile(r'(\s+)(<a href="settings\.html"[^>]*>.*?</a>)', re.DOTALL)
        match = pattern.search(content)
        if match:
            indent = match.group(1)
            content = content[:match.start()] + indent + audit_link + "\n" + match.group(0) + content[match.end():]
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            print(f"  ✅ {fname}")
            updated += 1
