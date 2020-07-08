import os
import io
import json
import hashlib
from configparser import ConfigParser
import operator as op
from flask import Flask, request, Response

config = ConfigParser()

app = Flask(__name__)
# 当前支持的 frps 插件版本
supportPluginVersion = "0.1.0"
# 盐
saltString = 'ka2&n2-I'
# 用户信息字典
UserInfo_dict = {}


# 加盐计算 MD5
def CalMd5(instr):
    return hashlib.md5((instr + saltString).encode('utf-8')).hexdigest()

# 用户信息
class UserInfo:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.sign = CalMd5(username + password)
        self.ProxyInfo = None

# 代理信息
class ProxyInfo:
    def __init__(self, name, remote_port):
        # 这里的 name 不带 UserName
        self.name = name
        self.remote_port = remote_port
        # 这个跟顺序有关
        # proxy_name(name部分) + proxy_type + use_encryption + use_compression + remote_port + custom_domains + locations + headers
        # 还有一些参数应该是空，但是都会进行拼接处理，所以不用显示出来
        catString = name + 'tcp' + 'True' + 'True' + remote_port + "None" + "None" + "None"
        self.sign = CalMd5(catString)

# 读取登录的缓存信息
def ReadTokenFromFile(config): 
    UserInfo_dict.clear()
    nowRootPath = os.getcwd()
    nowRootPath = os.path.join(nowRootPath, 'ClientInfos')
    strExtensionName_ini = ".ini"
    iniList = []
    # 找出所有的配置
    for fpath, dirnames, fnames in os.walk(nowRootPath):
        for fname in fnames:
            extensionName = os.path.splitext(fname)[-1]
            if op.eq(extensionName, strExtensionName_ini) == True:
                iniList.append(os.path.join(fpath, fname))
    
    for oneIni in iniList:
        config.read(oneIni)
        # UserInfo
        nowUserName = config.get('UserInfo', 'username')
        nowUserPass = config.get('UserInfo', 'password')
        nowUserInfo = UserInfo(nowUserName, nowUserPass)
        # ProxyInfo
        nowProxyName = config.get('ProxyInfo', 'name')
        nowremote_port = config.get('ProxyInfo', 'remote_port')
        nowUserInfo.ProxyInfo = ProxyInfo(nowProxyName, nowremote_port)
        # 加入字典
        UserInfo_dict[nowUserName] = nowUserInfo

        print('Add User : ' + nowUserName)

    print("Read Token From File Done.")

# 插件的版本判断
def JugVersion(nowVersion):
    if nowVersion != supportPluginVersion:
        return False
    else:
        return True

# 检查用户信息
def CheckUserInfo(content):
    nowUser = content['user']
    # 用户是否存在
    if nowUser not in UserInfo_dict.keys():
        return 
    # 是否有密码字段
    if 'token' not in content["metas"]:
        return -1
    # 是否有 sign 字段
    if 'sign' not in content["metas"]:
        return -2
    # 验证密码
    # nowToken = content["metas"]['token']
    # if UserInfo_dict[nowUser].password != nowToken:
    #     return -3
    # 验证 sign
    # 因为是必填项，所以就直接与缓存的 UserInfo sign 进行对于
    nowSign = content["metas"]['sign']
    if UserInfo_dict[nowUser].sign != nowSign:
        return -4
    
    return 0

# 检查代理信息
def CheckProxyInfo(content):
    # 是否有 sign 字段
    if 'sign' not in content["metas"]:
        return -1
    
    # 因为有很多参数是选填项，那么就需要读取现在所有参过来的参数进行计算 MD5
    nowSign = content["metas"]['sign']

    # 这个跟顺序有关
    # proxy_name(name部分) + proxy_type + use_encryption + use_compression + remote_port + custom_domains + locations
    # 还有一些参数应该是空，但是都会进行拼接处理，所以不用显示出来
    cat_content = ''
    for item in content.keys():
        if item == 'user' or item == 'proxy_name' or item == 'metas':
            continue
        cat_content += str(content[item])
    proxy_name = content['proxy_name']
    name = proxy_name.split('.')[1]
    cat_content = name + cat_content
    calNowSign = CalMd5(cat_content)
    # 传过来的信息需要先能够计算出相应的 sign 值
    if nowSign != calNowSign:
        return -2
    # 传过来的信息的 sign 要与在服务器端录入的信息计算出来的 sign 一致
    nowUserName = content['user']['user']
    if calNowSign != UserInfo_dict[nowUserName].ProxyInfo.sign:
        return -3
    
    return 0

# 统一的回复
def Frp_Response(allow, reject_reason = "", unchange = True, content = ""):
    # 拒绝
    if allow == False:
        response = {
            "reject": True,
            "reject_reason": reject_reason
        }
    # 允许
    else:
        response = {
            "reject": False
        }
        # 直接允许，不修改内容
        if unchange == True:
            response['unchange'] = True
        # 允许，但是需要修改内容
        else:
            response.pop('reject')
            response['unchange'] = True
            response['content'] = content

    return json.dumps(response)

def Login_Process(content):
    iret = CheckUserInfo(content)
    if iret < 0:
        print('Login Error {0} -- '.format(iret) + content['user'])
        return Frp_Response(False, 'config file error {0}'.format(iret))
    print("Login -- " + content['user'])
    return Frp_Response(True)

def NewProxy_Process(content):
    iret = CheckUserInfo(content['user'])
    if iret < 0:
        print('NewProxy Error {0} -- '.format(iret) + content['user'])
        return Frp_Response(False, 'config file error {0}'.format(iret))

    iret = CheckProxyInfo(content)
    if iret < 0:
        print('NewProxy Error {0} -- '.format(iret) + content['user'])
        return Frp_Response(False, 'proxy config error {0}'.format(iret))
    print("NewProxy -- " + content['proxy_name'])
    return Frp_Response(True)

def Ping_Process(content):
    iret = CheckUserInfo(content['user'])
    if iret < 0:
        print("Ping Error {0}, Kick off -- ".format(iret) + content['user']['user'])
        return Frp_Response(False, 'config file error {0}'.format(iret))

    return Frp_Response(True)

def NewWorkConn_Process(content):
    print("NewWorkConn")
    print(content)
    return Frp_Response(True)

def NewUserConn_Process(content):
    print("NewUserConn")
    print(content)
    return Frp_Response(True)

@app.route("/handler", methods=["POST"])
def handler():
    nowJson = request.get_json()
    # 判断支持的插件版本版本
    if JugVersion(nowJson['version']) == False:
        print('Frps Plugin Version is ' + nowJson['version'] + ", This APP Supported Version is " + supportPluginVersion)
        return
    # 切换 OP 接口
    now_OP = nowJson['op']
    now_content = nowJson['content']
    # 登录
    if now_OP == 'Login':
        return Login_Process(now_content)
    # 新增代理
    elif now_OP == 'NewProxy':
        return NewProxy_Process(now_content)
    # 心跳
    elif now_OP == 'Ping':
        return Ping_Process(now_content)
    # 创建工作连接
    elif now_OP == 'NewWorkConn':
        return NewWorkConn_Process(now_content)
    # 创建用户连接，当有用户使用对应的代理的时候，就会触发此事件
    elif now_OP == 'NewUserConn':
        return NewUserConn_Process(now_content)
    # 找不到对应的 OP
    return Frp_Response(False, "op not supported.")

@app.route("/reflash", methods=["GET"])
def reflash():
    ReadTokenFromFile(config)
    return "Done."

if __name__ == "__main__":
    ReadTokenFromFile(config)
    app.run(
        host = '0.0.0.0',
        port = 5000
    )