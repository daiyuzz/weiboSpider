# -*- coding: utf-8 -*-
import json

from scrapy import Request, Spider
from WeiboScrapy.items import *


class WeiboSpider(Spider):
    name = 'weibo'
    allowed_domains = ['m.weibo.cn']
    # 用户详情页
    user_url = 'https://m.weibo.cn/api/container/getIndex?uid={uid}&type=uid&value={uid}&containerid=100505{uid}'
    # 粉丝列表
    fan_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_fans_-_{uid}&since_id={page}'
    # 关注列表
    follow_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_followers_-_{uid}&page={page}'
    # 微博列表
    weibo_url = 'https://m.weibo.cn/api/container/getIndex?containerid=230413{uid}_-_WEIBO_SECOND_PROFILE_WEIBO&page={page}'

    start_users = ['1742566624', '1223178222', '1745465244', '1197369013', '3261134763', '3952070245']

    def start_requests(self):
        for uid in self.start_users:
            yield Request(self.user_url.format(uid=uid), callback=self.parse_user)

    def parse_user(self, response):
        result = json.loads(response.text)
        # self.logger.debug(result)
        if result.get('data').get('userInfo'):
            user_info = result['data']['userInfo']
            user_item = UserItem()
            filed_map = {
                'id': 'id', 'name': 'screen_name', 'avatar': 'profile_image_url', 'cover': 'cover_image_phone',
                'gender': 'gender', 'description': 'description', 'fans_count': 'followers_count',
                'follows_count': 'follow_count', 'weibos_count': 'statuses_count', 'verified': 'verified',
                'verified_reason': 'verified_reason', 'verified_type': 'verified_type'
            }
            for filed, attr in filed_map.items():
                user_item[filed] = user_info.get(attr)

            yield user_item

            # 关注
            uid = user_info.get('id')
            yield Request(self.follow_url.format(uid=uid, page=1), callback=self.parse_follows,
                          meta={"uid": uid, "page": 1})

            # 粉丝
            yield Request(self.fan_url.format(uid=uid, page=1), callback=self.parse_fans, meta={"uid": uid, "page": 1})

            # 微博列表
            yield Request(self.weibo_url.format(uid=uid, page=1), callback=self.parse_weibos,
                          meta={"uid": uid, "page": 1})

    def parse_follows(self, response):
        """解析关注用户"""
        result = json.loads(response.text)
        if result.get('data').get('cards') and len(result.get('data').get('cards')) and result.get('data').get('cards')[
            -1].get('card__group'):
            # 解析用户
            follows = result.get('data').get('cards')[-1].get('card_group')
            for follow in follows:
                if follow.get('user'):
                    uid = follow.get('user').get('id')
                    yield Request(self.user_url.format(uid=uid), callback=self.parse_user)
            # 关注列表
            uid = response.meta.get('uid')
            user_relation_item = UserRelationItem()
            follows = [{'id': follow.get('user').get('id'), 'name': follow.get('user').get('screen_name')} for follow in
                       follows]
            user_relation_item['id'] = uid
            user_relation_item['follows'] = follows
            user_relation_item['fans'] = []
            yield user_relation_item

            # 下一页关注
            page = response.meta.get('page') + 1
            yield Request(self.follow_url.format(uid=uid, page=page), callback=self.parse_follows,
                          meta={'uid': uid, 'page': page})

    def parse_fans(self, response):
        """解析粉丝列表"""
        result = json.loads(response.text)
        if result.get('data').get('cards') and len(result.get('data').get('cards')) and result.get('data').get('cards')[
            -1].get('card_group'):
            # 解析用户
            fans = result.get('data').get('cards')[-1].get('card_group')
            for fan in fans:
                if fan.get('user'):
                    uid = fan.get('user').get('id')
                    yield Request(self.user_url.format(uid=uid), callback=self.parse_user)

            # 粉丝列表
            uid = response.meta.get('uid')
            user_relation_item = UserRelationItem()
            fans = [{'id': fan.get('user').get('id'), 'name': fan.get('user').get('screen_name')} for fan in fans]
            user_relation_item['id'] = uid
            user_relation_item['fans'] = fans
            user_relation_item['follows'] = []
            yield user_relation_item

            # 下一页粉丝列表
            page = response.meta.get('page') + 1
            yield Request(self.fan_url.format(uid=uid, page=page), callback=self.parse_fans,
                          meta={'uid': uid, 'page': page})

    def parse_weibos(self, response):
        result = json.loads(response.text)
        if result.get('ok') and result.get('data').get('cards'):
            weibos = result.get('data').get('cards')
            for weibo in weibos:
                try:
                    mblog = weibo['mblog']
                except KeyError:
                    pass
                else:
                    if mblog:
                        weibo_item = WeiboItem()
                        field_map = {
                            'id': 'id', 'attitudes_count': 'attitudes_count', 'comments_count': 'comments_count',
                            'created_at': 'created_at', 'reposts_count': 'reposts_count', 'picture': 'original_pic',
                            'source': 'source', 'text': 'text', 'thumbnail': 'thumbnail_pic', 'pictures': 'pics'
                        }
                        for filed, attr in field_map.items():
                            weibo_item[filed] = mblog.get(attr)
                        yield weibo_item

            # 下一页微博列表
            uid = response.meta.get('uid')
            page = response.meta.get('page') + 1
            yield Request(self.weibo_url.format(uid=uid, page=page), callback=self.parse_weibos,
                          meta={'uid': uid, 'page': page})
