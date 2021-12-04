import pandas as pd
import numpy as np
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import selenium.common.exceptions as sel_exc
from selenium.webdriver.common.alert import Alert
from time import sleep as tms
from itertools import compress, repeat
import pickle
from Test import get_the_numbers
import traceback
import re


def undo(conditions, driver):
    input_boxes = driver.find_elements(By.XPATH, "//span[@class='select2-search select2-search--inline']")
    for i in range(4):
        if conditions[i] is None or conditions[i] == "not specified":
            continue
        my_click(input_boxes[i], driver, wait=False)
        for j in driver.find_elements_by_xpath(  # оптимизировать, чтобы не прогонять по selectoram, где value = None
                "//span[@class='select2-container select2-container--default select2-container--open']/*/*/*/li"):
            if j.text == conditions[i]:
                my_click(j, driver, wait=False)
        my_click(driver.find_element_by_xpath(
            "//div[@class='select2-link2 select2-close']/button[@class='btn btn-primary']"
        ), driver, wait=False)


def add_alias(aliases_dictionary, name):
    alias, value = input("Name is %s, enter alias and value with comma and space between them" % name).split(", ")
    aliases_dictionary[alias] = value
    with open("C:/Users/user/Desktop/DZ/Python/Projects/Elections/party_names_dictionary.pkl", "wb") as outp:
        pickle.dump(aliases_dictionary, outp, pickle.HIGHEST_PROTOCOL)


def convert_party_names(data_frame, column_with_names):
    with open("C:/Users/user/Desktop/DZ/Python/Projects/Elections/party_names_dictionary.pkl", "rb") as inp:
        aliases_dictionary = pickle.load(inp)
    keys = list(aliases_dictionary.keys())
    names = data_frame[column_with_names]
    index_of_neuchtennyh_row = [
        i for i, z in enumerate(names.unique()) if "не учтенных при получении" in z or "неучтенных при получении" in z or
                                          "не учтенных открепительных" in z]
    if len(index_of_neuchtennyh_row) > 0:
        unique_names = names.unique()[(max(index_of_neuchtennyh_row) + 1):]
    else:
        unique_names = names.unique()
    for name in unique_names:
        if name in list(aliases_dictionary.values()):
            continue
        alias_index = [i for i, z in enumerate(keys) if z in name.lower().translate({ord("'"): None, ord('"'): None})]
        if len(alias_index) != 0:
            #if len(alias_index) >= 2:
            #    input("Two or more elements in alias_index")
                #breakpoint()
            alias_index = alias_index[0]
            data_frame.loc[data_frame[column_with_names] == name,
                           column_with_names] = aliases_dictionary[keys[alias_index]]
        else:
            add_alias(aliases_dictionary, name)
            return convert_party_names(data_frame, column_with_names)
    return data_frame


def my_click(elem, driver, check_condition=True, wait=True):  # add captcha num and driver
    if wait:
        tms(2)
    if check_condition:
        elem.click()
        solve_captcha(driver)
    else:
        try:
            elem.click()
        except sel_exc.StaleElementReferenceException:
            return


def my_get(driver, link):
    tms(1)
    driver.get(link)
    solve_captcha(driver)
    tms(1)
    return


def collect_captchas(driver, captcha):
    rng = np.random.default_rng()
    captcha_num = 55
    while captcha_num < 101:
        name = str(captcha_num) + r".png"
        captcha.screenshot("C:/Users/user/Desktop/captchas/captcha" + name)
        input_field = driver.find_element_by_xpath("//input[@id='captcha']")
        input_field.send_keys("".join(map(str, rng.integers(0, 10, 5))))
        my_click(driver.find_element_by_xpath("//input[@id='send']"), driver, check_condition=False)
        captcha_num += 1
        tms(2)
    raise IndexError


def solve_captcha(driver):
    tms(1)
    try:
        captcha = driver.find_element_by_xpath("//img[@id = 'captchaImg']")
        captcha.screenshot("C:/Users/user/Desktop/DZ/Python/Projects/Elections/captcha1.png")
        feature_matrix = get_the_numbers(num_of_captchas_start=1, num_of_captchas_end=1,
                                         route_to_captchas="C:/Users/user/Desktop/DZ/Python/Projects/Elections/captcha")
        with open("C:/Users/user/Desktop/DZ/Python/Projects/Elections/model.pkl", "rb") as inp:
            model = pickle.load(inp)
        predictions = model.predict(feature_matrix)
        if len(predictions) > 5:
            breakpoint()
        input_field = driver.find_element_by_xpath("//input[@id='captcha']")
        input_field.send_keys("".join(map(str, predictions)))
        tms(2)
        my_click(driver.find_element_by_xpath("//input[@id='send']"), driver, check_condition=False)
        try:
            Alert(driver).accept()
            tms(1)
            solve_captcha(driver)
        except sel_exc.NoAlertPresentException:
            solve_captcha(driver)
            return
    except sel_exc.NoSuchElementException:
        return


def automatic_restart(function_name, args, err, exceptions):
    otp = None
    try:
        if err >= 3:
            for i in exceptions:
                print(i[0].__class__)
                traceback.print_tb(i[1])
                print("_________________________________")
            raise exceptions[2][0]
        else:
            otp = globals()[function_name](**args)
    except Exception as excp:
        if err >= 3:
            breakpoint()
            raise excp
        exceptions.append((excp, excp.__traceback__))
        otp = automatic_restart(function_name, args, err+1, exceptions)
    finally:
        return otp


