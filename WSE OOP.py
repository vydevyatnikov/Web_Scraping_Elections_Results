import pandas as pd
import numpy as np
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as sel_exc
from selenium.webdriver.common.alert import Alert
import time
from itertools import repeat
import pickle
import traceback
import imageio as im


class CollectTheData:

    def __init__(self, dates: dict,
                 regions: list = None, dicts_dir: str = "D:/DZ/Elections_database/Scripts_related_data/dicts/",
                 driver_loc: str = None, output_dir: str = "C:/Users",
                 what_to_extract: dict = None,
                 uiks_numbers_only: bool = False, supplement_dicts: bool = False, data_info_only: bool = False,
                 conditions: dict = None, start_from: str = None):

        self.dates = dates
        self.driver_loc = driver_loc
        self.output_dir = output_dir
        self.uiks_numbers_only = uiks_numbers_only
        self.supplement_dicts = supplement_dicts
        self.data_info_only = data_info_only
        self.dicts_dir = dicts_dir

        self.conditions = self.check_conditions(conditions)
        self.regions, self.regions_link = self.check_regions(regions, start_from)
        self.what_to_extract = {"maj_case": True, "prop_case": True} if what_to_extract is None else what_to_extract
        self.data = {i: pd.DataFrame() for i in self.what_to_extract.keys()}
        self.cand_data = {i: pd.DataFrame() for i in self.what_to_extract.keys()}

        try:
            self.driver = self.start_driver()
            self.get_the_data()
        except Exception as excp:
            input("Take a look at the page")
            raise excp
        finally:
            self.driver.quit()

    def start_driver(self):
        option = ChromeOptions()
        option.add_argument('--disable-blink-features=AutomationControlled')
        option.add_experimental_option("excludeSwitches", ["enable-automation"])
        option.add_experimental_option('useAutomationExtension', False)
        if self.driver_loc is None:
            driver = Chrome()
        else:
            driver = Chrome(executable_path=self.driver_loc, options=option)
        return driver

    def check_conditions(self, conditions):
        with open(self.dicts_dir + "full_set_of_possible_conditions.pkl", "rb") as inp:
            full_set_of_possible_conditions = pickle.load(inp)
        if conditions is None:
            conditions = full_set_of_possible_conditions
        else:
            for cond in full_set_of_possible_conditions.keys():
                if cond not in conditions.keys():
                    conditions[cond] = full_set_of_possible_conditions[cond]
        return conditions

    def check_regions(self, regions, start_from):
        with open(self.dicts_dir + "region_link.pkl", "rb") as inp:
            region_link = pickle.load(inp)
        if regions is None:
            regions = region_link.keys()  # возможно нужно обернуть keys в list!
        if start_from is not None:
            regions = regions[[i for i, z in enumerate(regions) if z in start_from][0]:]
        return regions, region_link

    def get_the_data(self):
        all_possible_combinations = CollectTheData.cartesian_product(*self.conditions.values())
        for region in self.regions:
            for condition in all_possible_combinations:
                self.filter_elections(region, condition)
                elections_elements = self.driver.find_elements_by_xpath("//a[@class='viboryLink']")
                if len(elections_elements) == 0:
                    continue
                elections_dict = {el.text: el.get_attribute("href") for el in elections_elements}
                for elections in elections_dict:
                    res = ElectionsPage(self.driver, condition, elections, elections_dict[elections],
                                        self.what_to_extract, region, self.dicts_dir)
                    res.get_cand_data()
                    res.get_elections_results()
                    res.complete_the_data(region, condition)
                    CollectTheData.dump_the_data(res, self.output_dir, region)
                    for i in self.what_to_extract.keys():
                        self.cand_data[i] = self.cand_data[i].append(res.cand_data[i])
                        self.data[i] = self.data[i].append(res.data[i])
        CollectTheData.dump_the_data(self, self.output_dir, "overall")

    def filter_elections(self, region, condition):  # add year at the end
        self.my_get(self.driver, self.regions_link[region])
        try:
            locate_page = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((
                By.XPATH, "//span[@class='filter']"
            )))
        except sel_exc.TimeoutException:
            input("Please enter smth: ")
            raise
        self.my_click(self.driver, locate_page)
        self.my_click(self.driver, self.driver.find_element_by_xpath("//button[@id='reset_btn']"))
        for i in self.dates.keys():
            elem = self.driver.find_element_by_xpath(f"//input[@id='{i}']")
            elem.clear()
            elem.send_keys(self.dates[i])
        input_boxes = self.driver.find_elements(By.XPATH,
                                                "//span[@class='select2-search select2-search--inline']")
        for i in range(len(input_boxes)):
            self.my_click(self.driver, input_boxes[i], wait=False, check_condition=False)
            options = self.driver.find_elements_by_xpath("//span[@class='select2-results']/*/li")
            needed_option = [opt for opt in options if opt.text == condition[i]][0]
            self.my_click(self.driver, needed_option, wait=False, check_condition=False)
            self.my_click(self.driver,
                          self.driver.find_elements_by_xpath("//button[@class='btn btn-primary']")[1],
                          wait=False, check_condition=False)
        self.my_click(self.driver, self.driver.find_element_by_xpath("//button[@type='submit']"),
                      wait=False, check_condition=False)

    #def gather_info_about_elections(self):
    #    self.my_click(self.driver, self.driver.find_element_by_xpath("//div[@class='main__menu']/div[2]/ul/div[1]/a"))
    #    self.my_click(self.driver, self.driver.find_element_by_xpath("//a[@id='election-results-name']"))
    #    menu_options = driver.find_elements_by_xpath("//div/div[9]/table/tbody/tr[@class='trReport']/td/a")


    @staticmethod
    def cartesian_product(*arrays):
        la = len(arrays)
        dtype = np.result_type(*arrays)
        arr = np.empty([len(a) for a in arrays] + [la], dtype=dtype)
        for i, a in enumerate(np.ix_(*arrays)):
            arr[..., i] = a
        return arr.reshape(-1, la)

    @staticmethod
    def my_get(driver, link):
        time.sleep(1)
        driver.get(link)
        CaptchaSolver(driver)
        time.sleep(1)
        return

    @staticmethod
    def my_click(driver, elem, check_condition=True, wait=True):
        if wait:
            time.sleep(1)
        if check_condition:
            elem.click()
            CaptchaSolver(driver)
        else:
            try:
                elem.click()
            except sel_exc.StaleElementReferenceException:
                return

    @staticmethod
    def dump_the_data(obj, output_dir, name):
        for i in ["prop_case", "maj_case"]:
            obj.cand_data[i].to_csv(f"{output_dir}{name}_cand_{i}.csv")
            obj.data[i].to_csv(f"{output_dir}{name}_{i}.csv")


