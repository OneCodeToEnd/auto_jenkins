# Jenkins 构建触发工具

这是一个通过 API 触发 Jenkins 构建的工具，构建完毕后并推送通知


## 配置文件

1. jenkins 用户名、token、地址
2. 邮箱配置

示例如下
```
[jenkins]
url = http://10.0.0.161:18080
user = dxie
token = 1137ce73adeb7d779056a39ea92aba5d0c

[email]
smtp_server = smtp.exmail.qq.com
smtp_port = 465
sender = 138279922343@qq.com
password = RoL8HMSkim2DtqGh
receiver = 138279922343@qq.com

```

## 如何使用

方式 1
```python
python quick_build.py my-service dev --no-wait
```


方式 2
```shell
build.sh   my-service dev --no-wait
```

方式 3

```shell
sudo ln -s ${pwd}/build.sh /usr/local/bin/jbuild
jbuild ocr-db-service develop
```

## 相关资源

- [Jenkins REST API 文档](https://www.jenkins.io/doc/book/using/remote-access-api/)
- [Python Requests 库](https://requests.readthedocs.io/)
- [SMTP 协议说明](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol)