def scrap_elections(start_date, end_date, what_to_extract, regions_to_collect="every", level=None, kind=None,
                    type_of_elections=None, electoral_system="Смешанная - пропорциональная и мажоритарная",
                    driver_loc=None, output_dir="C:/Users", start_from=None):  # Добавить опцию all для regions
    region_link = {'Москва': "http://www.moscow-city.vybory.izbirkom.ru/region/moscow-city",
                   "Московская область": "http://www.moscow-reg.vybory.izbirkom.ru/region/moscow-reg",
                   "Республика Алтай": "http://www.altai-rep.vybory.izbirkom.ru/region/altai-rep",
                   "Республика Адыгея": "http://www.adygei.vybory.izbirkom.ru/region/adygei",
                   "Республика Башкортостан": "http://www.bashkortostan.vybory.izbirkom.ru/region/bashkortostan",
                   "Республика Бурятия": "http://www.buriat.vybory.izbirkom.ru/region/buriat",
                   "Республика Дагестан": "http://www.dagestan.vybory.izbirkom.ru/region/dagestan",
                   "Республика Ингушетия": "http://www.ingush.vybory.izbirkom.ru/region/ingush",
                   "Кабардино-Балкарская Республика":
                       "http://www.kabardin-balkar.vybory.izbirkom.ru/region/kabardin-balkar",
                   "Республика Калмыкия": "http://www.kalmyk.vybory.izbirkom.ru/region/kalmyk",
                   "Карачаево-Черкесская Республика":
                       "http://www.karachaev-cherkess.vybory.izbirkom.ru/region/karachaev-cherkess/",
                   "Республика Карелия": "http://www.karel.vybory.izbirkom.ru/region/karel",
                   "Республика Коми": "http://www.komi.vybory.izbirkom.ru/region/komi",
                   "Республика Крым": "http://www.crimea.vybory.izbirkom.ru/region/crimea",
                   "Республика Марий Эл": "http://www.vybory.izbirkom.ru/region/mari-el",
                   "Республика Мордовия": "http://www.mordov.vybory.izbirkom.ru/region/mordov/",
                   "Республика Саха (Якутия)": "http://www.vybory.izbirkom.ru/region/yakut",
                   "Республика Северная Осетия - Алания":
                       "http://www.n-osset-alania.vybory.izbirkom.ru/region/n-osset-alania",
                   "Республика Татарстан": "http://www.tatarstan.vybory.izbirkom.ru/region/tatarstan",
                   "Республика Тыва": "http://www.tyva.vybory.izbirkom.ru/region/tyva",
                   "Удмуртская Республика": "http://www.udmurt.vybory.izbirkom.ru/region/udmurt",
                   "Республика Хакасия": "http://www.khakas.vybory.izbirkom.ru/region/khakas",
                   "Чеченская Республика": "http://www.chechen.vybory.izbirkom.ru/region/chechen",
                   "Чувашская Республика - Чувашия": "http://www.chuvash.vybory.izbirkom.ru/region/chuvash",
                   "Алтайский край": "http://www.altai-terr.vybory.izbirkom.ru/region/altai-terr",
                   "Забайкальский край": "http://zabkray.vybory.izbirkom.ru/region/zabkray",
                   "Камчатский край": "http://www.kamchatka-krai.vybory.izbirkom.ru/region/kamchatka-krai",
                   "Краснодарский край": "http://www.krasnodar.vybory.izbirkom.ru/region/krasnodar",
                   "Красноярский край": "http://www.krasnoyarsk.vybory.izbirkom.ru/region/krasnoyarsk/",
                   "Пермский край": "http://www.permkrai.vybory.izbirkom.ru/region/permkrai/",
                   "Приморский край": "http://www.primorsk.vybory.izbirkom.ru/region/primorsk",
                   "Ставропольский край": "http://www.stavropol.vybory.izbirkom.ru/region/stavropol/",
                   "Хабаровский край": "http://www.khabarovsk.vybory.izbirkom.ru/region/khabarovsk",
                   "Амурская область": "http://www.amur.vybory.izbirkom.ru/region/amur",
                   "Архангельская область": "http://www.arkhangelsk.vybory.izbirkom.ru/region/arkhangelsk",
                   "Астраханская область": "http://www.astrakhan.vybory.izbirkom.ru/region/astrakhan",
                   "Белгородская область": "http://www.belgorod.vybory.izbirkom.ru/region/belgorod/",
                   "Брянская область": "http://www.bryansk.vybory.izbirkom.ru/region/bryansk/",
                   "Владимирская область": "http://www.vladimir.vybory.izbirkom.ru/region/vladimir",
                   "Волгоградская область": "http://www.volgograd.vybory.izbirkom.ru/region/volgograd",
                   "Вологодская область": "http://www.vologod.vybory.izbirkom.ru/region/vologod",
                   "Воронежская область": "http://www.voronezh.vybory.izbirkom.ru/region/voronezh",
                   "Ивановская область": "http://www.vybory.izbirkom.ru/region/ivanovo",
                   "Иркутская область": "http://www.irkutsk.vybory.izbirkom.ru/region/irkutsk",
                   "Калининградская область": "http://www.kaliningrad.vybory.izbirkom.ru/region/kaliningrad",
                   "Калужская область": "http://www.kaluga.vybory.izbirkom.ru/region/kaluga/",
                   "Кемеровская область - Кузбасс": "http://www.kemerovo.vybory.izbirkom.ru/region/kemerovo",
                   "Кировская область": "http://www.kirov.vybory.izbirkom.ru/region/kirov",
                   "Костромская область": "http://www.kostroma.vybory.izbirkom.ru/region/kostroma/",
                   "Курганская область": "http://www.kurgan.vybory.izbirkom.ru/region/kurgan",
                   "Курская область": "http://www.kursk.vybory.izbirkom.ru/region/kursk/",
                   "Ленинградская область": "http://www.leningrad-reg.vybory.izbirkom.ru/region/leningrad-reg",
                   "Липецкая область": "http://www.lipetsk.vybory.izbirkom.ru/region/lipetsk",
                   "Магаданская область": "http://www.magadan.vybory.izbirkom.ru/region/magadan",
                   "Мурманская область": "http://www.murmansk.vybory.izbirkom.ru/region/murmansk",
                   "Нижегородская область": "http://www.nnov.vybory.izbirkom.ru/region/nnov",
                   "Новгородская область": "http://www.novgorod.vybory.izbirkom.ru/region/novgorod",
                   "Новосибирская область": "http://www.novosibirsk.vybory.izbirkom.ru/region/novosibirsk/",
                   "Омская область": "http://www.omsk.vybory.izbirkom.ru/region/omsk",
                   "Оренбургская область": "http://www.orenburg.vybory.izbirkom.ru/region/orenburg/",
                   "Орловская область": "http://www.orel.vybory.izbirkom.ru/region/orel",
                   "Пензенская область": "http://www.penza.vybory.izbirkom.ru/region/penza",
                   "Псковская область": "http://www.pskov.vybory.izbirkom.ru/region/pskov/",
                   "Ростовская область": "http://www.rostov.vybory.izbirkom.ru/region/rostov",
                   "Рязанская область": "http://www.ryazan.vybory.izbirkom.ru/region/ryazan",
                   "Самарская область": "http://www.samara.vybory.izbirkom.ru/region/samara",
                   "Саратовская область": "http://www.saratov.vybory.izbirkom.ru/region/saratov",
                   "Сахалинская область": "http://www.sakhalin.vybory.izbirkom.ru/region/sakhalin",
                   "Свердловская область": "http://www.sverdlovsk.vybory.izbirkom.ru/region/sverdlovsk",
                   "Смоленская область": "http://www.smolensk.vybory.izbirkom.ru/region/smolensk",
                   "Тамбовская область": "http://www.tambov.vybory.izbirkom.ru/region/tambov",
                   "Тверская область": "http://www.tver.vybory.izbirkom.ru/region/tver",
                   "Томская область": "http://www.tomsk.vybory.izbirkom.ru/region/tomsk",
                   "Тульская область": "http://www.tula.vybory.izbirkom.ru/region/tula",
                   "Тюменская область": "http://www.tyumen.vybory.izbirkom.ru/region/tyumen",
                   "Ульяновская область": "http://www.ulyanovsk.vybory.izbirkom.ru/region/ulyanovsk",
                   "Челябинская область": "http://www.chelyabinsk.vybory.izbirkom.ru/region/chelyabinsk",
                   "Ярославская область": "http://www.yaroslavl.vybory.izbirkom.ru/region/yaroslavl",
                   "Санкт-Петербург": "http://www.st-petersburg.vybory.izbirkom.ru/region/st-petersburg",
                   "Севастополь": "http://www.sevastopol.vybory.izbirkom.ru/region/sevastopol",
                   "Еврейская автономная область": "http://www.jewish-aut.vybory.izbirkom.ru/region/jewish-aut",
                   "Ненецкий АО": "http://www.nenetsk.vybory.izbirkom.ru/region/nenetsk",
                   "Ханты-Мансийский АО": "http://www.khantu-mansy.vybory.izbirkom.ru/region/khantu-mansy",
                   "Чукотский АО": "http://www.chukot.vybory.izbirkom.ru/region/chukot",
                   "Ямало-Ненецкий АО": "http://www.yamal-nenetsk.vybory.izbirkom.ru/region/yamal-nenetsk",
                   }
    full_set_of_possible_conditions = \
        {"level": ["Административный центр", "Местное самоуправление", "Федеральный", "Региональный"],
         "kind": ["Референдум", "Выборы на должность", "Выборы депутата", "Отзыв депутат", "Отзыв должностного лица"],
         "type_of_elections": ["Основные", "Основные повторные", "Основные отложенные", "Основные отдельные",
                               "Дополнительные", "Дополнительные повторные", "Довыборы", "Повторное голосование",
                               "Основные выборы и повторное голосование"],
         "electoral_system": ["Мажоритарная",
                              "Мажоритарная - по общерегиональному округу и по отдельным избирательным округам",
                              "Мажоритарная по общерегиональному округу", "Пропорциональная",
                              "Смешанная - пропорциональная и мажоритарная",
                              "Пропорциональная и мажоритарная по общерегиональному округу и отдельным избирательным округам"]}
    if driver_loc is None:
        driver = Firefox()
    else:
        driver = Firefox(executable_path=driver_loc)
    final_data = {i: pd.DataFrame() for i in list(what_to_extract.keys())}
    if regions_to_collect == "every":
        regions = list(region_link.keys())
    elif type(regions_to_collect) is not list:
        regions = [regions_to_collect]
    else:
        regions = regions_to_collect
    if start_from is not None:
        regions = regions[[i for i, z in enumerate(regions) if z in start_from][0]:]
    if type(electoral_system) == str:
        electoral_system = [electoral_system]
    try:
        dates = {"'start_date'": start_date, "'end_date'": end_date}  # двойные кавычки для @id
        conditions = {"level": level, "kind": kind, "type_of_elections": type_of_elections,
                      "electoral_system": electoral_system}
        for i in list(conditions.keys()):
            if conditions[i] is None:
                conditions[i] = full_set_of_possible_conditions[i]
        for i in regions:
            undo_conditions = None
            for lvl in conditions["level"]:
                if lvl == "Федеральный":
                    is_federal = True
                else:
                    is_federal = False
                for k in conditions["kind"]:
                    for t in conditions["type_of_elections"]:
                        for elec_system in conditions["electoral_system"]:
                            output = automatic_restart(function_name="region_elections",
                                                       args={"link": region_link[i],
                                                             "dates": dates,
                                                             "conditions": [lvl, k, t, elec_system],
                                                             "driver": driver, "what_to_extract": what_to_extract,
                                                             "is_federal": is_federal,
                                                             "undo_conditions": undo_conditions,
                                                             "region": i},
                                                       err=0,
                                                       exceptions=[])
                            undo_conditions = [lvl, k, t, elec_system]
                            if output["maj_data"].shape[0] != 0:
                                #output["maj_data"]["region"] = pd.Series(repeat(i, output["maj_data"].shape[0]))
                                output["maj_data"]["level"] = pd.Series(repeat(lvl, output["maj_data"].shape[0]))
                                output["maj_data"]["kind"] = pd.Series(repeat(k, output["maj_data"].shape[0]))
                                output["maj_data"]["type"] = pd.Series(repeat(t, output["maj_data"].shape[0]))
                                output["maj_data"]["elec_system"] = pd.Series(repeat(elec_system,
                                                                                     output["maj_data"].shape[0]))
                                final_data["maj_data"] = final_data["maj_data"].append(output["maj_data"])
                            if output["prop_data"].shape[0] != 0:
                                #output["prop_data"]["region"] = pd.Series(repeat(i, output["prop_data"].shape[0]))
                                output["prop_data"]["level"] = pd.Series(repeat(lvl, output["prop_data"].shape[0]))
                                output["prop_data"]["kind"] = pd.Series(repeat(k, output["prop_data"].shape[0]))
                                output["prop_data"]["type"] = pd.Series(repeat(t, output["prop_data"].shape[0]))
                                output["prop_data"]["elec_system"] = pd.Series(repeat(elec_system,
                                                                                      output["prop_data"].shape[0]))
                                final_data["prop_data"] = final_data["prop_data"].append(output["prop_data"])
            #final_data["maj_data"].to_csv(output_dir + "/Intermediate_results/" + i + "_maj.csv", index_label=False)
            final_data["maj_data"].to_csv("C:/Users/user/Desktop/DZ/Course_5/Курсовая/data/" + i + "_maj.csv",
                                          index_label=False)
            #final_data["prop_data"].to_csv(output_dir + "/Intermediate_results/" + i + "_prop.csv", index_label=False)
            final_data["prop_data"].to_csv("C:/Users/user/Desktop/DZ/Course_5/Курсовая/data/" + i + "_prop.csv",
                                           index_label=False)
    except Exception:
        input("Check webpage before it's closure")
        raise
    except KeyboardInterrupt:
        input("Check webpage before it's closure")
    finally:
        driver.quit()
        ans = input("Do you want to save results?")
        if ans == "Yes":
            if final_data["prop_data"].shape[0] != 0:
                name_of_prop_file = input("Enter name of file for data on proportional system results")
                final_data["prop_data"].to_csv(output_dir + "/" + name_of_prop_file + r".csv")
            if final_data["maj_data"].shape[0] != 0:
                name_of_maj_file = input("Enter name of file for data on majoritarian system results")
                final_data["maj_data"].to_csv(output_dir + "/" + name_of_maj_file + r".csv")


