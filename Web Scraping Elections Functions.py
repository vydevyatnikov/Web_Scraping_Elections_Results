import pandas as pd
import numpy as np
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as sel_exc
from selenium.webdriver.common.alert import Alert
from time import sleep as tms
from itertools import compress, repeat
import pickle
from Test import get_the_numbers
import traceback


def undo(conditions, driver):
    input_boxes = driver.find_elements(By.XPATH, "//span[@class='select2-search select2-search--inline']")
    for i in range(4):
        if conditions[i] is None:
            continue
        my_click(input_boxes[i], driver)
        for j in driver.find_elements_by_xpath(  # оптимизировать, чтобы не прогонять по selectoram, где value = None
                "//span[@class='select2-container select2-container--default select2-container--open']/*/*/*/li"):
            if j.text in conditions[i]:
                my_click(j, driver)
        my_click(driver.find_element_by_xpath(
            "//div[@class='select2-link2 select2-close']/button[@class='btn btn-primary']"
        ), driver)


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
            if len(alias_index) >= 2:
                input("Two or more elements in alias_index")
                breakpoint()
            alias_index = alias_index[0]
            data_frame.loc[data_frame.party_names == name, "party_names"] = aliases_dictionary[keys[alias_index]]
        else:
            add_alias(aliases_dictionary, name)
            return convert_party_names(data_frame, column_with_names)
    return data_frame


def my_click(elem, driver, check_condition=True):  # add captcha num and driver
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
            raise exceptions[2][0]
        else:
            otp = globals()[function_name](**args)
    except Exception as excp:
        otp = automatic_restart(function_name, args, err+1, exceptions.append((excp, excp.__traceback__)))
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
    full_set_of_possible_conditions = {"level": ["Административный центр", "Местное самоуправление",
                                                 "Федеральный", "Региональный"],
                                       "kind": ["Референдум", "Выборы на должность", "Выборы депутата",
                                                "Отзыв депутат", "Отзыв должностного лица"],
                                       "type_of_elections": ["Основные", "Основные повторные", "Основные отложенные",
                                                             "Основные отдельные", "Дополнительные",
                                                             "Дополнительные повторные", "Довыборы",
                                                             "Повторное голосование",
                                                             "Основные выборы и повторное голосование"],
                                       "electoral_system": ["Мажоритарная",
                                                            "Мажоритарная - по общерегиональному округу и по отдельным "
                                                            "избирательным округам",
                                                            "Мажоритарная по общенациональному округу",
                                                            "Пропорциональная",
                                                            "Смешанная - пропорциональная и мажоритарная",
                                                            "Пропорциональная и мажоритраная по общенациональному "
                                                            "округу и отдельным избирательным округам"]}
    if driver_loc is None:
        driver = Firefox()
    else:
        driver = Firefox(executable_path=driver_loc)
    final_data = {i: pd.DataFrame() for i in list(what_to_extract.keys())}
    if regions_to_collect == "every":
        regions = list(region_link.keys())
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
        if regions is not list and regions_to_collect != "every":
            regions = [regions]
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
                                                             "undo_conditions": undo_conditions},
                                                       err=0,
                                                       exceptions=[])
                            undo_conditions = [lvl, k, t, elec_system]
                            if output["maj_data"].shape[0] != 0:
                                output["maj_data"]["region"] = pd.Series(repeat(i, output["maj_data"].shape[0]))
                                output["maj_data"]["level"] = pd.Series(repeat(lvl, output["maj_data"].shape[0]))
                                output["maj_data"]["kind"] = pd.Series(repeat(k, output["maj_data"].shape[0]))
                                output["maj_data"]["type"] = pd.Series(repeat(t, output["maj_data"].shape[0]))
                                output["maj_data"]["elec_system"] = pd.Series(repeat(elec_system,
                                                                                     output["maj_data"].shape[0]))
                                final_data["maj_data"] = final_data["maj_data"].append(output["maj_data"])
                            if output["prop_data"].shape[0] != 0:
                                output["prop_data"]["region"] = pd.Series(repeat(i, output["prop_data"].shape[0]))
                                output["prop_data"]["level"] = pd.Series(repeat(lvl, output["prop_data"].shape[0]))
                                output["prop_data"]["kind"] = pd.Series(repeat(k, output["prop_data"].shape[0]))
                                output["prop_data"]["type"] = pd.Series(repeat(t, output["prop_data"].shape[0]))
                                output["prop_data"]["elec_system"] = pd.Series(repeat(elec_system,
                                                                                      output["prop_data"].shape[0]))
                                final_data["prop_data"] = final_data["prop_data"].append(output["prop_data"])
            #final_data["maj_data"].to_csv(output_dir + "/Intermediate_results/" + i + "_maj.csv", index_label=False)
            #final_data["prop_data"].to_csv(output_dir + "/Intermediate_results/" + i + "_prop.csv", index_label=False)
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
                final_data["prop_data"].to_csv(output_dir + "/" + name_of_prop_file + r".csv", index_label=False)
            if final_data["maj_data"].shape[0] != 0:
                name_of_maj_file = input("Enter name of file for data on majoritarian system results")
                final_data["maj_data"].to_csv(output_dir + "/" + name_of_maj_file + r".csv", index_label=False)


