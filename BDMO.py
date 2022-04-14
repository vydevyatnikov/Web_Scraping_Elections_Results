import pandas as pd
import numpy as np
import itertools as iter
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
import selenium.common.exceptions as sel_exc
# разобраться с warning для Амурской области

class Container:

    def __init__(self, regions, years, indicators):
        self.regions = regions
        self.years = years
        self.indicators = indicators
        self.driver = self.start_driver("D:/DZ/Python/Driver/chromedriver.exe")
        try:
            self.driver.get("https://www.gks.ru/dbscripts/munst/")

            self.data = pd.DataFrame()
            self.initiate_process()
        finally:
            self.driver.quit()

    def initiate_process(self):
        regions_elem = self.driver.find_elements_by_xpath("//tr[2]/td/p/a")
        regions_names = [el.text for el in regions_elem]
        regions_url = [el.get_attribute("href") for el in regions_elem]
        for i in self.regions:
            #self.driver.get(regions_url[[j for j, z in enumerate(regions_names) if z == i][0]])
            self.driver.get(regions_url[regions_names.index(i)])
            self.driver.find_element_by_xpath("//input[@id='Knopka2']").click()
            self.data = self.data.append(RaionsPage(self.years, self.indicators, self.driver, region=i).data)


    @staticmethod
    def start_driver(driver_loc: str):
        option = ChromeOptions()
        option.add_argument('--disable-blink-features=AutomationControlled')
        option.add_experimental_option("excludeSwitches", ["enable-automation"])
        option.add_experimental_option('useAutomationExtension', False)
        return Chrome(executable_path=driver_loc, options=option)