class CaptchaSolver:  # отделить ту часть, которая непосредственно связана с решением капчи, от кода, взаимодействующего с браузером
    def __init__(self, driver):
        self.driver = driver
        self.solve_captcha()

    def solve_captcha(self):
        time.sleep(1)
        try:
            captcha = self.driver.find_element_by_xpath("//img[@id = 'captchaImg']")
            captcha.screenshot("D:/DZ/Python/Projects/Elections/captcha1.png")
            feature_matrix = self.get_the_numbers(num_of_captchas_start=1, num_of_captchas_end=1,
                                                  route_to_captchas="D:/DZ/Python/Projects/Elections/captcha")
            with open("D:/DZ/Python/Projects/Elections/model.pkl", "rb") as inp:
                model = pickle.load(inp)
            predictions = model.predict(feature_matrix)
            if len(predictions) != 5:
                breakpoint()
            input_field = self.driver.find_element_by_xpath("//input[@id='captcha']")
            input_field.send_keys("".join(map(str, predictions)))
            time.sleep(2)
            CollectTheData.my_click(self.driver,
                                    self.driver.find_element_by_xpath("//input[@id='send']"), check_condition=False)
            try:
                Alert(self.driver).accept()
                time.sleep(1)
                self.solve_captcha()
            except sel_exc.NoAlertPresentException:
                self.solve_captcha()
                return
        except sel_exc.NoSuchElementException:
            return

    def get_the_numbers(self, num_of_captchas_start, num_of_captchas_end, route_to_captchas):
        feature_matrix = pd.DataFrame()
        for digit in range(num_of_captchas_start, num_of_captchas_end + 1):
            name = str(digit) + r".png"
            pic = im.imread(route_to_captchas + name)
            a = np.array([])
            for i in range(pic.shape[0]):
                for j in range(pic.shape[1]):
                    a = np.append(a, sum(pic[i, j, 0:3]))
            a = a.reshape((50, 130))
            data_table = pd.DataFrame(a) - 357
            data_table[data_table > 0] = 0
            feature_matrix = feature_matrix.append(self.cut_columns(data_table))
        return feature_matrix

    def cut_columns(self, data):
        col_sums = data.sum(axis=0)
        num_columns = list()
        ind = 0
        count = 0
        prev_count = -1  # Проверить, пострадает ли функция при изменении на 0
        for i in range(data.shape[1] - 6):
            temp = abs(sum(col_sums[ind:(ind + 7)]))
            if temp > count:
                ind += 1
            elif prev_count < count:
                num_columns.append((ind - 1, ind + 6))
                ind += 1
            else:
                ind += 1
            prev_count = count
            count = temp
        columns_with_numbers = [data.iloc[:, (num_columns[i][0]):(num_columns[i][1])] for i in range(len(num_columns))]
        return self.cut_rows(columns_with_numbers)

    def cut_rows(self, data):
        num_rows = list()
        for table in data:
            rows_sums = table.sum(axis=1)
            ind = 0
            count = 0
            prev_count = 0
            for i in range(table.shape[0] - 9):
                temp = abs(sum(rows_sums[ind:(ind + 10)]))
                if temp > count:
                    ind += 1
                elif prev_count < count:
                    num_rows.append((ind - 1, ind + 9))
                    ind += 1
                else:
                    ind += 1
                prev_count = count
                count = temp
        numbers = [data[i].iloc[(num_rows[i][0]):(num_rows[i][1]), :] for i in range(len(data))]
        numbers_dataframe = pd.DataFrame()
        for digit in numbers:
            digit = digit.to_numpy().reshape(1, 70)
            numbers_dataframe = numbers_dataframe.append(pd.DataFrame(digit))
        return numbers_dataframe