def region_elections(link, dates, conditions, driver, what_to_extract, is_federal, undo_conditions, region):
    my_get(driver, link)
    try:
        locate_page = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
            By.XPATH, "//span[@class='filter']"
        )))
    except sel_exc.TimeoutException:
        input("Please enter smth: ")
        raise
    my_click(locate_page, driver)
    for i in dates:
        elem = driver.find_element_by_xpath("//input[@id=%s]" % i)
        elem.clear()
        elem.send_keys(dates[i])
    if undo_conditions is not None:
        undo(undo_conditions, driver)
    input_boxes = driver.find_elements(By.XPATH, "//span[@class='select2-search select2-search--inline']")
    for i in range(4):
        if conditions[i] is None or conditions[i] == "not specified":
            continue
        my_click(input_boxes[i], driver, wait=False)
        for j in driver.find_elements_by_xpath(  # оптимизировать, чтобы не прогонять по selectoram, где value = None
                "//span[@class='select2-container select2-container--default select2-container--open']/*/*/*/li"):
            if j.text == conditions[i]:
                my_click(j, driver, wait=False)
        my_click(driver.find_element_by_xpath(
            "//div[@class='select2-link2 select2-close']/button[@class='btn btn-primary']"
        ), driver, wait=False)
    my_click(driver.find_element_by_xpath("//button[@id='calendar-btn-search']"), driver, wait=False)
    vibory_elements = driver.find_elements_by_xpath("//a[@class='viboryLink']")
    vibory_links = [el.get_attribute("href") for el in vibory_elements]
    vibory_texts = [el.text for el in vibory_elements]
    result_dict = {i: pd.DataFrame() for i in list(what_to_extract.keys())}
    if len(vibory_links) == 0:
        print("Can't found any elections")
        return result_dict
    for i in range(len(vibory_links)):  #range(len(vibory_links))
        my_get(driver, vibory_links[i])
        my_click(driver.find_element_by_xpath("//div[@class='main__menu']/div[2]/ul/div[1]/a"), driver)
        year = driver.find_element_by_xpath("//div[@id='election-info']/div/div[3]/div[2]/b").text.split(r".")[2]
        my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
        menu_options = driver.find_elements_by_xpath("//div/div[9]/table/tbody/tr[@class='trReport']/td/a")
        presence = {"maj_case": False, "prop_case": False}
        if sum([True for i in [el.text for el in menu_options] if "единому" in i]) > 0:
            presence["prop_case"] = True
        if sum([True for i in [el.text for el in menu_options] if "одномандат" in i]) > 0:
            presence["maj_case"] = True
        if what_to_extract["maj_data"] and presence["maj_case"]:  # call for another function (maj case or prop case or smth)
            maj_data = automatic_restart(function_name="maj_case",
                                         args={"driver": driver,
                                               "what_to_extract": what_to_extract,
                                               "is_federal": is_federal,
                                               "region": region},
                                         err=0,
                                         exceptions=[])
            if maj_data is not None:
                maj_data["year"] = pd.Series(repeat(year, len(maj_data.iloc[:, 0])))
                maj_data["name_of_elections"] = pd.Series(repeat(vibory_texts[i], len(maj_data.iloc[:, 0])))
                result_dict["maj_data"] = result_dict["maj_data"].append(maj_data)
        else:
            print("No info about maj_case")
        if what_to_extract["prop_data"] and presence["prop_case"]:
            prop_data = automatic_restart(function_name="prop_case",
                                          args={"driver": driver,
                                                "what_to_extract": what_to_extract,
                                                "is_federal": is_federal,
                                                "region": region},
                                          err=0,
                                          exceptions=[])
            if prop_data is not None:
                prop_data["year"] = pd.Series(repeat(year, len(prop_data.iloc[:, 0])))
                prop_data["name_of_elections"] = pd.Series(repeat(vibory_texts[i], len(prop_data.iloc[:, 0])))
                result_dict["prop_data"] = result_dict["prop_data"].append(prop_data)
        else:
            print("No info about prop_case")
        # Два идентичных if, можно сократить запись?
    return result_dict


