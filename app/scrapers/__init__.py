from app.scrapers.hackernews import HackerNewsScraper
from app.scrapers.usajobs import USAJobsScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.dice import DiceScraper
from app.scrapers.jobicy import JobicyScraper
from app.scrapers.indeed import IndeedScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.himalayas import HimalayasScraper
from app.scrapers.wellfound import WellfoundScraper
from app.scrapers.builtin import BuiltInScraper
from app.scrapers.greenhouse import GreenhouseScraper

ALL_SCRAPERS = [
    HackerNewsScraper, USAJobsScraper,
    LinkedInScraper, DiceScraper,
    JobicyScraper, IndeedScraper,
    RemoteOKScraper, HimalayasScraper,
    WellfoundScraper, BuiltInScraper,
    GreenhouseScraper,
]
