#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: webdisplay.py
编写作者: dongruihua
创建日期: 2025/1/14
修订说明:
使用fastapi+jinja2返回数据库查询接口的HTML页面
使用方法:
1. 启动webdisplay.py： python webdisplay.py
2. 访问http://127.0.0.1:8000/record/no/response/all，查看所有记录
3. 访问http://127.0.0.1:8000/record/no/response/{record_id}，查看指定record_id的记录
==================================================================="""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from curd.dataquery import DataQuery

app = FastAPI(title="流量录制记录查询", description="流量录制记录查询", version="0.1.0")
templates = Jinja2Templates(directory="templates")


@app.get("/record/with/response/{record_id}", response_class=HTMLResponse, tags=["流量录制记录"])
async def record(request: Request, record_id: str):
    """
    根据record_id查询数据库，返回HTML页面——有响应内容
    """
    if record_id == "all":
        record_data = DataQuery.get_all_data()
    elif record_id:
        record_data = DataQuery.get_data_by_id(record_id)
    else:
        record_data = []
    return templates.TemplateResponse("record_with_response.html", {
        "request": request,
        "record_data": record_data
    })


@app.get("/record/no/response/{record_id}", response_class=HTMLResponse, tags=["流量录制记录"])
async def record(request: Request, record_id: str):
    """
    根据record_id查询数据库，返回HTML页面——无响应内容
    """
    if record_id == "all":
        record_data = DataQuery.get_all_data()
    elif record_id:
        record_data = DataQuery.get_data_by_id(record_id)
    else:
        record_data = []
    return templates.TemplateResponse("record.html", {
        "request": request,
        "record_data": record_data
    })


if __name__ == "__main__":
    uvicorn.run(app="webdisplay:app", host="0.0.0.0", port=8000, reload=True)