def get_info_about_candidates_maj(driver, path, i):
    cand_names = pd.Series(
        [el.text for el in driver.find_elements_by_xpath(  # можно оптимизировать: 3 к ряду
            "//tbody[@valign='top']/tr/td[2]"
        )])
    birth_date = pd.Series(
        [el.text for el in driver.find_elements_by_xpath(  # можно оптимизировать: 3 к ряду
            "//tbody[@valign='top']/tr/td[3]"
        )])
    nom_subject = pd.Series([el.text for el in driver.find_elements_by_xpath(
        "//tbody[@valign='top']/tr/td[4]"
    )])
    county_num = pd.Series([el.text for el in driver.find_elements_by_xpath(
        "//tbody[@valign='top']/tr/td[5]"
    )])
    county_name = driver.find_element_by_xpath(path + f"[{i + 1}]/a[2]").text
    county_names = pd.Series([county_name for j in range(len(cand_names))])
    reg_status = pd.Series([True if el.text == "зарегистрирован" else False for el in
                            driver.find_elements_by_xpath("//tbody[@valign='top']/tr/td[7]")])
    elec_status = pd.Series([el.text if len(el.text) > 0 else np.NaN for
                             el in driver.find_elements_by_xpath("//tbody/tr/td[8]")])
    return pd.DataFrame({"cand_names": cand_names, "birth_data": birth_date, "nom_subject": nom_subject,
                         "county_num": county_num, "county_names": county_names, "reg_status": reg_status,
                         "electoral_status": elec_status})


