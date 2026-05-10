#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2025 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: demo.py
编写作者: dongruihua
创建日期: 2025/1/14
修订说明:
纯demo文件，无实际用途。
1.demo：生成python测试用例
2.demo:替换cookie，发送请求，打印响应内容
==================================================================="""

from db.SQLiteUtils import SQLiteUtils
import requests

host = "https://ieu.hik-partner.com"
cookie = "_gid=GA1.2.264646362.1736738958; "
"gdp_user_id=gioenc-38g83eg8%2Cg8g4%2C518c%2Cac01%2Ccd460dg631bb; d7f2195d633369d9_gdp_user_key=; hik_connect_pro_userlogin=1; emphasisStatus=0; JSESSIONID=3134927f-8932-4914-8a0a-eeb6d54e39de; hik_connect_pro_userohLogout=1; country=225; phone=undefined; isAuthed=1; name=test_sudan_remote_upgrade@teml.net%20test_sudan_remote_upgrade@teml.net; avatar=undefined; d7f2195d633369d9_gdp_cs1=gioenc-e33g6563da88572caa2b96b0cb730g1b; d7f2195d633369d9_gdp_gio_id=gioenc-e33g6563da88572caa2b96b0cb730g1b; d7f2195d633369d9_gdp_session_id=9a2aedd4-39fa-4131-af7d-22ecfc31ace1; d7f2195d633369d9_gdp_session_id_sent=9a2aedd4-39fa-4131-af7d-22ecfc31ace1; email=test_sudan_remote_upgrade@teml.net; _gat_gtag_UA_153689847_1=1; d7f2195d633369d9_gdp_sequence_ids={%22globalKey%22:963%2C%22VISIT%22:16%2C%22PAGE%22:95%2C%22CUSTOM%22:854}; _ga=GA1.1.60324856.1736738958; _ga_6GM4HD8GWX=GS1.1.1736832764.7.1.1736834150.0.0.0; _ga_6HBKRZDR7P=GS1.1.1736832764.7.1.1736834150.0.0.0"

get_example_template = """
def test_{uri_1}_{uri_2}(self):
    url = self.host + "{uri}"
    result = self.client.https_get_with_headers(url,None,cookies)
"""

post_example_template = """
def test_{uri_1}_{uri_2}(self):
    url = self.host + "{uri}"
    data = {body}
    result = self.client.https_post_with_headers(url,json.dumps(data),cookies)
"""


def main():
    db_handler = SQLiteUtils()
    sql = """SELECT * FROM mitmproxy_records"""
    result = db_handler.query_data(sql)
    for row in result:
        uri = row[2]
        method = row[3]
        if row[4] is not None:
            headers = {"Content-Type": row[4]}
        else:
            headers = {}
        body = row[5] or {}
        status_code = row[6]

        if method == "GET":
            example = get_example_template.format(uri_1=uri.split("/")[-1], uri_2=uri.split("/")[-2], uri=uri)
        if method == "POST":
            example = post_example_template.format(uri_1=uri.split("/")[-1], uri_2=uri.split("/")[-2], uri=uri,
                                                   body=body)
        print(example)

        # url = host + uri
        # headers.update({"Cookie": cookie})
        # result = requests.request(method, url=url, headers=headers, data=body)
        # print(f"{method} {uri}")
        # print(f"请求头: {headers}")
        # print(f"请求体: {body}")
        # print(f"响应状态码: {status_code}")
        # print(f"响应内容: {result.text}")

    db_handler.close()


if __name__ == "__main__":
    main()