def region_elections(link, dates, conditions, driver, what_to_extract, is_federal, undo_conditions):
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
        if conditions[i] is None:
            continue
        my_click(input_boxes[i], driver)
        for j in driver.find_elements_by_xpath(  # оптимизировать, чтобы не прогонять по selectoram, где value = None
                "//span[@class='select2-container select2-container--default select2-container--open']/*/*/*/li"):
            if j.text == conditions[i]:
                my_click(j, driver)
        my_click(driver.find_element_by_xpath(
            "//div[@class='select2-link2 select2-close']/button[@class='btn btn-primary']"
        ), driver)
    my_click(driver.find_element_by_xpath("//button[@id='calendar-btn-search']"), driver)
    vibory_elements = driver.find_elements_by_xpath("//a[@class='viboryLink']")
    vibory_links = [el.get_attribute("href") for el in vibory_elements]
    vibory_texts = [el.text for el in vibory_elements]
    result_dict = {i: pd.DataFrame() for i in list(what_to_extract.keys())}
    if len(vibory_links) == 0:
        print("Can't found any elections")
        return result_dict
    for i in range(len(vibory_links)):
        my_get(driver, vibory_links[i])
        my_click(driver.find_element_by_xpath("//div[@class='main__menu']/div[2]/ul/div[1]/a"), driver)
        year = driver.find_element_by_xpath("//div[@id='election-info']/div/div[3]/div[2]/b").text.split(r".")[2]
        my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
        menu_options = driver.find_elements_by_xpath("//tbody/tr[@class='trReport']/td/a")
        if what_to_extract["maj_data"]:  # call for another function (maj case or prop case or smth)
            maj_data = automatic_restart(function_name="maj_case",
                                         args={"driver": driver,
                                               "what_to_extract": what_to_extract,
                                               "is_federal": is_federal},
                                         err=0,
                                         exceptions=[])
            if maj_data is not None:
                maj_data["year"] = pd.Series(repeat(year, len(maj_data.iloc[:, 0])))
                maj_data["name_of_elections"] = pd.Series(repeat(vibory_texts[i], len(maj_data.iloc[:, 0])))
                result_dict["maj_data"] = result_dict["maj_data"].append(maj_data)
        if what_to_extract["prop_data"]:
            prop_data = automatic_restart(function_name="prop_case",
                                          args={"driver": driver,
                                                "what_to_extract": what_to_extract,
                                                "is_federal": is_federal},
                                          err=0,
                                          exceptions=[])
            if prop_data is not None:
                prop_data["year"] = pd.Series(repeat(year, len(prop_data.iloc[:, 0])))
                prop_data["name_of_elections"] = pd.Series(repeat(vibory_texts[i], len(prop_data.iloc[:, 0])))
                result_dict["prop_data"] = result_dict["prop_data"].append(prop_data)
        # Два идентичных if, можно сократить запись?
    return result_dict