def maj_case(driver, what_to_extract, is_federal, region):  # with uik's
    if is_federal:
        cik_region_name = driver.find_element_by_xpath("//div/ul/li[3]/a").text
        fed_number = "[" + [str(i + 1)
                            for i, z in
                            enumerate(
                                [el.text for el in driver.find_elements_by_xpath("//div/ul/li/ul/li/a[2]")])
                            if z == cik_region_name][0] + "]"
        path = f"//div/ul/li/ul/li{fed_number}/ul/li"
        my_get(driver, driver.find_element_by_xpath(f"//div/ul/li/ul/li{fed_number}/a[2]").get_attribute("href"))
    else:
        path = "//div/ul/li/ul/li"
    my_click(driver.find_element_by_xpath("//a[@id='standard-reports-name']"), driver)  # independent
    #try:
    #    my_click(driver.find_element_by_xpath("//a[@id='220-rep-dir-link']"), driver)  # dependent.
    #except sel_exc.NoSuchElementException:
    #if sum([True for i in
    #        driver.find_elements_by_xpath(
    #            "//table/tbody/tr[@class='tdReport']/td/a") if "одномандатным" in i.text]) == 0:
    #    input("No info about maj_case")
    #    return None
    # В ссылках содержится информация о том, из какого меню мы их открыли, поэтому для разных целей нужны разные
    # counties_links
    my_click(driver.find_element_by_xpath("//a[@id='220-rep-dir-link']"), driver)
    counties_links = [county.get_attribute('href') for county in driver.find_elements_by_xpath(
        path + "/a[2]"
    )]
    counties_text = [el.text for el in driver.find_elements_by_xpath(
        path + "/a[2]")]
    if len([i for i, z in enumerate(counties_text) if "Единый" in z]) > 0:
        start_point = 1
    else:
        start_point = 0
    data_info = pd.DataFrame()
    links_to_delete = []
    if not what_to_extract["uiks_numbers_only"]:
        for i in range(start_point, len(counties_links)):
            my_get(driver, counties_links[i])
            cand_names = pd.Series([el.text for el in driver.find_elements_by_xpath(  # можно оптимизировать: 3 к ряду
                "//tbody[@valign='top']/tr/td[2]"
            )])
            if len(cand_names) == 0:
                links_to_delete.append(i)
                temp_links = [el.get_attribute('href') for el in driver.find_elements_by_xpath(path + "/ul/li/a[2]")]
                counties_links = counties_links + temp_links
                for temp_link in temp_links:
                    my_get(driver, temp_link)
                    data_info = data_info.append(get_info_about_candidates_maj(driver, path, i))
            else:
                data_info = data_info.append(get_info_about_candidates_maj(driver, path, i))
        data_info = convert_party_names(data_info, "nom_subject")
        #if what_to_extract["electoral_results"]:
        #    return data_info
    if len(links_to_delete) != 0:
        for i in sorted(links_to_delete, reverse=True):
            del counties_links[i]
    # brand new counties links
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    menu_options = driver.find_elements_by_xpath("//tbody/tr[@class='trReport']/td/a")
    my_click(menu_options[[i for i, z in enumerate([el.text for el in menu_options])
                           if "Сводная" in z and "одномандат" in z][0]], driver)
    numbers = [i for i in range(start_point, len(driver.find_elements_by_xpath(path + "/a[2]")))]
    data = sub_counties_tricks(driver, numbers,
                               path=path,
                               what_to_extract=what_to_extract,
                               connector="cand_names",
                               region=region,
                               data_info=data_info)
    if not what_to_extract["uiks_numbers_only"]:
        final_dataset = pd.merge(data, data_info, on="cand_names", how="inner")
    else:
        final_dataset = data
    # final_dataset.to_csv("test.csv", index_label=False)
    return final_dataset


