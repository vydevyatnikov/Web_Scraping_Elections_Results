import pandas as pd
import numpy as np
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as sel_exc
from time import sleep as tms
from itertools import compress, repeat


region_link = {'Москва': "http://www.moscow-city.vybory.izbirkom.ru/region/moscow-city",
               "Московская область": "http://www.moscow-reg.vybory.izbirkom.ru/region/moscow-reg"}


def scrap_elections(regions, start_date, end_date, level, kind=None, type_of_elections=None,
                    electoral_system=None, driver_loc=None, maj=True, prop=True, output_dir="C:/Users"):
    if driver_loc is None:
        driver = Firefox()
    else:
        driver = Firefox(executable_path=driver_loc)
    final_maj_data, final_prop_data = pd.DataFrame(), pd.DataFrame()
    try:
        dates = {"'start_date'": start_date, "'end_date'": end_date}  # двойные кавычки для @id
        conditions = [level, kind, type_of_elections, electoral_system]
        what_to_extract = {"maj": maj, "prop": prop}
        if regions is not list:
            regions = [regions]
        for i in regions:
            maj_data, prop_data = region_elections(region_link[i], dates, conditions, driver, what_to_extract)  # разобраться с тем, что выдает эта функция
            if maj_data.shape[0] != 0:
                maj_data["region"] = pd.Series(repeat(i, maj_data.shape[0]))
                final_maj_data = final_maj_data.append(maj_data)
            if prop_data.shape[0] != 0:
                prop_data["region"] = pd.Series(repeat(i, prop_data.shape[0]))
                final_prop_data = final_prop_data.append(prop_data)
            # add region column
    except Exception as inst:
        input("Exception class: ")
        raise
    finally:
        driver.quit()
        if final_prop_data.shape[0] != 0:
            final_prop_data.to_csv(output_dir + "/final_prop_data.csv", index_label=False)
        if final_maj_data.shape[0] != 0:
            final_maj_data.to_csv(output_dir + "/final_maj_data.csv", index_label=False)


def region_elections(link, dates, conditions, driver, what_to_extract):
    driver.get(link)  # возможно, что в некторых случаях страница не успевает загрузиться
    try:
        locate_page = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
            By.XPATH, "//span[@class='filter']"
        )))
    except sel_exc.TimeoutException:
        input("Please enter smth: ")
        raise
    locate_page.click()
    for i in dates:
        elem = driver.find_element_by_xpath("//input[@id=%s]" % i)
        elem.clear()
        elem.send_keys(dates[i])
    input_boxes = driver.find_elements(By.XPATH, "//span[@class='select2-search select2-search--inline']")
    for i in range(4):
        if conditions[i] is None:
            continue
        input_boxes[i].click()
        for j in driver.find_elements_by_xpath(  # оптимизировать, чтобы не прогонять по selectoram, где value = None
                "//span[@class='select2-container select2-container--default select2-container--open']/*/*/*/li"):
            if j.text in conditions[i]:
                j.click()
        driver.find_element_by_xpath(
            "//div[@class='select2-link2 select2-close']/button[@class='btn btn-primary']"
        ).click()
    driver.find_element_by_xpath("//button[@id='calendar-btn-search']").click()
    vibory_links = [el.get_attribute("href") for el in driver.find_elements_by_xpath("//a[@class='viboryLink']")]
    maj_final_data, prop_final_data = pd.DataFrame(), pd.DataFrame()
    for i in vibory_links:
        driver.get(i)
        while True:
            try:
                driver.find_element_by_xpath("//a[@id='election-results-name']")  # иногда возникает ошибка
            except sel_exc.NoSuchElementException:
                tms(5)
                continue
            else:
                break
        driver.find_element_by_xpath("//div[@class='main__menu']/div[2]/ul/div[1]/a").click()
        year = driver.find_element_by_xpath("//div[@id='election-info']/div/div[3]/div[2]/b").text.split(r".")[2]
        # driver.find_element_by_xpath("//a[@id='election-results-name']").click()
        driver.find_element_by_xpath("//a[@id='election-results-name']").click()
        menu_options = driver.find_elements_by_xpath("//tbody/tr[@class='trReport']/td/a")
        menu_options_text = [el.text for el in menu_options]
        try:
            menu_options[
                [i for i, z in enumerate(menu_options_text) if "Сводная" in z and "одномандат" in z][0]].click()
        except IndexError:
            try:
                menu_options[
                    [i for i, z in enumerate(menu_options_text) if "Сводная" in z and "едином" in z][0]].click()
                if len([i for i, z in enumerate([el.text for el in driver.find_elements_by_xpath(
                        "//li[@class='tree-li']/*/li[@class='tree-li']/a[2]")]) if "Единый округ" in z]) != 1:
                    raise sel_exc.NoSuchElementException
            except IndexError:
                input("Can't assign func_option")
                raise
            except sel_exc.NoSuchElementException:
                input("Can't assign func_option")
                raise
            else:
                func_option = 1
        else:
            func_option = 0
        if what_to_extract["maj"]:  # call for another function (maj case or prop case or smth)
            maj_data = maj_case(driver, func_option)
            if maj_data is not None:
                maj_data["year"] = pd.Series(repeat(year, len(maj_data.iloc[:, 0])))
                maj_final_data = maj_final_data.append(maj_data)
        if what_to_extract["prop"]:
            prop_data = prop_case(driver, func_option)
            if prop_data is not None:
                prop_data["year"] = pd.Series(repeat(year, len(prop_data.iloc[:, 0])))
                prop_final_data = prop_final_data.append(prop_data)
        # Два идентичных if, можно сократить запись?
    return maj_final_data, prop_final_data


