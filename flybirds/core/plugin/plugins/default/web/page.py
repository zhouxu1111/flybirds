# -*- coding: utf-8 -*-
# @Time : 2022/3/7 19:18
# @Author : hyx
# @File : page.py
# @desc : web page implement
import json
import time
from urllib.parse import urlparse

import flybirds.core.global_resource as global_resource
import flybirds.core.global_resource as gr
import flybirds.utils.flybirds_log as log
import flybirds.utils.verify_helper as verify_helper
from flybirds.utils import dsl_helper
from flybirds.utils.dsl_helper import is_number

__open__ = ["Page"]


class Page:
    """Web Page Class"""

    name = "web_page"
    instantiation_timing = "plugin"

    def __init__(self):
        page, context = self.init_page()
        self.page = page
        self.context = context

    @staticmethod
    def init_page():
        browser = gr.get_value('browser')
        context = browser.new_context(record_video_dir="videos",
                                      ignore_https_errors=True)
        default_timeout = gr.get_web_info_value("default_time_out", 30)
        context.set_default_timeout(float(default_timeout) * 1000)
        page = context.new_page()

        # todo 读取 requestInterception 配置
        request_interception = True
        if request_interception:
            page.route("**/*", handle_route)
            # request listening events
            page.on("request", handle_request)

        ele_wait_time = gr.get_frame_config_value("wait_ele_timeout", 30)
        page_render_timeout = gr.get_frame_config_value("page_render_timeout",
                                                        30)
        page.set_default_timeout(float(ele_wait_time) * 1000)
        page.set_default_navigation_timeout(float(page_render_timeout) * 1000)
        return page, context

    def navigate(self, context, param):
        param_dict = dsl_helper.params_to_dic(param, "urlKey")
        url_key = param_dict["urlKey"]
        schema_url_value = gr.get_page_schema_url(url_key)
        # self.page.goto(schema_url_value)
        # todo 待去掉
        with self.page.expect_response(lambda
                                               response: response.status == 200 and 'airlineRebateActivityHomePage' in response.url) as response_info:
            self.page.goto(schema_url_value)
        response = response_info.value
        print(f'response>>>: {response.json()}')

    def return_pre_page(self, context):
        self.page.go_back()

    def sleep(self, context, param):
        if is_number(param):
            self.page.wait_for_timeout(float(param) * 1000)
        else:
            log.warn("default wait for timeout!")
            self.page.wait_for_timeout(3 * 1000)

    def cur_page_equal(self, context, param):
        cur_url = self.page.url.split('?')[0]
        if param.startswith(("http", "https")):
            target_url = param.split('?')[0]
        else:
            schema_url = global_resource.get_page_schema_url(param)
            target_url = schema_url
        verify_helper.text_equal(target_url, cur_url)


def handle_request(request):
    # interceptionRequest  缓存请求相关操作
    parsed_uri = urlparse(request.url)
    operation = parsed_uri.path.split('/')[-1]
    if operation is not None:
        # // 服务请求缓存是否存在
        interception_request = gr.get_value('interceptionRequest')
        request_body = interception_request.get(operation)

        if request_body is not None:
            log.info(
                f'[handle_request]缓存服务：{operation},'
                f'request_body: {request_body}')
            current_request_info = {'postData': request.post_data,
                                    'url': request.url,
                                    'updateTimeStamp': int(
                                        round(time.time() * 1000))}
            # // 缓存服务请求：赋值
            interception_request[operation] = current_request_info
            gr.set_value("interceptionRequest", interception_request)


def handle_route(route):
    # todo abort_domain_list 获取
    abort_domain_list = None
    parsed_uri = urlparse(route.request.url)
    domain = parsed_uri.hostname
    if abort_domain_list and domain in abort_domain_list:
        route.abort()
        return

    resource_type = route.request.resource_type
    if resource_type != 'fetch' and resource_type != 'xhr':
        route.continue_()
        return

    # mock response data
    operation = parsed_uri.path.split('/')[-1]
    mock_case_id = None
    if operation is not None:
        # /服务监听：operation->mockCaseId
        interception_values = gr.get_value('interceptionValues')
        mock_case_id = interception_values.get(operation)
    if mock_case_id:
        # todo   getCaseResponseBody 1. 从文件读取 ：load时存入global  2. 从接口读取
        # mock_body = getCaseResponseBody(mock_case_id)
        mock_body = json.dumps({'mock_case_id': f'hyx_{mock_case_id}'})
        if mock_body:
            route.fulfill(status=200,
                          content_type="application/json;charset=utf-8",
                          body=mock_body)
    else:
        route.continue_()

    # if "airlineRebateActivityHomePage" in route.request.url:
    #     print('handle_route:**** url:>', route.request.url)
    #     route.fulfill(
    #         status=200,
    #         content_type="application/json;charset=utf-8",
    #         body='{"data":"hyx"}')
    # else:
    #     route.continue_()