def prop_case(driver, what_to_extract, is_federal, region):
    if is_federal:
        cik_region_name = driver.find_element_by_xpath("//div/ul/li[3]/a").text
        fed_number = "[" + [str(i + 1)
                            for i, z in
                            enumerate(
                                [el.text for el in driver.find_elements_by_xpath("//div/ul/li/ul/li/a[2]")])
                            if z == cik_region_name][0] + "]"
        path = f"//div/ul/li/ul/li{fed_number}/ul/li"
        my_get(driver, driver.find_element_by_xpath(f"//div/ul/li/ul/li{fed_number}/a[2]").get_attribute("href"))
    else:
        path = "//div/ul/li/ul/li"
        my_get(driver, driver.find_element_by_xpath("//div/ul/li/a[2]").get_attribute("href"))
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    reports_options = driver.find_elements_by_xpath("//div[@id='election-results']/table/tbody/tr/td/a")
    reports_options_text = [el.text for el in reports_options]
    #try:
    #    reports_options[[i for i, z in enumerate(reports_options_text) if
    #                     "Сводная" in z and ("единому" in z or "федеральному" in z)][0]]
    #except IndexError:
    #    input("No info about prop_case")
    #    return None
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    # my_get(driver, driver.find_element_by_xpath("//div/ul/li/a[2]").get_attribute("href"))
    data_info = pd.DataFrame()
    if not what_to_extract["uiks_numbers_only"]:
        my_click(driver.find_element_by_xpath("//a[@id='standard-reports-name']"), driver)
        reports_options = [i for i in
                           driver.find_elements_by_xpath("//div[@id='standard-reports']/table/tbody/tr/td/a")]
        reports_options_text = [el.text for el in reports_options]
        # Electoral results______________
        my_click(reports_options[[
            i for i, z in enumerate(reports_options_text) if ("кандидатов" in z and "партиями" in z) or
                                                             (z == "Сведения о кандидатах")][0]], driver)
        pages = driver.find_elements_by_xpath("//div[@class='pagin']/ul[2]/li/a")
        last_box = pages[len(pages) - 1].get_attribute("href")
        pages_overall = int(last_box[(re.search("number=", last_box).span()[1]):]) + 1
        cand_data = pd.DataFrame()
        for i in range(1, pages_overall):
            if i != 1:
                pages = driver.find_elements_by_xpath("//div[@class='pagin']/ul[1]/li/a")
                links = [el.get_attribute("href") for el in pages]
                next_page = [j for j, z in enumerate(links) if type(z) is str and
                             int(z[re.search("number=", z).span()[1]:]) == i][0]
                my_click(pages[next_page], driver)
            else:
                pass
            party_cand_names = pd.Series([
                el.text for el in driver.find_elements_by_xpath("//tbody[@id='test']/tr/td[2]")])
            party = pd.Series([el.text for el in driver.find_elements_by_xpath("//tbody[@id='test']/tr/td[4]")])
            electoral_status = pd.Series([
                el.text if len(el.text) > 0 else np.NaN for el in
                driver.find_elements_by_xpath("//tbody[@id='test']/tr/td[10]")])
            cand_data = cand_data.append(pd.DataFrame({"party_cand_names": party_cand_names, "party_names": party,
                                                       "electoral_status": electoral_status}))
        cand_data = convert_party_names(cand_data, "party_names")
        cand_data.reset_index(drop=True, inplace=True)
        cand_data.drop(index=[i for i, z in enumerate(cand_data.electoral_status) if z is np.NaN], inplace=True)
        cand_data_2 = pd.DataFrame()
        for par in cand_data.party_names.unique():
            temp_data = cand_data.loc[cand_data.party_names == par]
            temp_var = list(zip(temp_data.party_cand_names, temp_data.electoral_status))
            cand_data_2 = cand_data_2.append(pd.DataFrame({"party_names": [par],
                                                           "electoral_status": [temp_var]}))
        # Electoral results______________
        my_click(driver.find_element_by_xpath("//a[@id='standard-reports-name']"), driver)
        reports_options = [i for i in
                           driver.find_elements_by_xpath("//div[@id='standard-reports']/table/tbody/tr/td/a")]
        reports_options_text = [el.text for el in reports_options]
        my_click(reports_options[[
            i for i, z in enumerate(reports_options_text) if "Список" in z and "принимающих" in z][0]], driver)
        data_info = data_info.append(pd.DataFrame({"party_names": [el.text for el in driver.find_elements_by_xpath(
            "//table[@id='politparty2']/tbody/tr/td[2]/form/a")],
                                                   "reg_status": [
                                                       el.text for el in driver.find_elements_by_xpath(
                                                           "//table/tbody/tr/td[6]")]}))
        data_info = convert_party_names(data_info, "party_names")
        data_info = pd.merge(data_info, cand_data_2, how="left", on="party_names")
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    menu_options = driver.find_elements_by_xpath("//div[@id='election-results']/table/tbody/tr/td/a")
    menu_options_text = [el.text for el in driver.find_elements_by_xpath(
        "//div[@id='election-results']/table/tbody/tr/td/a")]
    my_click(menu_options[[i for i, z in enumerate(menu_options_text)
                           if "Сводная" in z and ("едином" in z or "федеральному" in z)][0]], driver)
    counties_text = [el.text for el in driver.find_elements_by_xpath(
        path + "/a[2]")]
    if len([i for i, z in enumerate(counties_text) if "Единый" in z]) > 0:
        path = path + "[1]/ul/li"
    counties_links = [el.get_attribute("href") for el in driver.find_elements_by_xpath(path + "/a[2]")]
    #data = pd.DataFrame()
    numbers = [i for i, z in enumerate(driver.find_elements_by_xpath(path + "/a[2]"))]
    data = sub_counties_tricks(driver, numbers,
                               path=path,
                               what_to_extract=what_to_extract,
                               connector="party_names",
                               region=region,
                               data_info=data_info,
                               num_of_names=sum([True for i in data_info.reg_status if len(i) > 0]))
    # solution to party_names_problem
    if not what_to_extract["uiks_numbers_only"]:
        data = convert_party_names(data, "party_names")
        final_dataset = pd.merge(data, data_info, on="party_names", how="inner")
    else:
        final_dataset = data
    return final_dataset


