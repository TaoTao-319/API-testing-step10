# 接口说明

以下内容依据 `local-api/server.py` 的实现整理。基础地址为 `http://127.0.0.1:8000`，请求和响应数据使用 JSON。

## 接口列表

| 方法 | 路径 | 鉴权 | 成功结果 |
|---|---|---|---|
| GET | `/ping` | 不需要 | 200，`{"status":"ok"}` |
| POST | `/auth` | 提交账号密码 | 200，`{"token":"…"}` |
| GET | `/booking` | 不需要 | 200，`[{"bookingid":1}]`，无匹配时为 `[]` |
| POST | `/booking` | 不需要 | 200，`{"bookingid":1,"booking":{…}}` |
| GET | `/booking/{id}` | 不需要 | 200，直接返回预约对象 |
| PUT | `/booking/{id}` | 有效 token Cookie | 200，直接返回更新后的预约对象 |
| DELETE | `/booking/{id}` | 有效 token Cookie | 201，`{"message":"Booking deleted"}` |

创建返回 200、删除返回 201 是这个演示服务的具体约定，不是所有 HTTP 接口的通用规则。

## 身份认证

向 `/auth` 发送 POST 请求，Body 为：

```json
{
  "username": "admin",
  "password": "password123"
}
```

建议设置 `Content-Type: application/json`。正确凭证返回随机 token，错误凭证返回 401。token 不会由服务器自动设置为浏览器 Cookie；测试请求需要主动发送：

```text
Cookie: token={{token}}
```

在 Postman Headers 表格中，Key 填 `Cookie`，Value 填 `token={{token}}`。此服务不通过 Bearer Token 或 Basic Auth 验证更新、删除请求。

## 预约字段

POST 创建和 PUT 更新都需要完整的必填字段。PUT 会整体替换原预约对象。

| 字段 | 类型 | 必填 | 当前校验 |
|---|---|---|---|
| `firstname` | 字符串 | 是 | 检查类型 |
| `lastname` | 字符串 | 是 | 检查类型 |
| `totalprice` | 整数 | 是 | 必须是整数，布尔值不算整数 |
| `depositpaid` | 布尔值 | 是 | 使用 `true` 或 `false` |
| `bookingdates` | 对象 | 是 | 包含以下两个字符串字段 |
| `bookingdates.checkin` | 字符串 | 是 | 不验证真实日期 |
| `bookingdates.checkout` | 字符串 | 是 | 不验证真实日期或日期顺序 |
| `additionalneeds` | 字符串 | 否 | 若提供则检查类型 |

可使用“创建预约”请求中的 JSON 作为创建模板。
更新请求保留完整字段，将 `totalprice` 改为 300。

创建响应包含外层 `bookingid` 和内层 `booking`；详情查询及更新响应直接包含 `firstname`、`totalprice` 等字段。因此创建断言使用 `data.booking.totalprice`，查询及更新断言使用 `data.totalprice`。

## 姓名筛选

GET `/booking` 支持 `firstname` 和 `lastname` 查询参数，采用区分大小写的精确匹配；同时提供两个参数时，两个条件都必须满足。

在 Postman Params 中填写字段和值即可。筛选值应与创建请求中的值一致。其他查询参数目前不会参与筛选。

## 错误响应

| 状态码 | 示例情况 |
|---|---|
| 400 | JSON 无法解析、缺少预约必填字段、字段类型错误 |
| 401 | `/auth` 提交错误账号密码 |
| 403 | 更新或删除未提供有效 token Cookie |
| 404 | 预约不存在或路径不存在 |

错误响应使用 `{"error":"错误说明"}` 格式。PUT 和 DELETE 在检查指定预约是否存在前，会先检查 token，因此无有效 token 时，即便编号不存在也会返回 403。

服务没有实现 PATCH、HEAD、OPTIONS 的业务处理。token 仅在当前进程中有效，没有定时过期机制；停止再启动服务器后，所有 token 和预约都会清空。
