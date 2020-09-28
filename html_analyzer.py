import os
import re
from collections import defaultdict
from zipfile import ZipFile
from pathlib import Path

import argparse
from lxml import etree
import pandas as pd


class ProjectEvaluator:
    def __init__(self, proj_path):
        self.proj_path = proj_path
        self.file_index = self.__read_project()

    def __read_project(self):
        file_index = defaultdict(list)
        with ZipFile(self.proj_path) as archive:
            for file in archive.namelist():
                file_info = archive.getinfo(file)
                if file_info.is_dir():
                    continue
                file_index[Path(file).suffix].append((file, archive.read(file)))
        return file_index

    def html_num_check(self, stat):
        htm_num = len(self.file_index['.html'])
        stat['html_num'] = htm_num

    def html_content_check(self, stat):
        med_types = set()
        iframe_types = set()

        html_dict = defaultdict(lambda: 0)
        for file, content in self.file_index['.html']:
            tree = etree.HTML(content)
            bt_ck = tree.xpath('//button')
            nav_check = tree.xpath("//*[contains(@class,'nav')]")
            drop_down_check = tree.xpath("//div [contains(@class,'dropdown')]")
            ex_link = tree.xpath("//a[contains(@href, 'http')]")
            in_link = tree.xpath("//a[not(contains(@href, 'http'))]")
            img_ck = tree.xpath("//img")
            pagination_ck = tree.xpath("//div[contains(@class, 'pagination')]")
            head_meta = tree.xpath("//head/meta")
            alt_ck = tree.xpath("//*[@alt]")
            form_ck = tree.xpath("//form")
            table_ck = tree.xpath("//table")
            img_gallary = tree.xpath("//*[contains(@class, 'gallery')]")

            video_audio = tree.xpath("//source/@src")
            for med in video_audio:
                med_types.add(Path(med).suffix)

            iframe_src = tree.xpath("//iframe/@src")
            for src in iframe_src:
                home_site = src.strip("http://").strip("https://").split("/")[0]
                iframe_types.add(home_site)
            list_ck = tree.xpath("//ul|//ol|//li|//dl|//dt|//dd")
            inline_ck = tree.xpath('//*[@style]')
            code_ck = tree.xpath("//code")
            tooltips_ck = tree.xpath("//*[contains(@class,'tooltip')]")
            html_dict['button'] += len(bt_ck)
            html_dict['nav_bar'] += len(nav_check)
            html_dict['drop_down_check'] += len(drop_down_check)
            html_dict['external_link'] += len(ex_link)
            html_dict['internal_link'] += len(in_link)
            html_dict['image'] += len(img_ck)
            html_dict['pagination'] += len(pagination_ck)
            html_dict['head_meta'] += len(head_meta)
            html_dict['alt_ck'] += len(alt_ck)
            html_dict['form_ck'] += len(form_ck)
            html_dict['table_ck'] += len(table_ck)
            html_dict['img_gallary'] += len(img_gallary)
            html_dict['media_type'] = med_types
            html_dict['iframe_types'] = iframe_types
            html_dict['list_ck'] = len(list_ck)
            html_dict['inline_code'] = len(inline_ck)
            html_dict['code'] = len(code_ck)
            html_dict['tooltips'] = len(tooltips_ck)
        stat.update(html_dict)

    def css_content_check(self, stat):
        stat['css'] = 0
        for file, content in self.file_index['.css']:
            css_elements = re.findall("{[^\}]+}", str(content))
            stat['css'] += len(css_elements)

    def js_content_check(self, stat):
        stat['js_code_line'] = 0
        for file, content in self.file_index['.js']:
            js_len = len(str(content).split("\\n"))
            stat['js_code_line'] += js_len

    def gen_summary(self, stat):
        elements = 0
        allowd_elements = ['button', 'nav_bar', 'form_ck', 'img_gallary', 'list_ck', 'inline_code', 'code',
                           'drop_down_check', 'tooltips', 'pagination']
        for e in allowd_elements:
            elements += 1 if stat[e] > 0 else 0
        elements += min(2, len(stat['media_type']))
        elements += min(2, len(stat['iframe_types']))
        elements += 1 if stat['js_code_line'] > 5 else 0
        elements += 1 if stat['css'] > 7 else 0

        return {
            "html_num": "pass" if stat['html_num'] >= 7 else "fail",
            "nav_menu": "pass" if stat['internal_link'] > 7 else "fail",
            "css_elements": "pass" if stat['css'] >= 5 else "fail",
            "external_links": "pass" if stat['external_link'] >= 4 else 'fail',
            "img_num": 'pass' if stat['image']+ len(stat['media_type']) + len(stat['iframe_types']) >=4 else "fail",
            "head_meta": "pass" if stat['head_meta'] > 0 else "fail",
            "alt": "pass" if stat['alt_ck'] > 0 else "fail",
        }

    def evaluate(self):
        checks = [self.html_num_check,
                  self.html_content_check,
                  self.css_content_check,
                  self.js_content_check
                  ]
        stat = dict()
        for ck in checks:
            ck(stat)
        return stat


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Middle term auto-grading')
    parser.add_argument('--in_dir', help="path to the directory containsing zips")
    args = parser.parse_args()
    name = []
    summarys = []
    detailed_infos = []

    df = pd.DataFrame()
    for zip_file in os.listdir(args.in_dir):
        zip_path = os.path.join(args.in_dir, zip_file)
        name.append(zip_file)
        try:
            pe = ProjectEvaluator(zip_path)
            info = pe.evaluate()
            summarys.append(pe.gen_summary(info))
            detailed_infos.append(info)
        except:
            summarys.append("")
            detailed_infos.append("")
    df['name'] = name
    df['summary'] = summarys
    df['info'] = detailed_infos
    df.to_csv("report.csv")