def maj_case(driver, func_option):  # with uik's
    driver.find_element_by_xpath("//a[@id='standard-reports-name']").click()
    try:
        driver.find_element_by_xpath("//a[@id='220-rep-dir-link']").click()
    except sel_exc.NoSuchElementException:
        input("No info about maj_case")
        return None
    driver.find_element_by_xpath("//li[@class='tree-li']").click()
    counties_links = [county.get_attribute('href') for county in driver.find_elements_by_xpath(
        "//li[@class='tree-li']/*/li[@class='tree-li']/a[2]"
    )]
    data_info = pd.DataFrame()
    for i in range(len(counties_links)):
        tms(2)
        driver.get(counties_links[i])
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH, "//tbody[@valign='top']/tr/td[2]"
            )))
        except sel_exc.TimeoutException:
            input('Pls input smth :')
            raise
        cand_names = pd.Series([el.text for el in driver.find_elements_by_xpath(  # можно оптимизировать: 3 к ряду
            "//tbody[@valign='top']/tr/td[2]"
        )])
        nom_subject = pd.Series([el.text for el in driver.find_elements_by_xpath(
            "//tbody[@valign='top']/tr/td[4]"
        )])
        county_num = pd.Series([el.text for el in driver.find_elements_by_xpath(
            "//tbody[@valign='top']/tr/td[5]"
        )])
        county_name = driver.find_element_by_xpath("//li[@class='tree-li']/*/li[@class='tree-li']/a[2]").text
        county_names = pd.Series([county_name for i in range(len(cand_names))])
        reg_status = pd.Series([True if el.text == "зарегистрирован" else False for el in driver.find_elements_by_xpath(
            "//tbody[@valign='top']/tr/td[7]")])
        data_info = data_info.append(pd.DataFrame({"cand_names": cand_names, "nom_subject": nom_subject,
                                         "county_num": county_num, "county_names": county_names,
                                         "reg_status": reg_status}))
    driver.find_element_by_xpath("//a[@id='election-results-name']").click()
    menu_options = driver.find_elements_by_xpath("//tbody/tr[@class='trReport']/td/a")
    menu_options_text = [el.text for el in menu_options]
    menu_options[[i for i, z in enumerate(menu_options_text) if "Сводная" in z and "одномандат" in z][0]].click()
    # три строчки выше можно оптимизировать?
    counties_links = [el.get_attribute("href") for el in driver.find_elements_by_xpath(
        "//li[@class='tree-li']/*/li[@class='tree-li']/a[2]")]  # вторая одинаковая строка в одной функции
    if func_option == 1:
        counties_links = counties_links[1:]
    data = pd.DataFrame()
    for link in counties_links:
        driver.get(link)
        sub_counties_links_res = [el.get_attribute("href") for el in driver.find_elements_by_xpath(
            "//div/ul/li/ul/li[@class='tree-li']/ul/li/a[2]")]
        for i in sub_counties_links_res:
            driver.get(i)
            candidate_names = pd.Series([el.text for el in driver.find_elements_by_xpath(
                "//table[@id='fix-columns-table']/tbody/tr/td[2]")])
            for j in range(4, len(driver.find_elements_by_xpath("//table[@id='fix-columns-table']/thead/tr/th")) + 1):
                result = pd.Series(list(map(int, [el.text for el in driver.find_elements_by_xpath(
                    "//table[@id='fix-columns-table']/tbody/tr/td[%s]/nobr/b" % j)])))
                uik_num = driver.find_element_by_xpath("//table[@id='fix-columns-table']/thead/tr/th[%s]" % j).text
                uik_nums = pd.Series([uik_num for t in range(len(result))])
                came_to_ballotbox = result[[
                    y for y, z in enumerate(candidate_names) if "Число бюллетеней, содержащихся в" in z
                ]].sum()
                num_of_registered_voters = int(result[[
                    y for y, z in enumerate(candidate_names) if "Число избирателей, внесенных в список" in z
                ]])
                came_to_ballotbox = pd.Series(repeat(came_to_ballotbox, len(result)))
                num_of_registered_voters = pd.Series(repeat(num_of_registered_voters, len(result)))
                data = data.append(pd.DataFrame({"cand_names": candidate_names, "votes": result, "uik": uik_nums,
                                                 "came_to_ballotbox": came_to_ballotbox,
                                                 "num_of_registered_voters": num_of_registered_voters}))
    final_dataset = pd.merge(data, data_info, on="cand_names", how="inner")
    # final_dataset.to_csv("test.csv", index_label=False)
    return final_dataset


