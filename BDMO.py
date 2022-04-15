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
            breakpoint()
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
        self.region = region
        self.years = years
        self.indicators = indicators
        self.data = pd.DataFrame()
        self.driver = driver

        self.links = {}
        self.find_links(banned_words=np.array(["районы", "городские округа", "область", "край", "республика", " округ ",
                                              "образования"]))

        for raion in self.links.keys():
            self.choose_indicators(raion)
            #self.get_the_data(raion)

    def find_links(self, banned_words, num=None, path="//div[@id='WebTree']"):
        divs = self.driver.find_elements_by_xpath(path + "/div")
        div_id = [el.get_attribute("id") for el in divs]
        texts = [el.text.lower() for el in divs]
        if num is None:
            num = len(divs)
        count = 1
        while count <= num:
            what_type = None
            seq = [True if i in texts[count - 1] else False for i in banned_words]
            if sum(seq) > 0:
                what_type = banned_words[seq]
            if len(div_id[count - 1]) != 0:
                divs[count - 1].click()
                # здесь мы оказываемся только в том случае, если имеем дело с папкой (неважно, есть запрещенка или нет)
                if what_type is None:
                    self.find_links(banned_words, num=1, path=path + f"/div[{count+1}]")
                else:
                    self.find_links(banned_words, path=path + f"/div[{count+1}]")
                count += 2
                continue
            elif what_type is None:
                self.links[texts[count-1]] = self.driver.find_element_by_xpath(
                    path + f"/div[{count}]/a").get_attribute("href")
            count += 1

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
                                    "местного самоуправления" in z or "почтовая" in z]
        except IndexError:
            return
        for ind_num in indicators_types_num:
            self.driver.find_elements_by_xpath(
                "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")[ind_num].click()
            indicator_menu_text = [el.text.lower() for el in self.driver.find_elements_by_xpath(
                f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num+1}]/div/div/a")]
            indicator_menu = self.driver.find_elements_by_xpath(
                f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num+1}]/div/div/a/input")
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
            indicator = self.driver.find_element_by_xpath(
                f"//table[@class='passport']/tbody/tr[{j}]/td[1]").text.lower()
            temp_data[self.indicators[[i for i, z in enumerate(self.indicators) if z in indicator][0]]] = [
                float(el.text) if len(el.text) > 0 else np.NaN for el in self.driver.find_elements_by_xpath(
                    f"//table[@class='passport']/tbody/tr[{j}]/td[position()>2]")]
        self.data = self.data.append(temp_data)


if __name__ == "__main__":
    Container(regions=["Хабаровский край"], indicators=[
        "доля протяженности автодорог общего пользования местного значения, не отвечающих", "автобусного", "аварийном",
        "незавершенного", "нуждающегося"], years=["years"])

# ["Приморский край", "Амурская область", "Кировская область", "Липецкая область", "Мурманская область",
# "Костромская область", "Республика Алтай", "Республика Марий Эл", "Хабаровский край", "Тульская область"]
