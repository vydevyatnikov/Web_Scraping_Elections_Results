import pandas as pd
import numpy as np
import itertools
import pickle
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
# import selenium.common.exceptions as sel_exc


class Container:

    def __init__(self, regions, years, indicators):
        self.regions = regions
        self.years = years
        self.indicators = indicators
        self.driver = self.start_driver("D:/DZ/Python/Driver/chromedriver.exe")
        with open("D:/DZ/Elections_database/Scripts_related_data/dicts/BDMO_ind_dict.pkl", "rb") as inp:
            self.alias_dict = pickle.load(inp)

        try:
            self.driver.get("https://www.gks.ru/dbscripts/munst/")

            self.data = pd.DataFrame()
            self.initiate_process()
        finally:
            breakpoint()
            # self.data.to_csv("D:/DZ/Course_5/Курсовая/data/BDMO/overall.csv")
            self.driver.quit()

    def initiate_process(self):
        regions_elem = self.driver.find_elements_by_xpath("//tr[2]/td/p/a")
        regions_names = [el.text for el in regions_elem]
        regions_url = [el.get_attribute("href") for el in regions_elem]
        for i in self.regions:
            # self.driver.get(regions_url[[j for j, z in enumerate(regions_names) if z == i][0]])
            self.driver.get(regions_url[regions_names.index(i)])
            self.driver.find_element_by_xpath("//input[@id='Knopka2']").click()
            self.data = self.data.append(RaionsPage(self.years, self.indicators, self.driver, region=i,
                                                    alias_dict=self.alias_dict).data)

    @staticmethod
    def start_driver(driver_loc: str):
        option = ChromeOptions()
        option.add_argument('--disable-blink-features=AutomationControlled')
        option.add_experimental_option("excludeSwitches", ["enable-automation"])
        option.add_experimental_option('useAutomationExtension', False)
        return Chrome(executable_path=driver_loc, options=option)


