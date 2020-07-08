# frp-flask-plugindemo

适用于 frp 0.33 版本，插件 0.1.0 版本

详细的插件开发文档请查看 frp 的[服务端插件](https://gofrp.org/docs/features/common/server-plugin/)文档

## 目的

测试插件模式下，通过额外的 meta 数据做到有验证的 Client 用户登录以及新增代理配置。

注意，示例仅做了单个用户单个代理的配置处理。

### 期望做到的效果

由 frps 这边的程序下发 Client 的配置信息，且做到一些关键信息无法被修改，那么就使用了 sign 这个字段去校验。如果有修改数据的情况，就会被踢下线。

注意，目前带宽的限制不在服务器实现的，也就无法拿到这个参数，同时就无法限制客户端不去修改这个参数。

## How

### 如何运行示例

请务必看 frp 的基本使用文档。

#### 正常情况的演示

1. 下载 0.33 版本的 frp

2. frp 的配置，使用本程序目录下的两个配置：

   1. frps_multiser.ini
   2. frpc_multiser_user.ini

   有需要请自行修改。使用 frpc 以及 frps 分别加载两份配置。

3. 打开 frps

4. flask 会读取 ClientInfos 文件夹中 ini 格式的配置文件，也就是允许登录的用户：

   1. user_00.ini
   2. user_01.ini

   如果自行修改登录信息后，注意，参考 app.py 中的 CalMd5 函数，把计算后的 sign 值填写到 frpc_multiser_user.ini 中，否则无法正确上线。

5. 运行 app.py

6. 运行 frpc

效果就是正常上线且能够新建代理和进行后续的代理端口的连接。

#### 异常情况的演示

1. 先按上面的运行起来
2. 假设只使用 frpc 启动了 user_00 的登录配置，那么请修改 user_00.ini 中的密码或者账号，保存
3. 用浏览器访问此连接 http://127.0.0.1:5000/reflash ，如果提示 Done ，那么就刷新数据成功
4. 应该就能看到这个用户被踢下线了，需要等一个 Ping 的周期