class ElectionsPage:
    def __init__(self, driver, condition, elections, elections_link, what_to_extract, region, dicts_dir):
        self.driver = driver
        self.condition = condition
        self.elections = elections
        self.elections_link = elections_link
        self.what_to_extract = what_to_extract
        self.region = region
        self.dicts_dir = dicts_dir
        self.presence = {"maj_case": False, "prop_case": False}
        self.is_federal = True if condition[0] == "Федеральный" else False
        self.year = None
        self.path = None
        self.start_point = None
        self.cand_data = {i: pd.DataFrame() for i in self.what_to_extract.keys()}
        self.data = {i: pd.DataFrame() for i in self.what_to_extract.keys()}  # is there more beatiful way to create cont for data?

        with open("D:/DZ/Elections_database/Scripts_related_data/dicts/meta_data_dict.pkl", "rb") as inp:
            self.meta_data_dict = pickle.load(inp)

        self.gather_info_about_elections(elections_link)

    def gather_info_about_elections(self, elections_link):
        CollectTheData.my_get(self.driver, elections_link)
        CollectTheData.my_click(self.driver,
                                self.driver.find_element_by_xpath("//div[@class='main__menu']/div[2]/ul/div[1]/a"))
        self.year = self.driver.find_element_by_xpath(
            "//div[@id='election-info']/div/div[3]/div[2]/b").text.split(r".")[2]
        if self.is_federal:
            cik_region_name = self.driver.find_element_by_xpath("//div/ul/li[3]/a").text
            fed_number = "[" + [str(i + 1)
                                for i, z in
                                enumerate(
                                    [el.text for el in self.driver.find_elements_by_xpath("//div/ul/li/ul/li/a[2]")])
                                if z == cik_region_name][0] + "]"
            self.path = f"//div/ul/li/ul/li{fed_number}/ul/li"
            CollectTheData.my_get(self.driver,
                                  self.driver.find_element_by_xpath(
                                      f"//div/ul/li/ul/li{fed_number}/a[2]").get_attribute("href"))
        else:
            self.path = "//div/ul/li/ul/li"
        CollectTheData.my_click(self.driver, self.driver.find_element_by_xpath("//a[@id='election-results-name']"))
        menu_options = self.driver.find_elements_by_xpath("//div/div[9]/table/tbody/tr[@class='trReport']/td/a")
        if sum([True for i in [el.text for el in menu_options] if "единому" in i or "федеральному" in i]) > 0:
            self.presence["prop_case"] = True
        if sum([True for i in [el.text for el in menu_options] if "одномандат" in i]) > 0:
            self.presence["maj_case"] = True

    def get_cand_data(self):
            # Do we need this try statement?
            #try:
            #    CollectTheData.my_get(self.driver,
            #                          self.driver.find_element_by_xpath("//div/ul/li/a[2]").get_attribute("href"))
            #except sel_exc.NoSuchElementException:
            #    print("Didn't find overall button")
        CollectTheData.my_click(self.driver, self.driver.find_element_by_xpath("//a[@id='standard-reports-name']"))
        if self.what_to_extract["maj_case"] and self.presence["maj_case"]:
            CollectTheData.my_click(self.driver, self.driver.find_element_by_xpath("//a[@id='220-rep-dir-link']"))
            #CollectTheData.my_click(self.driver,
            #                        self.driver.find_element_by_xpath("//div[@id='jstree_demo_div']/ul/li/a[2]"))
            num_of_pages = int(self.driver.find_elements_by_xpath("//div[@class='pagin']/ul[1]/li")[-1].text)
            maj_cand_data = pd.DataFrame()
            for i in range(num_of_pages):
                pages = self.driver.find_elements_by_xpath("//div[@class='pagin']/ul[1]/li")
                needed_num = [j for j, el in enumerate(pages) if int(el.text) == i+1][0]
                CollectTheData.my_click(self.driver, pages[needed_num])
                html = self.driver.page_source
                maj_cand_data = maj_cand_data.append(pd.read_html(html)[4].droplevel(0, 1).drop(
                    columns=["№ п/п", "Unnamed: 8_level_1", "Unnamed: 9_level_1", "Выдвижение"]).iloc[3:, :])
            maj_cand_data.rename(columns={"ФИО кандидата": "cand_names", "Дата рождения кандидата": "birth_dates",
                                          "Субьект выдвижения": "nom_subject", "Номер округа": "county_num",
                                          "Регистрация": "reg_status", "Избрание": "elec_status"}, inplace=True)
            maj_cand_data = maj_cand_data.astype({"county_num": "int"})
            maj_cand_data["reg_status"] = pd.Series(np.asarray(maj_cand_data["reg_status"]) == "зарегистрирован")
            maj_cand_data["elec_status"] = pd.isnull(maj_cand_data["elec_status"])
            self.cand_data["maj_case"] = maj_cand_data
        if self.what_to_extract["prop_case"] and self.presence["prop_case"]:
            CollectTheData.my_click(self.driver, self.driver.find_element_by_xpath("//a[@id='standard-reports-name']"))
            options = self.driver.find_elements_by_xpath("//div[@id='standard-reports']/table/tbody/tr/td/a")
            needed_option = [i for i, z in enumerate(options)
                             if z.text ==
                             "Список политических партий, их региональных отделений, принимающих участие в выборах"][0]
            needed_link = [el.get_attribute("href") for el in options][needed_option]
            CollectTheData.my_get(self.driver, needed_link)
            parties = self.driver.find_elements_by_xpath("//table[@id='politparty2']/tbody/tr/td[2]/form/a")
            parties_name = [el.text for el in parties]
            num_of_parties = len(parties)
            prop_cand_data = pd.DataFrame()
            for i in range(num_of_parties):
                CollectTheData.my_get(self.driver, needed_link)
                CollectTheData.my_click(self.driver, self.driver.find_elements_by_xpath(
                    "//table[@id='politparty2']/tbody/tr/td[2]/form/a")[i])
                if len(self.driver.find_elements_by_xpath("//table[@id='candidates-220-1']/tbody/tr")) < 2:
                    continue
                html = self.driver.page_source
                prop_cand_data = prop_cand_data.append(pd.read_html(html)[5].droplevel(0, 1).drop(
                    columns=["№ п/п", "Unnamed: 9_level_1", "Unnamed: 10_level_1", "выдвижение"]).iloc[3:, :])
                prop_cand_data["nom_subject"] = parties_name[i]
            prop_cand_data.rename(columns={"ФИО кандидата": "cand_names", "Дата рождения кандидата": "birth_dates",
                                           "регистрация": "reg_status", "избрание": "elec_status",
                                           "Номер региональной группы": "num_of_regional_group",
                                           "Общесубъектовая часть, региональная группа": "part_of_the_list",
                                           "Номер в общесубъектовой части, региональной группе": "num_in_the_part"},
                                  inplace=True)
            prop_cand_data = prop_cand_data.astype({"num_of_regional_group": "int", "num_in_the_part": "int"})
            prop_cand_data["reg_status"] = pd.Series(np.asarray(prop_cand_data["reg_status"]) == "зарегистрирован")
            prop_cand_data["elec_status"] = pd.isnull(np.asarray(prop_cand_data["elec_status"]) == "избр.")
            self.cand_data["prop_case"] = prop_cand_data

    def get_elections_results(self):
        temp_data = {i: pd.DataFrame() for i in self.what_to_extract.keys()}
        CollectTheData.my_click(self.driver, self.driver.find_element_by_xpath("//a[@id='election-results-name']"))
        menu_options = self.driver.find_elements_by_xpath("//tbody/tr[@class='trReport']/td/a")
        for i in self.what_to_extract.keys():
            if self.presence[i] and self.what_to_extract[i]:
                if i == "maj_case":
                    CollectTheData.my_click(self.driver, menu_options[[i for i, z in enumerate(
                        [el.text for el in menu_options]) if "Сводная" in z and "одномандат" in z][0]])
                else:
                    CollectTheData.my_click(self.driver, menu_options[[i for i, z in enumerate(
                        [el.text for el in menu_options]) if "Сводная" in z and (
                            "едином" in z or "федеральному" in z)][0]])
                counties_links = [county.get_attribute('href') for county in self.driver.find_elements_by_xpath(
                    self.path + "/a[2]"
                )]
                counties_text = [el.text for el in self.driver.find_elements_by_xpath(
                    self.path + "/a[2]")]
                if self.start_point is None:
                    self.get_the_start_point(counties_text)
                if self.start_point != 0 and i == "prop_case":
                    counties_links = [el.get_attribute("href") for el in self.driver.find_elements_by_xpath(
                        self.path + "ul/li/a[2]")]
                    counties_nums = list(range(len(counties_links)))
                    local_path = self.path + "ul/li/"
                else:
                    counties_nums = list(range(self.start_point, len(counties_text)))
                    local_path = self.path
                for county in counties_nums:
                    func_output = self.scrap_data_off_county_page(counties_links[county], local_path=local_path)
                    temp_data[i] = temp_data[i].append(self.clean_up_the_data(func_output, counties_text[county]))
                temp_data[i]["region"] = self.region
                temp_data[i].rename(columns=self.meta_data_dict, inplace=True)
                if "None" in temp_data[i].columns:
                    temp_data[i].drop(columns=["None"], inplace=True)
            self.data[i] = self.data[i].append(temp_data[i])

    def clean_up_the_data(self, df, name):
        with open("D:/DZ/Python/Projects/Elections/regions_dict.pkl", "rb") as inp:
            region_dict = pickle.load(inp)
        temp_list = [region_dict[j] for j in list(region_dict.keys()) if name == j]
        if len(temp_list) != 0:
            if len(temp_list) == 1:
                county_region = temp_list[0]
            else:
                county_region = None
                breakpoint()
        else:
            county_region = self.region
        df["county_region "] = county_region
        with open("D:/DZ/Elections_database/Scripts_related_data/dicts/meta_data_dict.pkl", "rb") as inp:
            meta_data_dict = pickle.load(inp)
        df.rename(columns=meta_data_dict, inplace=True)
        try:
            df.drop(columns=["None"], inplace=True)
        except KeyError:
            pass
        return df

    def get_the_start_point(self, counties_text):
        if len([i for i, z in enumerate(counties_text) if "Единый" in z]) > 0:
            self.start_point = 1
        else:
            self.start_point = 0

    def scrap_data_off_county_page(self, link, hyper_params=None, local_path=None):
        temp_data = pd.DataFrame()
        omittings = []
        hyper_name = None
        if local_path is None:
            local_path = self.path
        CollectTheData.my_get(self.driver, link)
        sub_counties = self.driver.find_elements_by_xpath(local_path + "/ul/li/a[1]")
        numbers_of_subcounties = [i for i, z in enumerate(sub_counties) if
                                  z.get_attribute("class") == "tree-close need-load"]
        if hyper_params is None:
            if len(self.driver.find_elements_by_xpath(
                    "//table[@id='fix-columns-table']/tbody/tr/td[2]")) != 0:
                hyper_name = "maj"
            elif len(self.driver.find_elements_by_xpath(
                    "//tr[@class='text-left']/td[2]/div/table/tbody/tr/td")) != 0:
                hyper_name = "prop"
            try:
                with open("D:/DZ/Elections_database/Scripts_related_data/dicts/hyper_params_" + hyper_name + r".pkl",
                          "rb") as inp:
                    hyper_params = pickle.load(inp)
            except TypeError:
                if len(numbers_of_subcounties) == 0 and self.driver.find_element_by_xpath(
                        "//div[@class='col']").text == r"Нет данных для построения отчета.":
                    print("Can't found the data")
                    return
                else:
                    raise sel_exc.NoSuchElementException("Can't found the data")
        try:
            self.driver.find_element_by_xpath(hyper_params["result"] + "[2]")
        except sel_exc.NoSuchElementException:
            temp_value = False
            breakpoint()
        else:
            temp_value = True
        if temp_value:
            omittings = self.verify_omitting(numbers_of_subcounties, hyperparams=hyper_params)
        if len(omittings) == len(sub_counties):
            pass
        else:
            html = self.driver.page_source
            temp_data = pd.read_html(html)[hyper_params["table_num"]].drop(columns=hyper_params["columns_to_drop"])
            if hyper_params["beforehand_del"]:
                temp_data["Unnamed: 1"] = pd.read_html(html)[5].iloc[2:len(temp_data)+2, 1].reset_index(drop=True)
            temp_data.set_index("Unnamed: 1", inplace=True)
            temp_data = temp_data.transpose().reset_index(drop=False).rename(columns={"index": "uik"})
            if np.nan in temp_data.columns:
                temp_data.drop(columns=[np.nan], inplace=True)
            # common var for a region-time
            index_of_neuchtennyh_row = [
                i for i, z in enumerate(temp_data.columns) if "не учтенных" in z or "неучтенных" in z
                                                              or "не учтённых" in z
                                                              or "число утраченных" in z.lower()]
            temp_data = temp_data.melt(id_vars=temp_data.columns[:index_of_neuchtennyh_row[-1] + 1],
                                       var_name="participant", value_name="votes")
            try:
                temp_data.votes = temp_data.votes.str.split(n=1, expand=True).iloc[:, 0].astype(dtype="int64")
            except AttributeError:
                pass
        if len(numbers_of_subcounties) == 0:
            if len(numbers_of_subcounties) == len(sub_counties):
                raise ValueError
            else:
                return temp_data
        links = np.array([el.get_attribute("href") for
                          el in self.driver.find_elements_by_xpath(local_path + "/ul/li/a[2]")])[
            numbers_of_subcounties]
        for sub in links:
            temp_data = temp_data.append(self.scrap_data_off_county_page(sub, hyper_params, local_path + "/ul/li"))
        return temp_data

    def verify_omitting(self, numbers, hyperparams):
        true_numbers = []
        uiks_and_subcounties = [el.text for el in self.driver.find_elements_by_xpath(hyperparams["uik"])]
        for i in range(len(uiks_and_subcounties)):
            if "уик" not in uiks_and_subcounties[i] and i in numbers:
                true_numbers.append(i)
        return true_numbers

    def complete_the_data(self, region, condition):
        self.cand_data["prop_case"], self.cand_data["maj_case"], self.data["prop_case"] = self.convert_party_names(
            data=[[self.cand_data["prop_case"], "nom_subject"], [self.cand_data["maj_case"], "nom_subject"],
                  [self.data["prop_case"], "participant"]])
        for i in ["prop_case", "maj_case"]:
            self.cand_data[i]["region"] = region
            self.cand_data[i]["level"], self.cand_data[i]["kind"] = condition[0], condition[1]
            self.cand_data[i]["type_of_elections"], self.cand_data[i]["electoral_system"] = condition[2], condition[3]
            self.data[i]["region"] = region
            self.data[i]["level"], self.data[i]["kind"] = condition[0], condition[1]
            self.data[i]["type_of_elections"], self.data[i]["electoral_system"] = condition[2], condition[3]

    #def dump_the_data(self, output_dir):
    #    self.cand_data["prop_case"], self.cand_data["maj_case"], self.data["prop_cse"] = self.convert_party_names(
    #        data=[(self.cand_data["prop_case"], "nom_subject"), (self.cand_data["maj_case"], "nom_subject"),
    #              (self.data["prop_cse"], "participant")])
    #    for i in ["prop_case", "maj_case"]:
    #        self.cand_data[i].to_csv(output_dir + " cand" + i + r".csv")
    #        self.data[i].to_csv(output_dir + i + r".csv")

    def convert_party_names(self, data):
        for case in data:
            case[0] = self.find_aliases(case[0], case[1])
        return data[0][0], data[1][0], data[2][0]

    def find_aliases(self, data, col):
        if len(data) == 0:
            return data
        with open(self.dicts_dir + "party_names_dictionary.pkl", "rb") as inp:
            aliases_dictionary = pickle.load(inp)
        keys = list(aliases_dictionary.keys())
        names = data[col]
        for name in names:
            if name in list(aliases_dictionary.values()):
                continue
            alias_index = [i for i, z in enumerate(keys) if
                           z in name.lower().translate({ord("'"): None, ord('"'): None})]
            if len(alias_index) != 0:
                alias_index = alias_index[0]
                data.loc[data[col] == name, col] = aliases_dictionary[keys[alias_index]]
            else:
                inp_value = self.add_alias(aliases_dictionary, name)
                if inp_value == "None":
                    return self.find_aliases(data, col)
                else:
                    data.loc[data[col] == name, col] = inp_value
        return data

    def add_alias(self, aliases_dictionary, name):
        alias, value = input("Name is %s, enter alias and value with comma and space between them" % name).split(", ")
        if alias == "None" or value == "None":
            output = input("Value to insert")
            return output
        else:
            aliases_dictionary[alias] = value
            with open(self.dicts_dir + "party_names_dictionary.pkl", "wb") as outp:
                pickle.dump(aliases_dictionary, outp, pickle.HIGHEST_PROTOCOL)
            return "None"


if __name__ == "__main__":
    CollectTheData(dates={"start_date": "01.09.2019", "end_date": "01.01.2020"},
                   regions=["Кабардино-Балкарская Республика"],
                   conditions={"level": np.array(["Региональный"]), "kind": np.array(["Выборы депутата"]),
                               "type_of_elections": np.array(["Основные"])},
                   driver_loc="D:/DZ/Python/Driver/chromedriver.exe",
                   output_dir="D:/DZ/Elections_database/data/Web_Scraping_Data/OOP_testing/",
                   what_to_extract={"maj_case": True, "prop_case": True})