class RaionsPage:

    def __init__(self, years, indicators, driver, region, alias_dict):
        self.region = region
        self.years = years
        self.indicators = indicators
        self.data = pd.DataFrame()
        self.driver = driver
        self.alias_dict = alias_dict

        self.links = {}
        self.find_links(banned_words=np.array(["районы", "городские округа", "область", "край", "республика", " округа",
                                               "образования", "сельсовет"]))

        for raion in self.links.keys():
            self.choose_indicators(raion)
            # self.get_the_data(raion)
        self.data.to_csv(f"D:/DZ/Course_6/Diploma/Data/Financial_data/script/{region}.csv")

    def find_links(self, banned_words, num=None, path="//div[@id='WebTree']"):
        divs = self.driver.find_elements_by_xpath(path + "/div")
        div_id = [el.get_attribute("id") for el in divs]
        texts = [el.text for el in divs]
        if num is None:
            num = len(divs)
        count = 1
        while count <= num:
            what_type = None
            seq = [True if i in texts[count - 1].lower() else False for i in banned_words]
            if sum(seq) > 0:
                what_type = banned_words[seq]
            if len(div_id[count - 1]) != 0:
                divs[count - 1].click()
                # здесь мы оказываемся только в том случае, если имеем дело с папкой (неважно, есть запрещенка или нет)
                if what_type is None:
                    self.find_links(banned_words, num=1, path=path + f"/div[{count + 1}]")
                else:
                    self.find_links(banned_words, path=path + f"/div[{count + 1}]")
                count += 2
                continue
            elif what_type is None:
                self.links[texts[count - 1]] = self.driver.find_element_by_xpath(
                    path + f"/div[{count}]/a").get_attribute("href")
            count += 1

    def choose_indicators(self, raion):
        self.driver.get(self.links[raion])
        years_boxes = np.array(self.driver.find_elements_by_xpath("//table[@id='yearlist']/tbody/tr/td/input"))
        years_texts = np.array([int(el.text) for el in self.driver.find_elements_by_xpath(
            "//table[@id='yearlist']/tbody/tr/td")])
        for year in years_boxes[years_texts >= 2013]:  # поменять на years
            year.click()
        self.driver.find_element_by_xpath("//table[@class='tbl']/tbody/tr[10]/td/input").click()
        indicators_types_texts = [el.text.lower() for el in self.driver.find_elements_by_xpath(
            "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")]
        try:
            indicators_types_num = [i for i, z in enumerate(indicators_types_texts) if  # replace "почтовая" with var
                                    "местный бюджет" in z]
            # "местного самоуправления" in z or "почтовая" in z or "коммунальная сфера" in z or
            #                                     "спорт" in z or "население" in z
        except IndexError:
            return

        how_many_types = len(indicators_types_num)

        for j in range(how_many_types):
            ind_num = indicators_types_num[j]
            self.driver.find_elements_by_xpath(
                "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")[ind_num].click()
            indicator_menu_text = [el.text.lower() for el in self.driver.find_elements_by_xpath(
                f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num + 1}]/div/div/a")]
            indicator_menu = self.driver.find_elements_by_xpath(
                f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num + 1}]/div/div/a/input")
            for i in range(len(indicator_menu_text)):
                indic_temp = [True if ind == indicator_menu_text[i] else False for ind in self.alias_dict.keys()]
                if sum(indic_temp) == 1:
                    indicator_menu[i].click()
                    continue
                elif sum(indic_temp) > 1:
                    breakpoint()
        submit_button = self.driver.find_element_by_xpath("//td[@class='buttons']/input[@name='Button_Table']")
        if submit_button.is_enabled():
            submit_button.click()
        else:
            return

        data = pd.DataFrame()

        # creates dataframe, which basically replicates data presented on the site
        for tp in range(len(self.driver.find_elements_by_xpath("//table[@class='passport']"))):
            elems = self.driver.find_elements_by_xpath(
                f"//table[@class='passport' and position()={tp + 1}]/tbody/tr[position() > 1]/td[1]")
            temp_df = pd.DataFrame({"class": pd.Series([el.get_attribute("class") for el in elems]),
                                    "style": pd.Series([style if len(style) != 0 else "absent"
                                                        for style in [el.get_attribute("style") for el in elems]]),
                                    "text": pd.Series([el.text.lower() for el in elems])})
            for num in range(len(self.years)):
                temp_df[self.years[num]] = pd.Series(float(el.text) if len(el.text) > 0 else np.NaN
                                                     for el in self.driver.find_elements_by_xpath(
                    f"//table[@class='passport' and position()={tp + 1}]/tbody/tr[position() > 1]/td[{num + 3}]"))
            data = data.append(temp_df)
        data.reset_index(inplace=True, drop=True)

        indices = np.array([len(data)])

        data["indicator"] = pd.Series(itertools.repeat("Not present", len(data)))
        temp_series = data.loc[(data["class"] == "pok") & (data["style"] == "absent"), "text"]
        for g in temp_series.index:
            indic_temp = [m for m in self.alias_dict.keys() if m == temp_series[g]]
            if len(indic_temp) == 1:
                temp_series.loc[g] = self.alias_dict[indic_temp[0]]
            else:
                breakpoint()
        indices = np.concatenate((np.array(temp_series.index), indices))
        for i in range(len(temp_series)):
            data.loc[temp_series.index[i]:indices[(indices - temp_series.index[i]) > 0].min() - 1,
                     "indicator"] = temp_series.iloc[i]

        data["sub_indicator"] = pd.Series(itertools.repeat("Not present", len(data)))
        temp_series = data.loc[(data["class"] == "prizn") & (data["style"] == "padding-left: 10pt;"), "text"]
        indices = np.concatenate((indices, np.array(temp_series.index)))
        for i in range(len(temp_series)):
            data.loc[temp_series.index[i]:indices[(indices - temp_series.index[i]) > 0].min() - 1,
                     "sub_indicator"] = temp_series.iloc[i]

        data["times"] = pd.Series(itertools.repeat("Not present", len(data)))
        temp_series = data.loc[(data["class"] == "prizn") & (data["style"] == "padding-left: 20pt;"), "text"]
        indices = np.concatenate((indices, np.array(temp_series.index)))
        for i in range(len(temp_series)):
            data.loc[temp_series.index[i]:indices[(indices - temp_series.index[i]) > 0].min() - 1,
                     "times"] = self.alias_dict[temp_series.iloc[i]]
        print("Done")

        years = pd.Series([el.text for el in self.driver.find_elements_by_xpath(
            "//table[@class='passport' and position()=1]/tbody/tr[1]/th")[2:]], dtype="int")

        data_dict = {i:
                     {j:
                      {g:
                       data.loc[(data.indicator == i) & (data.sub_indicator == j) &
                                (data.times == g)].iloc[0, 3:len(years) + 3]
                       for g in data.loc[(data.indicator == i) & (data.sub_indicator == j)].times.unique()}
                      for j in data.loc[data.indicator == i].sub_indicator.unique()}
                     for i in data.indicator.unique()}
        temp_data = pd.DataFrame({**{"year": years, "region": pd.Series(itertools.repeat(self.region, len(years))),
                                     "raion": pd.Series(itertools.repeat(raion, len(years)))},
                                  **{i: itertools.repeat(np.NaN, len(years)) for i in self.indicators.keys()}})

        for ind in self.indicators.keys():
            multiple_subs = False
            try:
                temp_ind = data_dict[ind]["Not present"]["Not present"]
            except KeyError:
                continue
            if len(self.indicators[ind]) != 0:
                if len(self.indicators[ind]) > 1:
                    multiple_subs = True
                for sub_ind in self.indicators[ind].keys():
                    try:
                        temp_sub_ind = data_dict[ind][sub_ind]["Not present"]
                    except KeyError:
                        continue
                    temp_ind.loc[~pd.isnull(temp_sub_ind)] = temp_sub_ind.loc[~pd.isnull(temp_sub_ind)]
                    if len(self.indicators[ind][sub_ind]) != 0:
                        for t in self.indicators[ind][sub_ind]:
                            temp_t = data_dict[ind][sub_ind][t]
                            temp_ind.loc[~pd.isnull(temp_t)] = temp_t.loc[~pd.isnull(temp_t)]
                    if multiple_subs:
                        temp_data[sub_ind] = temp_ind.values
            if not multiple_subs:
                temp_data[ind] = temp_ind.values
        self.data = self.data.append(temp_data)

    def extract_the_data(self, elems_df, level, indic):
        presets = {"0": ("pok", "absent"), "1": ("prizn", "PADDING-LEFT: 10pt;"), "2": ("prizn", "PADDING-LEFT: 20pt;")}
        temp_obj = elems_df.loc[(elems_df["class"] == presets[level][0]) & (elems_df["style"] == presets[level][2])]
        temp_df = pd.DataFrame()
        for row in range(len(temp_obj)):
            mapping = [True if i in temp_obj.text[row] else False for i in indic.keys()]
            if sum(mapping) == 0:
                continue
            elif len(indic[indic.keys()[mapping]]) == 0:
                self.data = self.data.append(pd.DataFrame({}))
            temp_df = temp_df.append(pd.DataFrame({"indicator": pd.Series(np.array(indic.keys())[mapping])
                                                   if sum(mapping) > 0 else np.NaN,
                                                   "start": temp_obj.index[row],
                                                   "end": pd.Series(temp_obj.index[row + 1]) if row != len(temp_obj) - 1
                                                   else pd.Series(len(temp_obj))}))


if __name__ == "__main__":
    Container(regions=["Амурская область", "Кировская область", "Липецкая область", "Мурманская область",
                       "Костромская область", "Республика Алтай", "Республика Марий Эл", "Хабаровский край",
                       "Тульская область"],
              indicators={"расходы бюджета": {"дорожное хозяйство (дорожные фонды)": {},
                                              "жилищно-коммунальное хозяйство": {},
                                              "образование": {}}},
              years=["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022"])
