import pandas as pd
import numpy as np
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
import selenium.common.exceptions as sel_exc


class Container:

    def __init__(self, regions, years, indicators):
        self.regions = regions
        self.years = years
        self.indicators = indicators
        self.driver = self.start_driver("D:/DZ/Python/Driver/chromedriver.exe")
        try:
            self.driver.get("https://www.gks.ru/dbscripts/munst/")

            self.data = pd.DataFrame()
            self.get_the_data()
        finally:
            self.driver.quit()

    def get_the_data(self):
        regions_elem = self.driver.find_elements_by_xpath("//tr[2]/td/p/a")
        regions_names = [el.text for el in regions_elem]
        regions_url = [el.get_attribute("href") for el in regions_elem]
        for i in self.regions:
            #self.driver.get(regions_url[[j for j, z in enumerate(regions_names) if z == i][0]])
            self.driver.get(regions_url[regions_names.index(i)])
            self.driver.find_element_by_xpath("//td[@id='Knopka2']").click()
            region_data = RaionsPage(self.years, self.indicators, self.driver)


    @staticmethod
    def start_driver(driver_loc: str):
        option = ChromeOptions()
        option.add_argument('--disable-blink-features=AutomationControlled')
        option.add_experimental_option("excludeSwitches", ["enable-automation"])
        option.add_experimental_option('useAutomationExtension', False)
        return Chrome(executable_path=driver_loc, options=option)


class RaionsPage:

    def __init__(self, years, indicators, driver):
        self.years = years
        self.indicators = indicators
        self.data = pd.DataFrame()
        self.driver = driver

    def find_data(self):
        self.driver.find_elements_by_xpath

if __name__ == "__main__":
    Container(regions=["Псковская область"], indicators=["some_stuff"], years=["years"])

# ["Приморский край", "Амурская область", "Кировская область", "Липецкая область", "Мурманская область",
# "Костромская область", "Республика Алтай", "Республика Марий Эл", "Хабаровский край", "Тульская область"]