import json
import os
import time
import platform
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm


class FlashScoreScraper:
    def __init__(self, headless=True):
        """Initializes Flashscore scraper"""
        self.base_url = "https://www.flashscore.com"
        self.driver = self.setup_driver(headless)
        self.results = []

    def scrape_from_url(self, url):
        # Scrape ID from URL
        import re

        match_id = re.search(r"mid=([a-zA-Z0-9]+)", url)

        if match_id:
            match_id = match_id.group(1)
        else:
            try:
                match_id = url.split("/match/")[1].split("/")[0]
            except:
                print("Process went wrong during url scraping!")
                return None

        print(f"Found ID match: {match_id}")

        self.accept_cookies()
        result = self.scrape_match(match_id)
        if result:
            self.results = [result]
            return result
        return None

    def setup_driver(self, headless=True):
        """Configures the Chrome WebDriver with anit-bot measures"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Anti-bot detection flags
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Detect OS and use appropriate chromedriver
        system_os = platform.system()

        try:
            if system_os == "Windows":
                # Windows uses chromedriver.exe
                service = Service("./chromedriver.exe")
            else:
                # Linux/Mac uses chromedriver
                service = Service("./chromedriver")

            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"Using chromedriver local for {system_os}")
        except Exception as e:
            # Fallback: Use webdriver-manager to download the correct version
            print("Local chromedriver failed, downloading compatible version...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

        # Final anti-bot execution script
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        return driver

    def accept_cookies(self):
        """Accepts site cookies"""
        try:
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_btn.click()
            time.sleep(1)
        except:
            pass

    def get_match_basic_info(self, match_id):
        """Extracts basic match info and team slags"""
        url = f"{self.base_url}/match/{match_id}/#/match-summary/match-summary"
        self.driver.get(url)

        data = {"Id": match_id}

        try:
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_all_elements_located(
                    (By.CSS_SELECTOR, 'span[data-testid="wcl-scores-overline-03"]')
                )
            )

            # Pass the loaded HTML code to BeautifulSoup for fast scanning
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # 1. League and round extraction
            overlines = soup.select('span[data-testid="wcl-scores-overline-03"]')
            if len(overlines) >= 3:
                country = overlines[1].text.strip()
                division_round = overlines[2].text.strip()
                league_round = f"{country} - {division_round}"
                parts = league_round.split(" - ")
                if len(parts) >= 3:
                    data["League"] = " - ".join(parts[:2])
                    data["Round"] = parts[2]
                else:
                    data["League"] = league_round
                    data["Round"] = "-"

            # 2. Date and time extraction
            date_time_elem = soup.select_one("div.duelParticipant__startTime")
            if date_time_elem:
                date_time = date_time_elem.text.strip().split(" ")
                data["Date"] = date_time[0].replace(".", "/")
                data["Time"] = date_time[1]

            # 3. Team names extraction
            home_elem = soup.select_one(
                "div.duelParticipant__home div.participant__participantName"
            )
            away_elem = soup.select_one(
                "div.duelParticipant__away div.participant__participantName"
            )
            if home_elem:
                data["Home"] = home_elem.text.strip()
            if away_elem:
                data["Away"] = away_elem.text.strip()

            # 4. Team slugs extraction
            home_link = soup.select_one(
                "div.duelParticipant__home a.participant__participantLink--team"
            )
            away_link = soup.select_one(
                "div.duelParticipant__away a.participant__participantLink--team"
            )

            if home_link and "href" in home_link.attrs:
                home_href = home_link["href"].strip("/")
                segments = home_href.split("/")
                if len(segments) >= 2:
                    home_slug = segments[-2] + "-" + segments[-1]
                    data["Home_Slug"] = home_slug

            if away_link and "href" in away_link.attrs:
                away_href = away_link["href"].strip("/")
                segments = away_href.split("/")
                if len(segments) >= 2:
                    away_slug = segments[-2] + "-" + segments[-1]
                    data["Away_Slug"] = away_slug

            # 5. Score extraction
            score_elem = soup.select_one(
                "div.duelParticipant__score div.detailScore__wrapper"
            )
            if score_elem:
                scores = score_elem.select("span")
                if len(scores) >= 3:  # [Home, "-", Away]
                    try:
                        data["Home_Score"] = int(scores[0].text.strip())
                        data["Away_Score"] = int(scores[2].text.strip())
                    except ValueError:
                        pass

        except Exception as e:
            print(f"Error extracting bacic info: {e}")

        return data

    def extract_goals_and_minutes(self, match_id, data):
        """
        Extracts goal minutes
        Returns lists of goal minutes for home and away teams
        """
        # Only extract if match was played
        if "Home_Score" not in data or "Away_Score" not in data:
            return data

        url = f"{self.base_url}/match/{match_id}/#/match-summary/match-summary"
        self.driver.get(url)

        try:
            # Wait for the match events timeline to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.smv__participantRow")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            min_goals_home = []
            min_goals_away = []

            # Search for all goal event rows
            home_rows = soup.select("div.smv__participantRow.smv__homeParticipant")
            away_rows = soup.select("div.smv__participantRow.smv__awayParticipant")

            # Process goals for the HOME team
            for row in home_rows:
                # Check if there is a soccer ball or a score change indicator
                goal_icon = row.select_one('svg[data-testid="wcl-icon-soccer"]')
                goal_score = row.select_one("div.smv__incidentHomeScore")

                if goal_icon or goal_score:
                    time_box = row.select_one("div.smv__timeBox")
                    if time_box:
                        time_text = time_box.text.strip()
                        # Remove the minute mark "'" and handle added time (e.g "45+2" -> 45.02)
                        try:
                            if "+" in time_text:
                                parts = time_text.replace("'", "").split("+")
                                minute = float(parts[0]) + float(parts[1] / 100)
                            else:
                                minute = float(time_text.replace("'", ""))
                            min_goals_home.append(minute)
                        except ValueError:
                            pass

            # Process goals for the AWAY team
            for row in away_rows:
                goal_icon = row.select_one('svg[data-testid="wcl-icon-soccer"]')
                goal_score = row.select_one("div.smv__incidentAwayScore")

                if goal_icon or goal_score:
                    time_box = row.select_one("div.smv__timeBox")
                    if time_box:
                        time_text = time_box.text.strip()
                        # do the same
                        try:
                            if "+" in time_text:
                                parts = time_text.replace("'", "").split("+")
                                minute = float(parts[0]) + float(parts[1] / 100)
                            else:
                                minute = float(time_text.replace("'", ""))
                            min_goals_away.append(minute)
                        except ValueError:
                            pass

            # sort the minutes chronologically
            min_goals_home.sort()
            min_goals_away.sort()

            data["Min_Goals_Home"] = min_goals_home
            data["Min_Goals_Away"] = min_goals_away

        except Exception as e:
            print(f"Error extracting goals: {e}")
            data["Min_Goals_Home"] = []
            data["Min_Goals_Away"] = []

        return data

    def extract_odds_1x2_ft(self, match_id, data):
        """Extracts 1X2 (Home/Draw/Away) Full Time odds from all available bookmakers"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/1x2-odds/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            # WAit for the odds table to load
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.ui-table.oddsCell__odds")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.select_one("div.ui-table.oddsCell__odds")

            if not table:
                return data

            rows = table.select("div.ui-table__row")
            odds_data = []

            # Loop throug each row which represents diffrent bookmaker
            for row in rows:
                # 1. Exctarct bookmaker name from the image title/alt text
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()

                # 2. Extracts the odds values
                odds_cells = row.select("a.oddsCell__odd")
                if len(odds_cells) < 3:
                    continue

                try:
                    odd_1 = None
                    odd_x = None
                    odd_2 = None

                    for i, cell in enumerate(odds_cells[:3]):
                        # Skip cancelled odds
                        if cell.select("span.oddsCell__lineThrough"):
                            continue

                        odd_span = cell.select_one("span")
                        if odd_span:
                            odd_text = odd_span.text.strip()

                            # Conver ro standart float
                            odd_value = float(odd_text.replace(",", "."))

                            analytics = cell.get("data-analytics-element", "")
                            if "CELL_1" in analytics or i == 0:
                                odd_1 = odd_value
                            elif "CELL_2" in analytics or i == 1:
                                odd_x = odd_value
                            elif "CELL_3" in analytics or i == 2:
                                odd_2 = odd_value

                    # If valid odds were found append them
                    if odd_1 or odd_x or odd_2:
                        odds_data.append(
                            {
                                "Bookmaker": bookmaker,
                                "Odd_1": odd_1,
                                "Odd_X": odd_x,
                                "Odd_2": odd_2,
                            }
                        )
                except Exception:
                    continue

            # Store the list of all bookmakers odds in dict
            data["Odds_1X2_FT"] = odds_data

            # 3. Extract the "Best Odds" - highlighted
            for row in rows:
                odds_cells = row.select("a.oddsCell__odd.oddsCell__highlight")
                for cell in odds_cells:
                    if cell.select("span.oddsCell__lineThrough"):
                        continue

                    odd_span = cell.select_one("span")
                    if odd_span:
                        odd_value = float(odd_span.text.strip().replace(",", "."))
                        analytics = cell.get("data-analytics-element", "")

                        if "CELL_1" in analytics:
                            data["Best_Odd_1_FT"] = odd_value
                        elif "CELL_2" in analytics:
                            data["Best_Odd_X_FT"] = odd_value
                        elif "CELL_3" in analytics:
                            data["Best_Odd_2_FT"] = odd_value

        except Exception as e:
            print(f"Error extracting Best Odds FT: {e}")

        return data

    def extract_odds_ou_ft(self, match_id, data):
        """Extracts Over/Under Full Time odds for all available lines"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/over-under/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            # Wait for the odds table to load
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-table"))
            )

            # Click "Show more" button if it exists to load all hidden odds
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, "a.showMore__text"
                )
                show_more.click()
                time.sleep(1)
            except:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Get all line values and all corresponding tables
            line_spans = soup.select("span.wcl-oddsValue_jvPMg")
            tables = soup.select("div.ui-table.oddsCell__odds")

            ou_data = {}
            seen_lines = set()
            line_to_table = {}
            table_idx = 0

            # Map unique lines (goals threshold) to their specific odds tables
            for line_span in line_spans:
                line_text = line_span.text.strip()
                # Check if it's a valid number (allowing dots and commas)
                if line_text and line_text.replace(".", "").replace(",", "").isdigit():
                    try:
                        line_value = float(line_text.replace(",", "."))

                        # Only process each line value once
                        if line_value not in seen_lines:
                            seen_lines.add(line_value)

                            if table_idx < len(tables):
                                line_to_table[line_value] = tables[table_idx]
                                table_idx += 1
                    except:
                        continue

            # Process each unique line
            for line_value in sorted(seen_lines):
                if line_value not in line_to_table:
                    continue

                table = line_to_table[line_value]
                line_key = f"OU_{line_value}"
                ou_data[line_key] = []

                # Extract odds from this specific table
                rows = table.select("div.ui-table__row")
                for row in rows:
                    bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                    if not bookmaker_elem:
                        continue

                    bookmaker = (
                        bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                    ).strip()
                    odds_cells = row.select("a.oddsCell__odd")

                    if len(odds_cells) >= 2:
                        try:
                            # Ignore cancelled odds (line-through)
                            if odds_cells[0].select("span.oddsCell__lineThrough"):
                                continue
                            if odds_cells[1].select("span.oddsCell__lineThrough"):
                                continue

                            over_span = odds_cells[0].select_one("span")
                            under_span = odds_cells[1].select_one("span")

                            if over_span and under_span:
                                over = float(over_span.text.strip().replace(",", "."))
                                under = float(under_span.text.strip().replace(",", "."))

                                ou_data[line_key].append(
                                    {
                                        "Bookmaker": bookmaker,
                                        "Over": over,
                                        "Under": under,
                                    }
                                )
                        except:
                            continue

            data["Odds_OU_FT"] = ou_data

        except Exception as e:
            print(f"Error extracting OU FT: {e}")

        return data

    def extract_statistics(self, match_id, data, period="overall", period_name="FT"):
        """Extracts statistics for a given period (overall=FT, 1st-half=HT, 2nd-half=2T)"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/summary/stats/{period}/?mid={match_id}"
        self.driver.get(url)

        try:
            # Wait until the statistics container is loaded on the page
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-testid='wcl-statistics']")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            statistics = soup.select("div[data-testid='wcl-statistics']")

            stats_dict = {}

            # Iterate through each statistics row (e.g., Ball Possession, Shots on Goal)
            for stat in statistics:
                # Home Value Extraction
                home_value_elem = stat.select_one(
                    "div.wcl-homeValue_3Q-7P span[data-testid='wcl-scores-simple-text-01']"
                )

                # Away Value Extraction
                away_value_elem = stat.select_one(
                    "div.wcl-awayValue_Y-QR1 span[data-testid='wcl-scores-simple-text-01']"
                )

                # Statistic Name Extraction
                stat_name_elem = stat.select_one(
                    "div[data-testid='wcl-statistics-category'] span[data-testid='wcl-scores-simple-text-01']"
                )

                if home_value_elem and away_value_elem and stat_name_elem:
                    home_value = home_value_elem.text.strip()
                    away_value = away_value_elem.text.strip()
                    stat_name = stat_name_elem.text.strip()

                    def convert_value(value):
                        """Cleans and converts string values into floats or integers"""
                        value_clean = value.split("(")[0].strip()

                        try:
                            # Convert percentages to standard float decimals
                            if value_clean.endswith("%"):
                                return float(value_clean[:-1]) / 100
                            return float(value_clean)
                        except ValueError:
                            try:
                                return int(value_clean)
                            except ValueError:
                                return value_clean

                    # Store in dict
                    stats_dict[stat_name] = {
                        "Home": convert_value(home_value),
                        "Away": convert_value(away_value),
                    }

            # If any statistics were found, append them to the main data dictionary
            if stats_dict:
                data[f"Statistics_{period_name}"] = stats_dict

        except Exception as e:
            print(f"Error extracting stats for {period_name}: {e}")

        return data

    def extract_statistics_ft(self, match_id, data):
        """Extracts Full Time statistics"""
        return self.extract_statistics(
            match_id, data, period="overall", period_name="FT"
        )

    def extract_statistics_ht(self, match_id, data):
        """Extracts Half Time statistics (1st half)"""
        return self.extract_statistics(
            match_id, data, period="1st-half", period_name="HT"
        )

    def extract_statistics_2t(self, match_id, data):
        """Extracts 2nd Half statistics"""
        return self.extract_statistics(
            match_id, data, period="2nd-half", period_name="2T"
        )

    def extract_odds_1x2_ht(self, match_id, data):
        """Extracts 1X2 Half Time odds"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        # Note the specific URL path for 1st-half odds
        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/1x2-odds/1st-half/?mid={match_id}"
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.ui-table.oddsCell__odds")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.select_one("div.ui-table.oddsCell__odds")

            if not table:
                return data

            rows = table.select("div.ui-table__row")
            odds_data = []

            for row in rows:
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()
                odds_cells = row.select("a.oddsCell__odd")

                # Need exactly at least 3 odds (1, X, 2)
                if len(odds_cells) < 3:
                    continue

                try:
                    odd_1 = None
                    odd_x = None
                    odd_2 = None

                    # Iterate strictly over the first three cells
                    for i, cell in enumerate(odds_cells[:3]):
                        # Ignore cancelled odds (crossed out)
                        if cell.select("span.oddsCell__lineThrough"):
                            continue

                        odd_span = cell.select_one("span")
                        if odd_span:
                            odd_value = float(odd_span.text.strip().replace(",", "."))

                            # Map based on column index
                            if i == 0:
                                odd_1 = odd_value
                            elif i == 1:
                                odd_x = odd_value
                            elif i == 2:
                                odd_2 = odd_value

                    if odd_1 or odd_x or odd_2:
                        odds_data.append(
                            {
                                "Bookmaker": bookmaker,
                                "Odd_1": odd_1,
                                "Odd_X": odd_x,
                                "Odd_2": odd_2,
                            }
                        )

                except Exception:
                    continue

            # Save strictly to the Half Time specific key
            data["Odds_1X2_HT"] = odds_data

        except Exception as e:
            print(f"Error extracting 1X2 HT: {e}")

        return data

    def extract_odds_btts_ft(self, match_id, data):
        """Extracts Both Teams to Score (BTTS) Full Time odds"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        # Specific URL for the BTTS market
        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/both-teams-to-score/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            # Wait for the odds table to load
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.ui-table.oddsCell__odds")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.select_one("div.ui-table.oddsCell__odds")

            if not table:
                return data

            rows = table.select("div.ui-table__row")
            btts_data = []

            for row in rows:
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()
                odds_cells = row.select("a.oddsCell__odd")

                # BTTS market always has two options: Yes and No
                if len(odds_cells) >= 2:
                    try:
                        # CRITICAL FIX: Skip cancelled odds
                        if odds_cells[0].select(
                            "span.oddsCell__lineThrough"
                        ) or odds_cells[1].select("span.oddsCell__lineThrough"):
                            continue

                        yes_span = odds_cells[0].select_one("span")
                        no_span = odds_cells[1].select_one("span")

                        if yes_span and no_span:
                            yes_odd = float(yes_span.text.strip().replace(",", "."))
                            no_odd = float(no_span.text.strip().replace(",", "."))

                            btts_data.append(
                                {"Bookmaker": bookmaker, "Yes": yes_odd, "No": no_odd}
                            )
                    except Exception:
                        continue

            data["Odds_BTTS_FT"] = btts_data

        except Exception as e:
            print(f"Error extracting BTTS FT: {e}")

        return data

    def extract_odds_dc_ft(self, match_id, data):
        """Extracts Double Chance (1X, 12, X2) Full Time odds"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        # Specific URL for the Double Chance market
        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/double-chance/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            # Wait for the odds table to load
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.ui-table.oddsCell__odds")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.select_one("div.ui-table.oddsCell__odds")

            if not table:
                return data

            rows = table.select("div.ui-table__row")
            dc_data = []

            for row in rows:
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()
                odds_cells = row.select("a.oddsCell__odd")

                # Double Chance always has 3 options (1X, 12, X2)
                if len(odds_cells) >= 3:
                    try:
                        odd_1x = None
                        odd_12 = None
                        odd_x2 = None

                        for i, cell in enumerate(odds_cells[:3]):
                            # Ignore cancelled odds
                            if cell.select("span.oddsCell__lineThrough"):
                                continue

                            odd_span = cell.select_one("span")
                            if odd_span:
                                odd_value = float(
                                    odd_span.text.strip().replace(",", ".")
                                )

                                if i == 0:
                                    odd_1x = odd_value
                                elif i == 1:
                                    odd_12 = odd_value
                                elif i == 2:
                                    odd_x2 = odd_value

                        if odd_1x or odd_12 or odd_x2:
                            dc_data.append(
                                {
                                    "Bookmaker": bookmaker,
                                    "Odd_1X": odd_1x,
                                    "Odd_12": odd_12,
                                    "Odd_X2": odd_x2,
                                }
                            )
                    except Exception:
                        continue

            # Save the data under the Double Chance (DC) key
            data["Odds_DC_FT"] = dc_data

        except Exception as e:
            print(f"Error extracting DC FT: {e}")

        return data

    def extract_odds_cs_ft(self, match_id, data):
        """Extracts Correct Score Full Time odds - ALL scores."""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/correct-score/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-table"))
            )

            # Click "Show more" button to expand all scores if it exists
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, "a.showMore__text"
                )
                show_more.click()
                time.sleep(1)  # Small pause to allow the DOM to render new rows
            except Exception:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            rows = soup.select("div.ui-table__row")

            cs_data = {}

            # Each row contains: bookmaker + score text + 1 odd
            for row in rows:
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()

                # Extract the score string (e.g., "1:0", "2:2")
                score_elem = row.select_one("span.wcl-oddsValue_jvPMg")
                if not score_elem:
                    continue

                score = score_elem.text.strip()
                if ":" not in score:
                    continue

                # Correct score rows only have 1 odd per line
                odds_cells = row.select("a.oddsCell__odd")
                if not odds_cells:
                    continue

                try:
                    # Ignore cancelled odds
                    if odds_cells[0].select("span.oddsCell__lineThrough"):
                        continue

                    odd_span = odds_cells[0].select_one("span")
                    if odd_span:
                        odd_value = float(odd_span.text.strip().replace(",", "."))

                        # Initialize the list for this specific score if it doesn't exist
                        if score not in cs_data:
                            cs_data[score] = []

                        # Append the bookmaker's odd to the specific score category
                        cs_data[score].append(
                            {"Bookmaker": bookmaker, "Odd": odd_value}
                        )
                except Exception:
                    continue

            data["Odds_CS_FT"] = cs_data

        except Exception as e:
            print(f"Error extracting CS FT: {e}")

        return data

    def extract_odds_asian_handicap_ft(self, match_id, data):
        """Extracts Asian Handicap Full Time odds - ALL LINES"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/asian-handicap/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-table"))
            )

            # Click "Show more" button to expand all handicap lines
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, "a.showMore__text"
                )
                show_more.click()
                time.sleep(1)
            except Exception:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            rows = soup.select("div.ui-table__row")

            ah_data = {}

            # Each row contains: bookmaker + handicap line + 2 odds (Home, Away)
            for row in rows:
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()

                # Extract the handicap line (e.g., "-1.5", "+0.5", "0")
                line_elem = row.select_one("span.wcl-oddsValue_jvPMg")
                if not line_elem:
                    continue

                line = line_elem.text.strip().replace(" ", "")
                if not line or ("+" not in line and "-" not in line and line != "0"):
                    continue

                line_key = f"AH_{line}"

                odds_cells = row.select("a.oddsCell__odd")
                if len(odds_cells) < 2:
                    continue

                try:
                    home_odd = None
                    away_odd = None

                    # Parse Home odd (First column)
                    if not odds_cells[0].select("span.oddsCell__lineThrough"):
                        home_span = odds_cells[0].select_one("span")
                        if home_span:
                            home_odd = float(home_span.text.strip().replace(",", "."))

                    # Parse Away odd (Second column)
                    if not odds_cells[1].select("span.oddsCell__lineThrough"):
                        away_span = odds_cells[1].select_one("span")
                        if away_span:
                            away_odd = float(away_span.text.strip().replace(",", "."))

                    if home_odd or away_odd:
                        # Initialize the list for this specific handicap line
                        if line_key not in ah_data:
                            ah_data[line_key] = []

                        ah_data[line_key].append(
                            {"Bookmaker": bookmaker, "Home": home_odd, "Away": away_odd}
                        )
                except Exception:
                    continue

            data["Odds_AH_FT"] = ah_data

        except Exception as e:
            print(f"Error extracting AH FT: {e}")

        return data

    def extract_odds_european_handicap_ft(self, match_id, data):
        """Extracts European Handicap Full Time odds - ALL LINES"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/european-handicap/full-time/?mid={match_id}"
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-table"))
            )

            # Click "Show more" button to expand all handicap lines
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, "a.showMore__text"
                )
                show_more.click()
                time.sleep(1)
            except Exception:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            rows = soup.select("div.ui-table__row")

            eh_data = {}

            # Each row contains: bookmaker + line + 3 odds (Home, Draw, Away)
            for row in rows:
                bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                if not bookmaker_elem:
                    continue

                bookmaker = (
                    bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                ).strip()

                # Extract the European Handicap line (e.g., "-1", "+2")
                line_elem = row.select_one("span.wcl-oddsValue_jvPMg")
                if not line_elem:
                    continue

                line = line_elem.text.strip().replace(" ", "")
                if not line:
                    continue

                line_key = f"EH_{line}"

                # European Handicap always has 3 options (Home, Draw, Away)
                odds_cells = row.select("a.oddsCell__odd")
                if len(odds_cells) < 3:
                    continue

                try:
                    home_odd = None
                    draw_odd = None
                    away_odd = None

                    # Parse Home odd (First column)
                    if not odds_cells[0].select("span.oddsCell__lineThrough"):
                        home_span = odds_cells[0].select_one("span")
                        if home_span:
                            home_odd = float(home_span.text.strip().replace(",", "."))

                    # Parse Draw odd (Second column)
                    if not odds_cells[1].select("span.oddsCell__lineThrough"):
                        draw_span = odds_cells[1].select_one("span")
                        if draw_span:
                            draw_odd = float(draw_span.text.strip().replace(",", "."))

                    # Parse Away odd (Third column)
                    if not odds_cells[2].select("span.oddsCell__lineThrough"):
                        away_span = odds_cells[2].select_one("span")
                        if away_span:
                            away_odd = float(away_span.text.strip().replace(",", "."))

                    if home_odd or draw_odd or away_odd:
                        if line_key not in eh_data:
                            eh_data[line_key] = []

                        eh_data[line_key].append(
                            {
                                "Bookmaker": bookmaker,
                                "Home": home_odd,
                                "Draw": draw_odd,
                                "Away": away_odd,
                            }
                        )
                except Exception:
                    continue

            data["Odds_EH_FT"] = eh_data

        except Exception as e:
            print(f"Error extracting EH FT: {e}")

        return data

    def extract_odds_ou_ht(self, match_id, data):
        """Extracts Over/Under Half Time odds - ALL LINES"""
        home_slug = data.get("Home_Slug", "")
        away_slug = data.get("Away_Slug", "")

        if not home_slug or not away_slug:
            return data

        url = f"{self.base_url}/match/football/{home_slug}/{away_slug}/odds/over-under/1st-half/?mid={match_id}"
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-table"))
            )

            # Click "Show more" button if it exists
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, "a.showMore__text"
                )
                show_more.click()
                time.sleep(1)
            except Exception:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Extract all line headers and ALL distinct tables
            line_spans = soup.select("span.wcl-oddsValue_jvPMg")
            tables = soup.select("div.ui-table.oddsCell__odds")

            ou_data = {}
            seen_lines = set()
            line_to_table = {}
            table_idx = 0

            # Map unique lines (e.g., 0.5, 1.5) to their corresponding tables
            for line_span in line_spans:
                line_text = line_span.text.strip()

                # Verify if the text is a valid number (e.g., "1.5")
                if line_text and line_text.replace(".", "").replace(",", "").isdigit():
                    try:
                        line_value = float(line_text.replace(",", "."))

                        # Process each line only once
                        if line_value not in seen_lines:
                            seen_lines.add(line_value)

                            if table_idx < len(tables):
                                line_to_table[line_value] = tables[table_idx]
                                table_idx += 1
                    except Exception:
                        continue

            # Process each unique table separately
            for line_value in sorted(seen_lines):
                if line_value not in line_to_table:
                    continue

                table = line_to_table[line_value]
                line_key = f"OU_{line_value}"
                ou_data[line_key] = []

                # Extract odds specifically from this mapped table
                rows = table.select("div.ui-table__row")
                for row in rows:
                    bookmaker_elem = row.select_one("div.wcl-bookmakerLogo_4IUU0 a img")
                    if not bookmaker_elem:
                        continue

                    bookmaker = (
                        bookmaker_elem.get("title") or bookmaker_elem.get("alt", "")
                    ).strip()
                    odds_cells = row.select("a.oddsCell__odd")

                    if len(odds_cells) >= 2:
                        try:
                            # Ignore cancelled odds
                            if odds_cells[0].select(
                                "span.oddsCell__lineThrough"
                            ) or odds_cells[1].select("span.oddsCell__lineThrough"):
                                continue

                            over_span = odds_cells[0].select_one("span")
                            under_span = odds_cells[1].select_one("span")

                            if over_span and under_span:
                                over = float(over_span.text.strip().replace(",", "."))
                                under = float(under_span.text.strip().replace(",", "."))

                                ou_data[line_key].append(
                                    {
                                        "Bookmaker": bookmaker,
                                        "Over": over,
                                        "Under": under,
                                    }
                                )
                        except Exception:
                            continue

            data["Odds_OU_HT"] = ou_data

        except Exception as e:
            print(f"Error occurred while scraping match {match_id}: {e}")
            pass

        return data

    def scrape_match(self, match_id):
        """Complete match scraping orchestration"""
        print(f"\nProcessing match ID: {match_id}...")

        # 1. Basic Info & Slugs
        data = self.get_match_basic_info(match_id)

        # Fail-fast: If critical data is missing, abort early
        if not data.get("Home_Slug") or not data.get("Away_Slug"):
            print("Slugs not found, skipping match...")
            return None

        print(f"{data.get('Home', '?')} vs {data.get('Away', '?')}")

        # 2. Odds 1X2 FT
        data = self.extract_odds_1x2_ft(match_id, data)
        if data.get("Odds_1X2_FT"):
            print(f" - 1X2 FT: {len(data['Odds_1X2_FT'])} bookmakers")

        # 3. Odds 1X2 HT
        data = self.extract_odds_1x2_ht(match_id, data)
        if data.get("Odds_1X2_HT"):
            print(f" - 1X2 HT: {len(data['Odds_1X2_HT'])} bookmakers")

        # 4. Odds Over/Under FT (ALL lines)
        data = self.extract_odds_ou_ft(match_id, data)
        if data.get("Odds_OU_FT"):
            total_lines = len(data["Odds_OU_FT"])
            total_bookmakers = sum(len(odds) for odds in data["Odds_OU_FT"].values())
            print(f" - O/U FT: {total_lines} lines, {total_bookmakers} odds")

        # 5. Odds Over/Under HT (ALL lines)
        data = self.extract_odds_ou_ht(match_id, data)
        if data.get("Odds_OU_HT"):
            total_lines = len(data["Odds_OU_HT"])
            total_bookmakers = sum(len(odds) for odds in data["Odds_OU_HT"].values())
            print(f"- O/U HT: {total_lines} lines, {total_bookmakers} odds")

        # 6. Odds BTTS FT
        data = self.extract_odds_btts_ft(match_id, data)
        if data.get("Odds_BTTS_FT"):
            print(f" - BTTS FT: {len(data['Odds_BTTS_FT'])} bookmakers")

        # 7. Odds Double Chance FT
        data = self.extract_odds_dc_ft(match_id, data)
        if data.get("Odds_DC_FT"):
            print(f" - DC FT: {len(data['Odds_DC_FT'])} bookmakers")

        # 8. Odds Correct Score FT
        data = self.extract_odds_cs_ft(match_id, data)
        if data.get("Odds_CS_FT"):
            total_scores = len(data["Odds_CS_FT"])
            total_cs_odds = sum(len(odds) for odds in data["Odds_CS_FT"].values())
            print(f" - CS FT: {total_scores} scores, {total_cs_odds} odds")

        # 9. Odds Asian Handicap FT
        data = self.extract_odds_asian_handicap_ft(match_id, data)
        if data.get("Odds_AH_FT"):
            total_lines = len(data["Odds_AH_FT"])
            total_ah_odds = sum(len(odds) for odds in data["Odds_AH_FT"].values())
            print(f" - Asian Handicap FT: {total_lines} lines, {total_ah_odds} odds")

        # 10. Odds European Handicap FT
        data = self.extract_odds_european_handicap_ft(match_id, data)
        if data.get("Odds_EH_FT"):
            total_lines = len(data["Odds_EH_FT"])
            total_eh_odds = sum(len(odds) for odds in data["Odds_EH_FT"].values())
            print(f" - European Handicap FT: {total_lines} lines, {total_eh_odds} odds")

        # 11. Statistics FT
        data = self.extract_statistics_ft(match_id, data)
        if data.get("Statistics_FT"):
            print(f" - Stats FT: {len(data['Statistics_FT'])} metrics")

        # 12. Statistics HT (1st half)
        data = self.extract_statistics_ht(match_id, data)
        if data.get("Statistics_HT"):
            print(f" - Stats HT: {len(data['Statistics_HT'])} metrics")

        # 13. Statistics 2T (2nd half)
        data = self.extract_statistics_2t(match_id, data)
        if data.get("Statistics_2T"):
            print(f" - Stats 2T: {len(data['Statistics_2T'])} metrics")

        # 14. Final Score and Goal Minutes (for past matches only)
        data = self.extract_goals_and_minutes(match_id, data)
        if data.get("Min_Goals_Home") is not None:
            total_goals = len(data.get("Min_Goals_Home", [])) + len(
                data.get("Min_Goals_Away", [])
            )
            if total_goals > 0:
                print(
                    f" - Goals: {len(data['Min_Goals_Home'])}x{len(data['Min_Goals_Away'])} - "
                    f"Minutes: {data['Min_Goals_Home']} x {data['Min_Goals_Away']}"
                )

        return data

    def scrape_matches(self, match_ids):
        """Scrapes multiple matches with a progress bar and incremental saving"""
        self.accept_cookies()

        # tqdm creates a nice progress bar in the terminal
        for match_id in tqdm(match_ids, desc="Scraping Matches"):
            result = self.scrape_match(match_id)
            if result:
                self.results.append(result)

                # Incremental save (Defensive Programming)
                # Saves to the output folder we created earlier
                incremental_path = "data/output/flashscore_incremental.json"
                with open(incremental_path, "w", encoding="utf-8") as f:
                    json.dump(self.results, f, ensure_ascii=False, indent=2)

        return self.results

    def save_results(self, filename="data/output/flashscore_results"):
        """Saves the scraped data to a comprehensive JSON and a flattened CSV file."""
        json_file = f"{filename}.json"
        existing_matches = []
        if os.path.exists(json_file) and os.path.getsize(json_file) > 0:
            try:
                with open(json_file, encoding="utf-8") as f:
                    existing_matches = json.load(f)
                if not isinstance(existing_matches, list):
                    existing_matches = []
            except (json.JSONDecodeError, OSError):
                existing_matches = []

        merged_by_id = {
            str(match.get("Id")): match
            for match in existing_matches
            if isinstance(match, dict) and match.get("Id")
        }
        for match in self.results:
            if isinstance(match, dict) and match.get("Id"):
                merged_by_id[str(match["Id"])] = match

        self.results = list(merged_by_id.values())

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\nSaved comprehensive JSON: {json_file} ({len(self.results)} matches)")

        try:
            df_simple = []
            for match in self.results:
                row = {
                    "Id": match.get("Id"),
                    "Date": match.get("Date"),
                    "Time": match.get("Time"),
                    "League": match.get("League"),
                    "Round": match.get("Round"),
                    "Home": match.get("Home"),
                    "Away": match.get("Away"),
                    "Home_Score": match.get("Home_Score"),
                    "Away_Score": match.get("Away_Score"),
                    "Best_Odd_1_FT": match.get("Best_Odd_1_FT"),
                    "Best_Odd_X_FT": match.get("Best_Odd_X_FT"),
                    "Best_Odd_2_FT": match.get("Best_Odd_2_FT"),
                }

                stats_ft = match.get("Statistics_FT", {})
                for stat_name, values in stats_ft.items():
                    row[f"Home_{stat_name}"] = values.get("Home")
                    row[f"Away_{stat_name}"] = values.get("Away")

                df_simple.append(row)

            df = pd.DataFrame(df_simple)
            csv_file = f"{filename}.csv"
            df.to_csv(csv_file, index=False, encoding="utf-8-sig")
            print(f"Saved flattened CSV: {csv_file}")

        except Exception as e:
            print(f"Error generating CSV file: {e}")

    def close(self):
        """Safely closes the Selenium WebDriver to free up memory."""
        self.driver.quit()


# Main block to run the scraper
if __name__ == "__main__":
    # Initialize the scraper - headless=True
    scraper = FlashScoreScraper(headless=True)

    try:
        match_ids = ["Ei2ZTQz9", "EJZRaQ15", "hf989Iwo"]

        results = scraper.scrape_matches(match_ids)
        scraper.save_results()

        print(f"\nScraping finished! Total: {len(results)} matches processed.")

    finally:
        # Closing scraper
        scraper.close()