def verify_omitting(driver, numbers):
    true_numbers = []
    for j in numbers:
        if "уик" not in driver.find_element_by_xpath(
                f"//table[@id='fix-columns-table']/thead/tr/th[{j+4}]").text.lower():
            true_numbers.append(j)
    return true_numbers


def sub_counties_tricks(driver, numbers, path, what_to_extract, connector, region, data_info, num_of_names=None):
    data = pd.DataFrame()
    for i in numbers:
        with open("C:/Users/user/Desktop/DZ/Python/Projects/Elections/regions_dict.pkl", "rb") as inp:
            region_dict = pickle.load(inp)
        web_elem = driver.find_element_by_xpath(path + f"[{i + 1}]/a[2]")
        #if web_elem.text == "Одинцовская городская № 2":
        #    breakpoint()
        temp_list = [region_dict[j] for j in list(region_dict.keys()) if web_elem.text == j]
        if len(temp_list) != 0:
            if len(temp_list) == 1:
                county_region = temp_list[0]
            else:
                county_region = None
                breakpoint()
        else:
            county_region = region
        my_get(driver, web_elem.get_attribute("href"))
        sub_sub_counties = driver.find_elements_by_xpath(path + f"[{i + 1}]" + "/ul/li/a[1]")
        numbers_of_sub_subcounties = [i for i, z in enumerate(sub_sub_counties) if
                                      z.get_attribute("class") == "tree-close need-load"]
        if len(numbers_of_sub_subcounties) != len(sub_sub_counties):
            omittings = verify_omitting(driver, numbers_of_sub_subcounties)
            try:
                temp_data = get_the_data(driver, connector, what_to_extract,
                                         omit=np.array(omittings) + 4, data_info=data_info, num_of_names=num_of_names)
            except sel_exc.NoSuchElementException as exception:
                if exception.args[0] == "Can't found the data":
                    continue
                else:
                    raise exception
            temp_data["region"] = pd.Series(repeat(county_region, len(temp_data.iloc[:, 0])))
            if what_to_extract["uiks_numbers_only"]:
                temp = driver.find_elements_by_xpath(path + f"[{i + 1}]" + "/ul/li")
                uiks_numbers = [temp[j].text for j in gener(0, len(sub_sub_counties)-1,
                                                            omit=np.array(omittings))]
                tvd = [temp[j].get_attribute("id") for j in gener(0, len(sub_sub_counties)-1,
                                                                  omit=np.array(omittings))]
                if len(tvd) != len(temp_data.iloc[:, 0]):
                    ind_to_remove = [i for i, z in enumerate(uiks_numbers) if z not in np.array(temp_data.uik_num)]
                    for ind in sorted(ind_to_remove, reverse=True):
                        del tvd[ind]
                temp_data["tvd"] = tvd
            data = data.append(temp_data)
        elif len(numbers_of_sub_subcounties) == 0:
            raise ValueError
        if len(numbers_of_sub_subcounties) != 0:
            data = data.append(sub_counties_tricks(driver, numbers_of_sub_subcounties,
                                                   path=path+f"[{i + 1}]/ul/li",
                                                   what_to_extract=what_to_extract,
                                                   connector=connector,
                                                   region=county_region,
                                                   data_info=data_info,
                                                   num_of_names=num_of_names))
    return data