def prop_case(driver, func_option):
    driver.find_element_by_xpath("//a[@id='standard-reports-name']").click()
    reports_options = driver.find_elements_by_xpath("//div[@id='standard-reports']/table/tbody/tr/td/a")
    reports_options_text = [el.text for el in driver.find_elements_by_xpath(
            "//div[@id='standard-reports']/table/tbody/tr/td/a")]
    try:
        reports_options[[i for i, z in enumerate(reports_options_text) if "списке" in z and "политическими" in z][0]]
    except IndexError:
        input("No info about prop_case")
        return None
    reports_options[[i for i, z in enumerate(reports_options_text) if "Список" in z and "принимающих" in z][0]].click()
    data_info = pd.DataFrame({"party_names": [el.text for el in driver.find_elements_by_xpath(
        "//table[@id='politparty2']/tbody/tr/td[2]/form/a")]})
    driver.find_element_by_xpath("//a[@id='election-results-name']").click()
    menu_options = driver.find_elements_by_xpath("//div[@id='election-results']/table/tbody/tr/td/a")
    menu_options_text = [el.text for el in driver.find_elements_by_xpath(
        "//div[@id='election-results']/table/tbody/tr/td/a")]
    menu_options[[i for i, z in enumerate(menu_options_text) if "Сводная" in z and "едином" in z][0]].click()
    counties_links = [el.get_attribute("href") for el in driver.find_elements_by_xpath(
        "//li[@class='tree-li']/*/li[@class='tree-li']/a[2]")]
    if func_option == 1:
        counties_links = counties_links[0]
    data = pd.DataFrame()
    for link in counties_links:
        driver.get(link)
        sub_counties_links_res = [el.get_attribute("href") for el in driver.find_elements_by_xpath(
            "//div/ul/li/ul/li[@class='tree-li']/ul/li/a[2]")]
        for i in sub_counties_links_res:
            driver.get(i)
            party_names = pd.Series([el.text for el in driver.find_elements_by_xpath(
                "//table[@id='fix-columns-table']/tbody/tr/td[2]")])
            for j in range(4, len(driver.find_elements_by_xpath("//table[@id='fix-columns-table']/thead/tr/th")) + 1):
                result = pd.Series(list(map(int, [el.text for el in driver.find_elements_by_xpath(
                    "//table[@id='fix-columns-table']/tbody/tr/td[%s]/nobr/b" % j)])))
                uik_num = driver.find_element_by_xpath("//table[@id='fix-columns-table']/thead/tr/th[%s]" % j).text
                uik_nums = pd.Series(repeat(uik_num, len(result)))
                came_to_ballotbox = result[[
                    y for y, z in enumerate(party_names) if "Число бюллетеней, содержащихся в" in z
                ]].sum()
                num_of_registered_voters = int(result[[
                    y for y, z in enumerate(party_names) if "Число избирателей, внесенных в список" in z
                ]])
                came_to_ballotbox = pd.Series(repeat(came_to_ballotbox, len(result)))
                num_of_registered_voters = pd.Series(repeat(num_of_registered_voters, len(result)))
                data = data.append(pd.DataFrame({"party_names": party_names, "votes": result, "uik": uik_nums,
                                                 "came_to_ballotbox": came_to_ballotbox,
                                                 "num_of_registered_voters": num_of_registered_voters}))
    final_dataset = pd.merge(data, data_info, on="party_names", how="inner")
    # final_dataset.to_csv("test.csv", index_label=False)
    return final_dataset


def scrap_particular_elections(driver, what_to_extract):  # not necessary
    while True:
        try:
            driver.find_element_by_xpath("//a[@id='election-results-name']")
        except sel_exc.NoSuchElementException:
            tms(5)
            continue
        else:
            break
        finally:
            driver.find_element_by_xpath("//a[@id='election-results-name']").click()


x = scrap_elections(regions="Московская область", start_date="01.01.2010", end_date="01.01.2015", level="Региональный",
                    kind="Выборы депутата", type_of_elections="Основные",
                    driver_loc="C:/Users/user/Desktop/DZ/Python/Driver/geckodriver.exe", maj=True,
                    output_dir="C:/Users/user/Desktop/DZ/Python/Projects/Elections")
