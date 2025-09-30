from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import nest_asyncio
import streamlit as st
import psutil, signal
import shutil
import sys

# ReportLab Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Other Imports
from collections import defaultdict
from datetime import datetime
import os
import platform
import re
import requests
import subprocess

# Fix for Windows + Playwright async subprocesses
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def setup_browser():
    playwright = await async_playwright().start()

    browser = await playwright.firefox.launch(
        headless=True,
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        java_script_enabled=True,
        device_scale_factor=1,
        is_mobile=False,
        has_touch=False,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
    )

    page = await context.new_page()

    # --- Hide headless indicators for stealth ---
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = { runtime: {} };
    """)

    # --- goto_full helper ---
    async def goto_full(url: str, wait_for: str = None, timeout: int = 15000):
        # Ensure full URL
        if url.startswith("/"):
            url = "https://playtennis.usta.com" + url
        elif not url.startswith("http"):
            url = "https://" + url.lstrip("/")

        print(f"[goto_full] Navigating to: {url}")
        try:
            # Wait for page navigation
            await asyncio.wait_for(page.goto(url), timeout=timeout / 1000)
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)

            # 🔽 Scroll repeatedly until bottom stops changing
            last_height = 0
            scroll_attempts = 0
            while scroll_attempts < 30:  # Max 30 scrolls to prevent infinite loops
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await asyncio.sleep(1.2)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1

            # Extra wait for JS-rendered content (player names) to appear
            await asyncio.sleep(2)

        except (asyncio.TimeoutError, PlaywrightTimeoutError) as e:
            print(f"[goto_full] Timeout or navigation error for {url}: {e}")
            try:
                await page.close()
            except:
                pass
            await context.close()
            await browser.close()
            await playwright.stop()
            raise

    page.goto_full = goto_full

    return playwright, browser, context, page

async def age_groups_level(tournament_link):
    playwright, browser, context, page = await setup_browser()
    await page.goto(tournament_link.lower())

    try:
        await page.wait_for_selector("._H6_1iwqn_128", timeout=10000)
        age_groups = await page.locator("._H6_1iwqn_128").all_inner_texts()

        level_xpath = "/html/body/div[4]/div/div/div[2]/div[3]/div[1]/div[2]/div[2]/div/div/div[1]/div/div/div[1]/h6"
        await page.wait_for_selector(f"xpath={level_xpath}", timeout=10000)
        level = await page.locator(f"xpath={level_xpath}").inner_text()

        continue_age = level in ["Level 7", "Level 6"]
        age_groups_final = age_groups[1:]

        return [level, continue_age, age_groups_final]
    except:
        return []
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()


def parse_wtn(wtn_str):
    try:
        return float(wtn_str)
    except ValueError:
        return 40.0


def sort_key(k):
    try:
        return float(k)
    except ValueError:
        return float('inf')


async def scrape_recruiting(name, location, page):
    player_rating = "Unknown"
    player_year = "Unknown"
    player_utr = "0.xx"
    retries = 0
    max_retries = 5   # prevent infinite loop

    player_grades = ["Graduate","Senior","Junior","Sophomore","Freshman",
                     "8th Grader","7th Grader","6th Grader"]

    player_rating_xpath = "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img"
    player_year_xpath = "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[3]/td[2]/div[3]"

    while (player_rating == "Unknown" or player_year == "Unknown" or player_utr == "0.xx") and retries < max_retries:
        retries += 1
        await page.goto("https://www.tennisrecruiting.net/player.asp")

        await page.fill("input[name=f_playername]", name)
        await page.keyboard.press("Enter")

        try:
            await page.wait_for_selector(f"xpath={player_rating_xpath}", timeout=10000)
            player_rating = page.locator(f"xpath={player_rating_xpath}")
        except:
            player_rating = "Unknown"

        try:
            await page.wait_for_selector("text=.xx", timeout=5000)
            player_utr = await page.locator("text=.xx").nth(0).inner_text()
        except:
            player_utr = "0.xx"

        try:
            await page.wait_for_selector(f"xpath={player_year_xpath}", timeout=5000)
            player_year = await page.locator(f"xpath={player_year_xpath}").inner_text()
            for grade in player_grades:
                if grade in player_year:
                    player_year = grade
                    if "Provisional" in player_year:
                        player_year = player_year + "?"
                    break
        except:
            player_year = "Unknown"

    # if rating never loads, return placeholder image
    if player_rating == "Unknown":
        return ["https://www.tennisrecruiting.net/img/record.gif", player_utr, player_year]

    return [await player_rating.get_attribute("src"), player_utr, player_year]


async def scrape_usta(player_link, age_group, max_retries: int = 5):
    retries = 0
    while retries < max_retries:
        retries += 1
        playwright, browser, context, page = await setup_browser()
        try:
            await page.goto(player_link + "&tab=about")

            try:
                player_name_selector = "span.readonly-text__text > h3"
                await page.wait_for_selector(player_name_selector, timeout=10000)
                locator = page.locator(player_name_selector)
                player_name = await locator.text_content()
                player_name = player_name.strip()
            except:
                player_name = "Unknown Player"

            try:
                await page.wait_for_selector(".readonly-text__content", timeout=10000)
                player_location = await page.locator(".readonly-text__content").nth(1).inner_text()
                player_location = player_location.split('|')[1].split('Section:')[0].strip("\n")
            except:
                player_location = "Unknown"

            try:
                await page.wait_for_selector(".readonly-text__content", timeout=10000)
                player_district = await page.locator(".readonly-text__content").nth(1).inner_text()
                player_district = player_district.split("|")[2].split(": ")[1]
            except:
                player_district = "Unknown"

            try:
                player_wtn_xpath = "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[2]/div/div/div[2]/div/div[3]/div/div/div/div[2]/div/form/div[3]/div/div/div/div[1]/div/div[2]/div[1]/div/p"
                await page.wait_for_selector(f"xpath={player_wtn_xpath}", timeout=10000)
                player_wtn = await page.locator(f"xpath={player_wtn_xpath}").inner_text()
            except:
                player_wtn = "40.00"

            player_points = "0"
            player_rank = "20000"

            try:
                await page.goto(player_link + "&tab=rankings")
                await page.wait_for_selector(".v-grid-cell__content", timeout=10000)
                player_ranking_info = await page.locator(".v-grid-cell__content").all_inner_texts()  
                player_data = []
                i = 0
                while i < len(player_ranking_info):
                    player_data.append([
                        player_ranking_info[i],
                        player_ranking_info[i + 1],
                        player_ranking_info[i + 2],
                        player_ranking_info[i + 3],
                        player_ranking_info[i + 4]
                    ])
                    i += 5
                for player in player_data:
                    if (age_group.split(" ")[1] + " National Standings List") in player[0]:
                        player_points = player[1]
                        player_rank = player[2]
            except:
                player_points = "0"
                player_rank = "20,000"

            try:
                recruiting_rating = await scrape_recruiting(player_name, player_location, page)
            except:
                recruiting_rating = ["https://www.tennisrecruiting.net/img/record.gif","0.xx","Unknown"]

            if "0star" in recruiting_rating[0]:
                recruiting_rating[0] = "0 Star"
            elif "1star" in recruiting_rating[0]:
                recruiting_rating[0] = "1 Star"
            elif "2star" in recruiting_rating[0]:
                recruiting_rating[0] = "2 Star"
            elif "3star" in recruiting_rating[0]:
                recruiting_rating[0] = "3 Star"
            elif "4star" in recruiting_rating[0]:
                recruiting_rating[0] = "4 Star"
            elif "5star" in recruiting_rating[0]:
                recruiting_rating[0] = "5 Star"
            elif "6star" in recruiting_rating[0]:
                recruiting_rating[0] = "Blue Chip"
            else:
                recruiting_rating[0] = "Unknown"

            # ✅ Close resources
            await context.close()
            await browser.close()
            await playwright.stop()

            return [
                player_name, player_location, player_district,
                player_wtn, player_points, player_rank,
                recruiting_rating[0], recruiting_rating[1], recruiting_rating[2]
            ]

        except Exception as e:
            try:
                await context.close()
                await browser.close()
                await playwright.stop()
            except:
                pass
            if retries >= max_retries:
                return [
                    "Unknown", "Unknown", "Unknown", "40.00", "0", "20,000",
                    "Unknown", "0.xx", "Unknown"
                ]

async def scrape_draw_size(link, selected_age_group):
    playwright, browser, context, page = await setup_browser()
    await page.goto(link)

    tournament_groups_final = []
    await page.wait_for_selector("._H6_1iwqn_128", timeout=10000)
    tournament_age_groups = await page.locator("._H6_1iwqn_128").all_inner_texts()

    await page.wait_for_selector("._link_19t7t_285", timeout=10000)
    links = await page.query_selector_all("._link_19t7t_285")

    for age_group in tournament_age_groups:
        tournament_groups_final.append(age_group)

    tournament_link_final = await links[tournament_groups_final.index(selected_age_group) - 1].get_attribute("href")
    if tournament_link_final and not tournament_link_final.startswith("http"):
        tournament_link_final = "https://playtennis.usta.com" + tournament_link_final
    await page.goto(tournament_link_final)

    await page.wait_for_selector("._bodyXSmall_1iwqn_137", timeout=10000)
    tournament_draw_temp = await page.locator("._bodyXSmall_1iwqn_137").all_inner_texts()

    try:
        tournament_draw_size = int(tournament_draw_temp[1])
    except:
        tournament_draw_size = 100000

    sort_type = tournament_draw_temp[5]
    if "ranking" in sort_type.lower():
        sort_type = 1
    elif "wtn" in sort_type.lower():
        sort_type = 2
    elif "manual" in sort_type.lower():
        sort_type = 1
    elif ("n/a" == sort_type.lower()) or ("first" in sort_type.lower()):
        print("1.Points\n2.WTN")
        sort_type = str(input("Choose a selection type: "))
        if sort_type == "1":
            sort_type = 1
        elif sort_type == "2":
            sort_type = 2

    await context.close()
    await browser.close()
    await playwright.stop()

    return [tournament_draw_size, sort_type]


async def scrape_player(player_link, age_group):
    try:
        player_info = await scrape_usta(player_link, age_group)
        return {
            "Name": player_info[0],
            "Profile": player_link,
            "Location": player_info[1],
            "District": player_info[2],
            "WTN": player_info[3],
            "Points": player_info[4],
            "Ranking": player_info[5],
            "Recruiting": player_info[6],
            "Class": player_info[8],
            "UTR": player_info[7],
        }
    except:
        return {
            "Name": "Unknown",
            "Profile": "",
            "Location": "Unknown",
            "District": "Unknown",
            "WTN": "40.00",
            "Points": "0",
            "Ranking": "20,000",
            "Recruiting": "Unknown",
            "Class": "Unknown",
            "UTR": "0.xx",
        }


def sort_players(player_data, tournament_level, sort):
    sort_type = ""
    if "Level 7" in tournament_level:
        if sort == 1:
            sort_type = "points"
            player_data = sorted(player_data,key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0)
        elif sort == 2:
            sort_type = "wtn"
            player_data = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]), reverse=True)
    elif "Level 6" in tournament_level:
        if sort == 1:
            sort_type = "points"
            player_data = sorted(player_data,key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0, reverse=True)
        elif sort == 2:
            sort_type = "wtn"
            player_data = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]))
    else:
        sort_type = "mixed"
        player_data = sorted(player_data,key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0, reverse=True)

    return [player_data, sort_type]


async def scrape_tournament_data(tournament_url, age_group, draw_size, sort, tournament_level):
    playwright, browser, context, page = await setup_browser()
    tournament_url = tournament_url.lower()
    await page.goto(tournament_url)
    tournament_name = await page.locator("//*[@id='tournaments']/div/div/div/div[1]/div/div[1]/h1").inner_text()

    await page.goto(tournament_url.replace("overview", "players"))
    await page.wait_for_selector("._alignLeft_1nqit_268", timeout=10000)
    players_list = await page.query_selector_all("._alignLeft_1nqit_268")

    player_links = []
    for player_row in players_list:
        text = await player_row.inner_text()
        if age_group in text:
            link = await players_list[players_list.index(player_row) - 1].query_selector("a")
            href = await link.get_attribute('href')
            player_links.append(href)
    
    if not player_links:
        print("No player links found. Exiting.")
        return

    print("Found", len(player_links), "players. Starting information search...")

    # Helper to run tasks in batches of 10
    async def gather_in_batches(tasks, batch_size=25):
        results = []
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
        return results

    # Create tasks
    tasks = [scrape_player(link, age_group) for link in player_links]

    # Run them in batches of 10
    player_data = await gather_in_batches(tasks, batch_size=25)

    # Filter out failed scrapes
    player_data = [data for data in player_data if data is not None]

    # Sort players
    player_data = sort_players(player_data, tournament_level, sort)
    sort_type = player_data[1]
    player_data = player_data[0]

    print("Completed. Analyzing data...")

    # Close browser + playwright
    await context.close()
    await browser.close()
    await playwright.stop()

    player_names = []
    player_profiles = []
    player_locations = []
    player_districts = []
    player_seeds = []
    player_wtns = []
    player_points = []
    player_rankings = []
    player_recruiting = []
    player_year = []
    player_utr = []
    row_colors = []
    counts = 0

    for player in player_data:
        if player and isinstance(player, dict):
            try:
                player["Points"] = f'{int(player["Points"]):,}'
            except:
                player["Points"] = "0"

            try:
                player["Ranking"] = f'{int(player["Ranking"]):,}'
            except:
                player["Ranking"] = "20,000"

            player_names.append(player.get("Name", "Unknown"))
            player_profiles.append(player.get("Profile", "Unknown"))
            player_locations.append(player.get("Location", "Unknown"))
            player_districts.append(player.get("District", "Unknown"))
            player_wtns.append(player.get("WTN", "N/A"))
            player_points.append(player["Points"])
            player_rankings.append(player["Ranking"])
            player_recruiting.append(player["Recruiting"])
            player_year.append(player["Class"])
            player_utr.append(player["UTR"])
            if int(counts) > int(draw_size) - 1:
                row_colors.append('lightcoral')
            else:
                row_colors.append('white')
            counts += 1

    seeds_temp = []
    seeds_final = []
    num_seeds = 0
    total_players = min(int(draw_size),len(player_links))

    while pow(2,num_seeds) <= total_players:
        num_seeds += 1
    num_seeds = pow(2,num_seeds - 2)
    
    for i in player_wtns[:total_players]:
        seeds_temp.append(i)

    seeds_temp.sort()
    seeds_temp = seeds_temp[0:num_seeds]

    for i in player_wtns[:total_players]:
        if i in seeds_temp:
            seeds_final.append(seeds_temp.index(i) + 1)
        else:
            seeds_final.append("-")

    while len(seeds_final) < len(player_names):
        seeds_final.append("-")

    today_str = datetime.today().strftime("%Y-%m-%d")
    safe_name = "".join(c if c.isalnum() or c in " -" else "-" for c in tournament_name)
    filename = f"{safe_name}_{today_str}_{sort_type}.pdf"
    pdf_dir = "C:/Users/shaur/Downloads"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter))

    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"<b>{tournament_name}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    table_data = [["No", "Name", "Location", "District", "Seed", "WTN", "Points", "Ranking", "Recruiting", "Grade", "UTR"]]

    link_style = ParagraphStyle(
        'Link',
        parent=styles['Normal'],
        textColor=colors.blue,
        wordWrap='LTR',   # disables breaking for CJK and forces LTR text
    )

    for i in range(len(player_names)):
        # Make player name clickable if link exists
        if i < len(player_profiles) and player_profiles[i]:
            name_with_link = Paragraph(
                f'<a href="{player_profiles[i]}"><u>{player_names[i]}</u></a>',
                link_style
            )
        else:
            name_with_link = Paragraph(player_names[i], styles['Normal'])

        row = [
            str(i + 1),
            name_with_link,
            player_locations[i],
            player_districts[i],
            str(seeds_final[i]),
            player_wtns[i],
            player_points[i],
            player_rankings[i],
            player_recruiting[i],
            player_year[i],
            player_utr[i]
        ]
        table_data.append(row)

    # Example column widths (adjust as needed)
    col_widths = [20, 110, 110, 125, 40, 40, 40, 40, 50, 50, 30]  # first value = "No" column width
    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ])

    for idx in range(1, len(table_data)):
        if idx > int(draw_size):
            table_style.add('BACKGROUND', (0, idx), (-1, idx), colors.lightcoral)

    table.setStyle(table_style)
    utr_counter = defaultdict(int)
    utr_placeholders = set()

    for each_utr in player_utr:
        each_utr = each_utr.strip()

        if each_utr == "?":
            key = "? UTR"
        elif re.match(r"^\d+\.xx$", each_utr):
            key = each_utr.split('.')[0] + ".0"
            utr_placeholders.add(key)
        else:
            key = each_utr

        utr_counter[key] += 1

    utrs_sorted = sorted(utr_counter.items(), key=lambda x: sort_key(x[0]))
    utr_summary_lines = []
    total = len(player_utr)

    for utr_val, count in utrs_sorted:
        display_val = f"{utr_val.split('.')[0]}.xx" if utr_val in utr_placeholders else utr_val
        pct = round(100 * count / total, 2)

        if count == 1:
            utr_summary_text = f" - There is <b>{count}</b> UTR rated <b>{display_val}</b> in this tournament (<b>{pct}%</b>)."
            utr_summary_lines.append(utr_summary_text)
        else:
            utr_summary_text = f" - There are <b>{count}</b> UTRs rated <b>{display_val}</b> in this tournament (<b>{pct}%</b>)."
            utr_summary_lines.append(utr_summary_text)

    utr_summary_text = "<br/>".join(utr_summary_lines)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(utr_summary_text, styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey, spaceBefore=12, spaceAfter=12, dash=3))
    elements.append(table)
    doc.build(elements)
    print(f"PDF saved to: {pdf_path}")
    return pdf_path
        
nest_asyncio.apply()  # allow nested event loops in Streamlit

# Helper to run async functions
def run_async(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

def main():
    st.title("USTA Tennis Tournament Analyzer")

    # Input from user
    tournament_link = st.text_input("Enter the tournament link:")

    # Initialize session state
    if "age_groups_final" not in st.session_state:
        st.session_state.age_groups_final = []
    if "age_options" not in st.session_state:
        st.session_state.age_options = None

    # Button to fetch age groups
    if st.button("Find age groups:"):
        age_options = run_async(age_groups_level(tournament_link))
        st.session_state.age_groups_final = age_options[2]  # store age groups
        st.session_state.age_options = age_options  # store full options

    # Show dropdown if we have age groups
    if st.session_state.age_groups_final:
        selected_age_group = st.selectbox(
            "Select an age group:", st.session_state.age_groups_final
        )
        st.write("You selected:", selected_age_group)

        # Single button to analyze tournament
        if st.button("Analyze tournament"):
            sort = run_async(scrape_draw_size(
                tournament_link.replace("overview", "events"), selected_age_group
            ))

            pdf_path = run_async(scrape_tournament_data(
                tournament_link.lower(),
                selected_age_group,
                sort[0],
                sort[1],
                st.session_state.age_options[0]  # use session state
            ))

            # Make PDF downloadable in Streamlit
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Download Tournament PDF",
                    data=f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
    finally:
        # ✅ Force close leftover Chrome/Chromium processes
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] and ("chrome" in proc.info['name'].lower() or "chromium" in proc.info['name'].lower()):
                try:
                    proc.send_signal(signal.SIGKILL)
                except Exception:
                    pass