def get_the_data(driver, name, what_to_extract, omit, data_info, num_of_names=None):
    with open("C:/Users/user/Desktop/DZ/Python/Projects/Elections/meta_data_dict.pkl", "rb") as inp:
        meta_data_dict = pickle.load(inp)
    names_start = 0
    data = pd.DataFrame()
    # test
    try:
        driver.find_element_by_xpath(
            "//table[@id='fix-columns-table']/tbody/tr/td[2]")
    except sel_exc.NoSuchElementException as exception:
        raise sel_exc.NoSuchElementException("Can't found the data")
    smth_names = [el.text for el in driver.find_elements_by_xpath(
        "//table[@id='fix-columns-table']/tbody/tr/td[2]")]
    if num_of_names is not None:
        names_start = len(smth_names) - num_of_names
    else:
        num_of_names = 0
    columns_to_delete = []
    for i in range(len(smth_names) - num_of_names):
        if smth_names[i] in list(data_info.iloc[:, 0]):
            names_start = i
            break
        elif smth_names[i] in list(meta_data_dict.keys()):
            if meta_data_dict[smth_names[i]] != "None":
                smth_names[i] = meta_data_dict[smth_names[i]]
            else:
                columns_to_delete.append(i)
        else:
            value = input(f"The name is {smth_names[i]}, enter the value")
            meta_data_dict[smth_names[i]] = value
            with open("C:/Users/user/Desktop/DZ/Python/Projects/Elections/meta_data_dict.pkl", "wb") as outp:
                pickle.dump(meta_data_dict, outp, pickle.HIGHEST_PROTOCOL)
            if value != "None":
                smth_names[i] = value
            else:
                columns_to_delete.append(i)
    names_start -= len(columns_to_delete)
    for i in sorted(columns_to_delete, reverse=True):
        del smth_names[i]
    for j in gener(4, len(driver.find_elements_by_xpath("//table[@id='fix-columns-table']/thead/tr/th")), omit):
        temp_data = pd.DataFrame()
        uik_num = driver.find_element_by_xpath("//table[@id='fix-columns-table']/thead/tr/th[%s]" % j).text
        if what_to_extract["uiks_numbers_only"]:
            data = data.append(pd.DataFrame({"uik_num": pd.Series(uik_num)}))
            continue
        result = list(map(int, [el.text for el in driver.find_elements_by_xpath(
            "//table[@id='fix-columns-table']/tbody/tr/td[%s]/nobr/b" % j)]))
        uik_nums = [uik_num for t in range(names_start, len(smth_names))]
        temp_data = temp_data.append(pd.DataFrame({
            "x": pd.Series(smth_names[names_start:]), "votes": pd.Series(result[names_start:]),
            "uik": pd.Series(uik_nums)}))
        for k in range(names_start):
            temp_data[smth_names[k]] = pd.Series(repeat(result[k], len(smth_names) - names_start))
        data = data.append(temp_data)
    if not what_to_extract["uiks_numbers_only"]:
        data = data.rename(columns={"x": name})
    return data


def gener(start_point, end_point, omit):  # generates numbers from start_point to end_point including the end_point
    temp = start_point
    while temp <= end_point:
        if temp in omit:
            temp += 1
            continue
        else:
            yield temp
            temp += 1


if __name__ == "__main__":
    x = scrap_elections(regions_to_collect=["Республика Коми", "Белгородская область", "Воронежская область",
                                            "Калужская область", "Костромская область", "Курганская область",
                                            "Магаданская область", "Новосибирская область", "Рязанская область",
                                            "Челябинская область", "Ямало-Ненецкий АО"],
                        start_from="Калужская область",
                        start_date="01.01.2020",
                        end_date="01.01.2021",
                        level=["Региональный"],
                        kind=["Выборы депутата"],
                        what_to_extract={"maj_data": False, "prop_data": True, "uiks_numbers_only": False,
                                         "electoral_results": True},
                        type_of_elections=["Основные"],
                        driver_loc="C:/Users/user/Desktop/DZ/Python/Driver/geckodriver.exe",
                        output_dir="C:/Users/user/Desktop/DZ/Course_5/Курсовая/data",
                        electoral_system=None)
# Все conditions должны быть листами