def maj_case(driver, what_to_extract, is_federal):  # with uik's
    if is_federal:
        region = driver.find_element_by_xpath("//div/ul/li[3]/a").text
        fed_number = "[" + [str(i + 1)
                            for i, z in
                            enumerate(
                                [el.text for el in driver.find_elements_by_xpath("//div/ul/li/ul/li/a[2]")])
                            if z == region][0] + "]"
        path = f"//div/ul/li/ul/li{fed_number}/ul/li"
        my_get(driver, driver.find_element_by_xpath(f"//div/ul/li/ul/li{fed_number}/a[2]").get_attribute("href"))
    else:
        path = "//div/ul/li/ul/li"
    my_click(driver.find_element_by_xpath("//a[@id='standard-reports-name']"), driver)  # independent
    try:
        my_click(driver.find_element_by_xpath("//a[@id='220-rep-dir-link']"), driver)  # dependent.
    except sel_exc.NoSuchElementException:
        input("No info about maj_case")
        return None
    # В ссылка содержится информация о том, из какого меню мы их открыли, поэтому для разных целей нужны разные
    # counties_links
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
                    cand_names = pd.Series(
                        [el.text for el in driver.find_elements_by_xpath(  # можно оптимизировать: 3 к ряду
                            "//tbody[@valign='top']/tr/td[2]"
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
                    data_info = data_info.append(pd.DataFrame({"cand_names": cand_names, "nom_subject": nom_subject,
                                                               "county_num": county_num, "county_names": county_names,
                                                               "reg_status": reg_status}))
            else:
                cand_names = pd.Series(
                    [el.text for el in driver.find_elements_by_xpath(  # можно оптимизировать: 3 к ряду
                        "//tbody[@valign='top']/tr/td[2]"
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
                data_info = data_info.append(pd.DataFrame({"cand_names": cand_names, "nom_subject": nom_subject,
                                                           "county_num": county_num, "county_names": county_names,
                                                           "reg_status": reg_status}))
    if len(links_to_delete) != 0:
        corrector = 0
        for i in links_to_delete:
            del counties_links[i-corrector]
            corrector += 1
    # brand new counties links
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    menu_options = driver.find_elements_by_xpath("//tbody/tr[@class='trReport']/td/a")
    my_click(menu_options[[i for i, z in enumerate([el.text for el in menu_options])
                           if "Сводная" in z and "одномандат" in z][0]], driver)
    counties_links = [county.get_attribute('href') for county in driver.find_elements_by_xpath(
        path + "/a[2]"
    )]
    # got new brand new counties links, wow
    data = pd.DataFrame()
    for i in range(start_point, len(counties_links)):
        my_get(driver, counties_links[i])
        sub_counties = driver.find_elements_by_xpath(path + f"[{i+1}]/ul/li/a[1]")
        numbers_of_subcounties = [i for i, z in enumerate(sub_counties) if
                                  z.get_attribute("class") == "tree-close need-load"]
        if len(numbers_of_subcounties) != len(sub_counties):
            data = data.append(get_the_data(driver, "cand_names", what_to_extract, omit=numbers_of_subcounties))
        if len(numbers_of_subcounties) != 0:
            # real_counties_links = counties_links[i]
            for j in numbers_of_subcounties:
                my_get(driver, driver.find_element_by_xpath(path + f"[{i+1}]/ul/li[{j+1}]/a[2]").get_attribute("href"))
                sub_sub_counties = driver.find_elements_by_xpath(path + f"[{i+1}]/ul/li[{j+1}]" + "/ul/li/a[1]")
                numbers_of_sub_subcounties = [i for i, z in enumerate(sub_sub_counties) if
                                              z.get_attribute("class") == "tree-close need-load"]
                if len(numbers_of_sub_subcounties) != len(sub_sub_counties):
                    data = data.append(get_the_data(driver, "cand_names", what_to_extract,
                                                    omit=numbers_of_sub_subcounties))
                if len(numbers_of_sub_subcounties) != 0:
                    for k in numbers_of_sub_subcounties:
                        my_get(driver, driver.find_element_by_xpath(
                            path + f"[{i+1}]/ul/li[{j+1}]/ul/li[{k+1}]/a[2]").get_attribute("href"))
                        data = data.append(get_the_data(driver, "cand_names", what_to_extract, omit=[]))
    if not what_to_extract["uiks_numbers_only"]:
        final_dataset = pd.merge(data, data_info, on="cand_names", how="inner")
    else:
        final_dataset = data
    # final_dataset.to_csv("test.csv", index_label=False)
    return final_dataset


def prop_case(driver, what_to_extract, is_federal):
    if is_federal:
        region = driver.find_element_by_xpath("//div/ul/li[3]/a").text
        fed_number = "[" + [str(i + 1)
                            for i, z in
                            enumerate(
                                [el.text for el in driver.find_elements_by_xpath("//div/ul/li/ul/li/a[2]")])
                            if z == region][0] + "]"
        path = f"//div/ul/li/ul/li{fed_number}/ul/li"
        my_get(driver, driver.find_element_by_xpath(f"//div/ul/li/ul/li{fed_number}/a[2]").get_attribute("href"))
    else:
        path = "//div/ul/li/ul/li"
        my_get(driver, driver.find_element_by_xpath("//div/ul/li/a[2]").get_attribute("href"))
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    reports_options = driver.find_elements_by_xpath("//div[@id='election-results']/table/tbody/tr/td/a")
    reports_options_text = [el.text for el in reports_options]
    try:
        reports_options[[i for i, z in enumerate(reports_options_text) if
                         "Сводная" in z and ("единому" in z or "федеральному" in z)][0]]
    except IndexError:
        input("No info about prop_case")
        return None
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    # my_get(driver, driver.find_element_by_xpath("//div/ul/li/a[2]").get_attribute("href"))
    data_info = pd.DataFrame()
    if not what_to_extract["uiks_numbers_only"]:
        my_click(driver.find_element_by_xpath("//a[@id='standard-reports-name']"), driver)
        reports_options = [i for i in
                           driver.find_elements_by_xpath("//div[@id='standard-reports']/table/tbody/tr/td/a")]
        reports_options_text = [el.text for el in reports_options]
        my_click(reports_options[[
            i for i, z in enumerate(reports_options_text) if "Список" in z and "принимающих" in z][0]], driver)
        data_info = data_info.append(pd.DataFrame({"party_names": [el.text for el in driver.find_elements_by_xpath(
            "//table[@id='politparty2']/tbody/tr/td[2]/form/a")]}))
    my_click(driver.find_element_by_xpath("//a[@id='election-results-name']"), driver)
    menu_options = driver.find_elements_by_xpath("//div[@id='election-results']/table/tbody/tr/td/a")
    menu_options_text = [el.text for el in driver.find_elements_by_xpath(
        "//div[@id='election-results']/table/tbody/tr/td/a")]
    my_click(menu_options[[i for i, z in enumerate(menu_options_text)
                           if "Сводная" in z and ("едином" in z or "федеральному" in z)][0]], driver)
    counties_text = [el.text for el in driver.find_elements_by_xpath(
        path + "/a[2]")]
    if len([i for i, z in enumerate(counties_text) if "Единый" in z]) > 0:
        counties_links = [el.get_attribute("href") for el in driver.find_elements_by_xpath(
            path + "[1]/ul/li/a[2]")]
        path = path + "[1]/ul/li"
    else:
        counties_links = [el.get_attribute("href") for el in driver.find_elements_by_xpath(path + "/a[2]")]
    data = pd.DataFrame()
    for i in range(len(counties_links)):
        my_get(driver, counties_links[i])
        sub_counties = driver.find_elements_by_xpath(path + f"[{i + 1}]/ul/li/a[1]")
        numbers_of_subcounties = [i for i, z in enumerate(sub_counties) if
                                  z.get_attribute("class") == "tree-close need-load"]
        if len(numbers_of_subcounties) != len(sub_counties):
            data = data.append(get_the_data(driver, "party_names", what_to_extract, omit=numbers_of_subcounties))
        if len(numbers_of_subcounties) != 0:
            # real_counties_links = counties_links[i]
            for j in numbers_of_subcounties:
                my_get(driver, driver.find_element_by_xpath(path + f"[{i + 1}]/ul/li[{j + 1}]/a[2]").get_attribute("href"))
                sub_sub_counties = driver.find_elements_by_xpath(path + f"[{i + 1}]/ul/li[{j + 1}]" + "/ul/li/a[1]")
                numbers_of_sub_subcounties = [i for i, z in enumerate(sub_sub_counties) if
                                              z.get_attribute("class") == "tree-close need-load"]
                if len(numbers_of_sub_subcounties) != len(sub_sub_counties):
                    data = data.append(get_the_data(driver, "party_names", what_to_extract,
                                                    omit=numbers_of_sub_subcounties))
                if len(numbers_of_sub_subcounties) != 0:
                    for k in numbers_of_sub_subcounties:
                        my_get(driver, driver.find_element_by_xpath(
                            path + f"[{i + 1}]/ul/li[{j + 1}]/ul/li[{k + 1}]/a[2]").get_attribute("href"))
                        data = data.append(get_the_data(driver, "party_names", what_to_extract, omit=[]))
    # solution to party_names_problem
    if not what_to_extract["uiks_numbers_only"]:
        data_info = convert_party_names(data_info, "party_names")
        data = convert_party_names(data, "party_names")
        final_dataset = pd.merge(data, data_info, on="party_names", how="inner")
    else:
        final_dataset = data
    return final_dataset


def get_the_data(driver, name, what_to_extract, omit):
    data = pd.DataFrame()
    smth_names = pd.Series([el.text for el in driver.find_elements_by_xpath(
        "//table[@id='fix-columns-table']/tbody/tr/td[2]")])
    for j in gener(4, len(driver.find_elements_by_xpath("//table[@id='fix-columns-table']/thead/tr/th")), omit):
        uik_num = driver.find_element_by_xpath("//table[@id='fix-columns-table']/thead/tr/th[%s]" % j).text
        if what_to_extract["uiks_numbers_only"]:
            data = data.append(pd.DataFrame({"uik_num": pd.Series(uik_num)}))
            continue
        result = pd.Series(list(map(int, [el.text for el in driver.find_elements_by_xpath(
            "//table[@id='fix-columns-table']/tbody/tr/td[%s]/nobr/b" % j)])))
        uik_nums = pd.Series([uik_num for t in range(len(result))])
        came_to_ballotbox = result[[
            y for y, z in enumerate(smth_names) if "Число бюллетеней, содержащихся в" in z or "Число бюллетеней в" in z
                                                   or "Число избирательных бюллетеней, содержащихся в" in z
        ]].sum()
        num_of_registered_voters = int(result[[
            y for y, z in enumerate(smth_names) if "Число избирателей, внесенных в список" in z or
                                                   "Число избирателей, внесенных в списки" in z
        ]])
        came_to_ballotbox = pd.Series(repeat(came_to_ballotbox, len(result)))
        num_of_registered_voters = pd.Series(repeat(num_of_registered_voters, len(result)))
        data_dict = {"x": smth_names, "votes": result, "uik": uik_nums,
                     "came_to_ballotbox": came_to_ballotbox,
                     "num_of_registered_voters": num_of_registered_voters}
        data = data.append(pd.DataFrame(data_dict))
    if not what_to_extract["uiks_numbers_only"]:
        data = data.rename(columns={"x": name})
    return data


def gener(start_point, end_point, omit):
    temp = start_point
    while temp <= end_point:
        yield temp
        prev_temp = temp
        if len(omit) != 0:
            for i in omit:
                if temp == i - 1:
                    temp += 2
                    break
        if temp == prev_temp:
            temp += 1


if __name__ == "__main__":
    x = scrap_elections(
                        start_date="01.01.2021",
                        end_date="31.12.2021",
                        level=["Федеральный"],
                        kind=["Выборы депутата"],
                        what_to_extract={"maj_data": False, "prop_data": True, "uiks_numbers_only": True},
                        type_of_elections=["Основные"],
                        driver_loc="C:/Users/user/Desktop/DZ/Python/Driver/geckodriver.exe",
                        output_dir="C:/Users/user/Desktop/DZ/Python/Projects/Elections")
# Все conditions должны быть листами
