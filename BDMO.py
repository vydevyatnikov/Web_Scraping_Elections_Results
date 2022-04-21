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
            self.data.to_csv("D:/DZ/Course_5/Курсовая/data/BDMO/overall.csv")
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
        self.data.to_csv(f"D:/DZ/Course_5/Курсовая/data/BDMO/{region}.csv")

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
                    self.find_links(banned_words, num=1, path=path + f"/div[{count+1}]")
                else:
                    self.find_links(banned_words, path=path + f"/div[{count+1}]")
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
        for year in years_boxes[years_texts >= 2013]: # поменять на years
            year.click()
        self.driver.find_element_by_xpath("//table[@class='tbl']/tbody/tr[10]/td/input").click()
        indicators_types_texts = [el.text.lower() for el in self.driver.find_elements_by_xpath(
            "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")]
        try:
            indicators_types_num = [i for i, z in enumerate(indicators_types_texts) if  # replace "почтовая" with var
                                    "местного самоуправления" in z or "почтовая" in z or "коммунальная сфера" in z or
                                    "спорт" in z or "население" in z]
        except IndexError:
            return

        how_many_types = len(indicators_types_num)

        for j in range(how_many_types):
            ind_num = indicators_types_num[j]
            self.driver.find_elements_by_xpath(
                "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")[ind_num].click()
            indicator_menu_text = [el.text.lower() for el in self.driver.find_elements_by_xpath(
                f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num+1}]/div/div/a")]
            indicator_menu = self.driver.find_elements_by_xpath(
                f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num+1}]/div/div/a/input")
            for i in range(len(indicator_menu_text)):
                indic_temp = [True if ind in indicator_menu_text[i] else False for ind in self.indicators]
                if sum(indic_temp) > 0:
                    indicator_menu[i].click()
        submit_button = self.driver.find_element_by_xpath("//td[@class='buttons']/input[@name='Button_Table']")
        if submit_button.is_enabled():
            submit_button.click()
        else:
            return

        data = pd.DataFrame()

        for tp in range(len(self.driver.find_elements_by_xpath("//table[@class='passport']"))):
            elems = self.driver.find_elements_by_xpath(
                f"//table[@class='passport' and position()={tp+1}]/tbody/tr[position() > 1]/td[1]")
            temp_df = pd.DataFrame({"class": pd.Series([el.get_attribute("class") for el in elems]),
                                     "style": pd.Series([style if len(style) != 0 else "absent"
                                                         for style in [el.get_attribute("style") for el in elems]]),
                                     "text": pd.Series([el.text.lower() for el in elems])})
            for num in range(len(self.years)):
                temp_df[self.years[num]] = pd.Series(float(el.text) if len(el.text) > 0 else np.NaN
                                                     for el in self.driver.find_elements_by_xpath(
                    f"//table[@class='passport' and position()={tp+1}]/tbody/tr[position() > 1]/td[{num+3}]"))
            data = data.append(temp_df)
        data.reset_index(inplace=True, drop=True)

        indices = np.array([len(data)])

        data["indicator"] = pd.Series(iter.repeat("Not present", len(data)))
        temp_series = data.loc[(data["class"] == "pok") & (data["style"] == "absent"), "text"]
        for g in temp_series.index:
            temp_series.loc[g] = np.array(list(self.indicators.keys()))[[
                True if m in temp_series[g] else False for m in self.indicators.keys()]][0]
        indices = np.concatenate((np.array(temp_series.index), indices))
        for i in range(len(temp_series)):
            data.loc[temp_series.index[i]:indices[
                                              (indices-temp_series.index[i]) > 0].min()-1,
                     "indicator"] = temp_series.iloc[i]

        data["sub_indicator"] = pd.Series(iter.repeat("Not present", len(data)))
        temp_series = data.loc[(data["class"] == "prizn") & (data["style"] == "padding-left: 10pt;"), "text"]
        indices = np.concatenate((indices, np.array(temp_series.index)))
        for i in range(len(temp_series)):
            data.loc[temp_series.index[i]:indices[(indices-temp_series.index[i]) > 0].min()-1,
                     "sub_indicator"] = temp_series.iloc[i]

        data["times"] = pd.Series(iter.repeat("Not present", len(data)))
        temp_series = data.loc[(data["class"] == "prizn") & (data["style"] == "padding-left: 20pt;"), "text"]
        indices = np.concatenate((indices, np.array(temp_series.index)))
        for i in range(len(temp_series)):
            data.loc[temp_series.index[i]:indices[(indices-temp_series.index[i]) > 0].min()-1,
                     "times"] = temp_series.iloc[i]
        print("Done")

        years = pd.Series([el.text for el in self.driver.find_elements_by_xpath(
                "//table[@class='passport' and position()=1]/tbody/tr[1]/th")[2:]], dtype="int")
        #temp_data = pd.DataFrame({"years": years, "region": pd.Series(iter.repeat(self.region, len(years))),
        #                             "raion": pd.Series(iter.repeat(raion, len(years)))})
        temp_data = pd.DataFrame({**{"year": years, "region": pd.Series(iter.repeat(self.region, len(years))),
                                     "raion": pd.Series(iter.repeat(raion, len(years)))},
                                  **{i: iter.repeat(np.NaN, len(years)) for i in self.indicators.keys()}})
        for ind in self.indicators.keys():
            temp_ind = data.loc[(data["indicator"] == ind) & (data["sub_indicator"] == "Not present") &
                                (data["times"] == "Not present")]
            if len(self.indicators[ind]) == 0:
                if len(temp_ind) != 0:
                    temp_data[ind] = temp_ind.iloc[0, 3:len(years)+3].values
                else:
                    continue
            else:
                for sub_ind in self.indicators[ind].keys():
                    temp_sub_ind = data.loc[
                        (data["indicator"] == ind) & (data["sub_indicator"] == sub_ind) &
                        (data["times"] == "Not present")]
                    temp_ind.iloc[0, np.array(range(temp_ind.shape[1]))[~pd.isnull(temp_sub_ind).values[0]]] = temp_sub_ind.iloc[~pd.isnull(temp_sub_ind)]
                    if len(self.indicators[ind][sub_ind]) == 0:
                        if len(temp_ind) != 0:
                            temp_data[ind] = temp_ind.iloc[0, 3:len(years) + 3].values
                        else:
                            continue
                    else:
                        for t in self.indicators[ind][sub_ind].keys():
                            temp_t = data.loc[
                                (data["indicator"] == ind) & (data["sub_indicator"] == sub_ind) &
                                (data["times"] == t)]
                            temp_ind.loc[~pd.isnull(temp_t.indicator)] = temp_t[~pd.isnull(temp_t.indicator)]
                            if len(self.indicators[ind][sub_ind][t]) == 0 and len(temp_ind) != 0:
                                temp_data[ind] = temp_ind.iloc[0, 3:len(years) + 3].values
        self.data = self.data.append(temp_data)






        #how_many_types = len(indicators_types_num)
        #mapping_dict = {str(g): {} for g in range(how_many_types)}
        #
        #for j in range(how_many_types):
        #    ind_num = indicators_types_num[j]
        #    self.driver.find_elements_by_xpath(
        #        "//table[@class='tbl']/tbody/tr[10]/td/span/div/span/span[2]")[ind_num].click()
        #    indicator_menu_text = [el.text.lower() for el in self.driver.find_elements_by_xpath(
        #        f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num+1}]/div/div/a")]
        #    indicator_menu = self.driver.find_elements_by_xpath(
        #        f"//table[@class='tbl']/tbody/tr[10]/td/span/div[{ind_num+1}]/div/div/a/input")
        #    for i in range(len(indicator_menu_text)):
        #        indic_temp = [True if ind in indicator_menu_text[i] else False for ind in self.indicators]
        #        if sum(indic_temp) > 0:
        #            mapping_dict[str(j)][self.indicators[indic_temp][0]] = len(mapping_dict[str(j)])
        #            indicator_menu[i].click()
        #self.driver.find_element_by_xpath("//td[@class='buttons']/input[@name='Button_Table']").click()
       # self.extract_the_data()


        #years = pd.Series([el.text for el in self.driver.find_elements_by_xpath(
        #    "//table[@class='passport']/tbody/tr[1]/th")[2:]], dtype="int")
        #temp_data = pd.DataFrame({**{"year": years, "region": pd.Series(iter.repeat(self.region, len(years))),
        #                             "raion": pd.Series(iter.repeat(raion, len(years)))},
        #                          **{i: iter.repeat(np.NaN, len(years)) for i in self.indicators}})
        #for j in range(2, len(self.driver.find_elements_by_xpath("//table[@class='passport']/tbody/tr")) + 1):
        #    indicator = self.driver.find_element_by_xpath(
        #        f"//table[@class='passport']/tbody/tr[{j}]/td[1]").text.lower()
        #    temp_data[self.indicators[[i for i, z in enumerate(self.indicators) if z in indicator][0]]] = [
        #        float(el.text) if len(el.text) > 0 else np.NaN for el in self.driver.find_elements_by_xpath(
        #            f"//table[@class='passport']/tbody/tr[{j}]/td[position()>2]")]
        #self.data = self.data.append(temp_data)

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
            temp_df = temp_df.append(pd.DataFrame({"indicator":
                                                   pd.Series(np.array(indic.keys())[mapping])
                                                   if sum(mapping) > 0 else np.NaN,
                                                   "start": temp_obj.index[row],
                                                   "end": pd.Series(temp_obj.index[row+1]) if row != len(temp_obj)-1
                                                   else pd.Series(len(temp_obj))}))


if __name__ == "__main__":
    Container(regions=["Приморский край", "Амурская область", "Кировская область", "Липецкая область",
                       "Мурманская область", "Костромская область", "Республика Алтай", "Республика Марий Эл",
                       "Хабаровский край", "Тульская область", "Новгородская область"],
              indicators={
        "доля протяженности автодорог общего пользования местного значения, не отвечающих": {},
        "не имеющих регулярного автобусного": {},
        "доля муниципальных дошкольных образовательных учреждений, здания которых находятся в аварийном состоянии": {},
        "объем незавершенного в установленные сроки строительства": {},
        "состоящего на учете в качестве нуждающегося в жилых помещениях": {},
        "число спортивных сооружений": {},
        "заменено и отремонтировано уличной газовой сети": {},
        "протяженность тепловых и паровых сетей, которые были заменены и отремонтированы": {},
        "протяжение уличной канализационной сети, которая заменена": {},
        "оценка численности населения": {"все население": {"на 1 января"}}},
              years=["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022"])

# ["Приморский край", "Амурская область", "Кировская область", "Липецкая область", "Мурманская область",
# "Костромская область", "Республика Алтай", "Республика Марий Эл", "Хабаровский край", "Тульская область"]
