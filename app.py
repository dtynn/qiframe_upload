#coding=utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os

import tornado
import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer

import ConfigParser
import json
from uuid import uuid4
from qiniu import conf as qConf, rs as qRs
import urllib
from base64 import b64decode

#config & settings
confFile = open('config.conf', 'r')
conf = ConfigParser.ConfigParser()
conf.readfp(confFile)

accesskey = conf.get('qiniu', 'accesskey')
secretkey = conf.get('qiniu', 'secretkey')
bucket = conf.get('qiniu', 'bucket')
domain = conf.get('qiniu', 'domain')
qUpHost = conf.get('qiniu', 'upHost')

siteDomain1 = conf.get('site', 'domain1')
siteDomain2 = conf.get('site', 'domain2')

description = dict()
description['local_simple'] = '不跨域iframe上传，弹窗提示上传结果'
description['local_crossdomain'] = '从 %s 域上传到 %s 域，上传结果无法处理' % (siteDomain1, siteDomain2)
description['qiniu_crossdomain'] = '从 %s 域上传到up.qiniu.com域，uptoken不设置跳转，上传结果无法处理' % (siteDomain1,)
description['qiniu_redirect'] = '从 %s 域上传到up.qiniu.com域，uptoken设置跳转到 %s 上的接口，弹窗提示上传结果。' % (siteDomain1, siteDomain1)


#handlers
class IndexHdl(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html', domain=siteDomain1)
        return


class SimpleUploadHdl(tornado.web.RequestHandler):
    def get(self):
        desc = description['local_simple']
        upHost = 'http://%s/receive' % (siteDomain1,)
        token = ''
        self.render('upload.html', upHost=upHost, token=token, desc=desc)
        return


class SimpleUploadCrossdomainHdl(tornado.web.RequestHandler):
    def get(self):
        desc = description['local_crossdomain']
        upHost = 'http://%s/receive' % (siteDomain2,)
        token = ''
        self.render('upload.html', upHost=upHost, token=token, desc=desc)
        return


class QiniuUploadCrossdomainHdl(tornado.web.RequestHandler):
    def get(self):
        desc = description['qiniu_crossdomain']
        qConf.ACCESS_KEY = accesskey
        qConf.SECRET_KEY = secretkey
        policy = qRs.PutPolicy(bucket)
        upHost = qUpHost
        token = policy.token()
        self.render('upload.html', upHost=upHost, token=token, desc=desc)
        return


class QiniuUploadRedirectHdl(tornado.web.RequestHandler):
    def get(self):
        desc = description['qiniu_redirect']
        qConf.ACCESS_KEY = accesskey
        qConf.SECRET_KEY = secretkey
        policy = qRs.PutPolicy(bucket)
        policy.returnUrl = 'http://%s/receive' % (siteDomain1,)
        upHost = qUpHost
        token = policy.token()
        self.render('upload.html', upHost=upHost, token=token, desc=desc)
        return


class ReceiveHdl(tornado.web.RequestHandler):
    def get(self):
        result = self.get_argument('upload_ret', '')
        if not result:
            errCode = self.get_argument('code', '')
            errDetail = self.get_argument('error', 'something error')
            detail = dict(err_code=errCode, err_msg=urllib.unquote(errDetail))
        else:
            try:
                detail = json.loads(b64decode(result))
            except (TypeError, ValueError):
                detail = 'invalid data'
        self.write(json.dumps(detail))
        return

    def post(self):
        res = dict(status=0, data=uuid4().hex)
        self.write(json.dumps(res))
        return

#settings & urls
PORT = 50041

settings = dict(
    debug=False,
    template_path='tmpl',
    static_path=os.path.abspath('static'),
)


urls = [
    (r'/', IndexHdl),
    (r'/upload_simple', SimpleUploadHdl),
    (r'/upload_crossdomain', SimpleUploadCrossdomainHdl),
    (r'/upload_qiniu_cross', QiniuUploadCrossdomainHdl),
    (r'/upload_qiniu_redirect', QiniuUploadRedirectHdl),
    (r'/receive', ReceiveHdl)
]

app = tornado.web.Application(urls, **settings)
server = HTTPServer(app, xheaders=True)
server.bind(PORT)
server.start()
tornado.ioloop.IOLoop.instance().start()