class RaionsPage:

    def __init__(self, years, indicators, driver, region):
        self.years = years
        self.indicators = indicators
        self.data = pd.DataFrame()
        self.driver = driver
        self.links = self.find_links()
        self.region = region

        for raion in self.links.keys():
            self.choose_indicators(raion)
            #self.get_the_data(raion)

    def find_links(self):
        links = {}
        banned_words = ["районы", "городские округа", "область", "край", "республика", " округ ", "образования"]
        divs = self.driver.find_elements_by_xpath("//div[@id='WebTree']/div")
        div_id = [el.get_attribute("id") for el in divs]
        texts = [el.text.lower() for el in divs]
        sub_rows = [1]
        cities = False

        for num in range(1, len(divs)+1):
            seq = [1 if i in texts[num-1] else 0 for i in banned_words]
            if sum(seq) > 0:
                if len(div_id[num-1]) != 0 and seq[1] == 1:
                    cities = True
                else:
                    continue
            if len(div_id[num-1]) == 0:
                links[self.driver.find_element_by_xpath(
                    f"//div[@id='WebTree']/div[{num}]/a").text] = self.driver.find_element_by_xpath(
                    f"//div[@id='WebTree']/div[{num}]/a").get_attribute("href")
                #links.append(self.driver.find_element_by_xpath(f"//div[@id='WebTree']/div[{num}]/a").
                #             get_attribute("href"))
            elif "title" in div_id[num-1]:
                divs[num - 1].click()
                if cities:
                    sub_rows = list(range(2, len(self.driver.find_elements_by_xpath(
                        f"//div[@id='WebTree']/div[{num+1}]/div")) + 1))
                    cities = False
                continue
            else:
                links = {**links, **{self.driver.find_element_by_xpath(f"//div[@id='WebTree']/div[{num}]/div[{j}]/a").
                                         text: self.driver.find_element_by_xpath(
                    f"//div[@id='WebTree']/div[{num}]/div[{j}]/a").get_attribute("href") for j in sub_rows}}
                sub_rows = [1]
        return links

    def choose_indicators(self, raion):
        self.driver.get(self.links[raion])
        years_boxes = np.array(self.driver.find_elements_by_xpath("//table[@id='yearlist']/tbody/tr/td/input"))
        years_texts = np.array([int(el.text) for el in self.driver.find_elements_by_xpath(
            "//table[@id='yearlist']/tbody/tr/td")])
        for year in years_boxes[years_texts >= 2013]:
            year.click()
        self.driver.find_element_by_xpath("//table[@class='tbl']/tbody/tr[10]/td/input").click()
        indicators_types_texts = [el.text.lower() for el in self.driver.find_elements_by_xpath(
            "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")]
        try:
            indicators_types_num = [i for i, z in enumerate(indicators_types_texts) if
                                    "местного самоуправления" in z][0]
        except IndexError:
            return
        self.driver.find_elements_by_xpath(
            "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")[indicators_types_num].click()
        indicator_menu_text = [el.text.lower() for el in self.driver.find_elements_by_xpath(
            f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{indicators_types_num+1}]/div/div/a")]
        indicator_menu = self.driver.find_elements_by_xpath(
            f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{indicators_types_num+1}]/div/div/a/input")
        for i in range(len(indicator_menu_text)):
            if sum([1 if ind in indicator_menu_text[i] else 0 for ind in self.indicators]) > 0:
                indicator_menu[i].click()
        self.driver.find_element_by_xpath("//td[@class='buttons']/input[@name='Button_Table']").click()

        years = pd.Series([el.text for el in self.driver.find_elements_by_xpath(
            "//table[@class='passport']/tbody/tr[1]/th")[2:]], dtype="int")
        temp_data = pd.DataFrame({**{"year": years, "region": pd.Series(iter.repeat(self.region, len(years))),
                                     "raion": pd.Series(iter.repeat(raion, len(years)))},
                                  **{i: iter.repeat(np.NaN, len(years)) for i in self.indicators}})
        for j in range(2, len(self.driver.find_elements_by_xpath("//table[@class='passport']/tbody/tr")) + 1):
            indicator = self.driver.find_element_by_xpath(f"//table[@class='passport']/tbody/tr[{j}]/td[1]").text
            temp_data[self.indicators[[i for i, z in enumerate(self.indicators) if z in indicator][0]]] = [
                float(el.text) if len(el.text) > 0 else np.NaN for el in self.driver.find_elements_by_xpath(
                    f"//table[@class='passport']/tbody/tr[{j}]/td[position()>2]")]
        self.data = self.data.append(temp_data)

    def get_the_data(self, raion):
        years = pd.Series([el.text for el in self.driver.find_elements_by_xpath(
            "//table[@class='passport']/tbody/tr[1]/th")[2:]], dtype="int")
        temp_data = pd.DataFrame({**{"year": years, "region": pd.Series(iter.repeat(self.region, len(years))),
                                     "raion": pd.Series(iter.repeat(raion, len(years)))},
                                 **{i: iter.repeat(np.NaN, len(years)) for i in self.indicators}})
        for j in range(2, len(self.driver.find_elements_by_xpath("//table[@class='passport']/tbody/tr")) + 1):
            indicator = self.driver.find_element_by_xpath(f"//table[@class='passport']/tbody/tr[{j}]/td[1]").text
            temp_data[self.indicators[[i for i, z in enumerate(self.indicators) if z in indicator][0]]] = [
                float(el.text) if len(el.text) > 0 else np.NaN for el in self.driver.find_elements_by_xpath(
                    f"//table[@class='passport']/tbody/tr[{j}]/td[position()>2]")]
        self.data = self.data.append(temp_data)




class RaionData:

    def __init__(self, link, driver):
        self.link = link
        self.driver = driver

        #self.driver.find_elements_by_xpath("//div/a[@class='item']").get_attribute("href")





if __name__ == "__main__":
    Container(regions=["Кировская область"], indicators=[
        "автодорог", "автобусного", "аварийном", "незавершенного", "жилищные"], years=["years"])

# ["Приморский край", "Амурская область", "Кировская область", "Липецкая область", "Мурманская область",
# "Костромская область", "Республика Алтай", "Республика Марий Эл", "Хабаровский край", "Тульская область"]