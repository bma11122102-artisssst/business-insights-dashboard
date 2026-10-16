from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path('assets/screenshots');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    page.goto('http://127.0.0.1:8501',wait_until='networkidle')
    page.get_by_role('heading',name='Overview',exact=True).wait_for(timeout=60000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(out/'overview.png'),full_page=True)
    page.get_by_role('link',name='Recommendations',exact=True).click()
    page.get_by_role('heading',name='Your step-by-step checklist').wait_for(timeout=60000)
    page.wait_for_timeout(1000)
    page.screenshot(path=str(out/'recommendations.png'),full_page=True)
    page.get_by_role('link',name='Model checks',exact=True).click()
    page.get_by_role('tab',name='Marketing',exact=True).click(timeout=60000)
    page.wait_for_timeout(1000)
    page.screenshot(path=str(out/'model-checks.png'),full_page=True)
    print('Captured actual Streamlit pages.')
    browser.close()
