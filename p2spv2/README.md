

p2sp聊天程序的第二版本。使用asyncio，异步构建p2sp的聊天程序。主要是深入研究、理解python的异步IO编程，和网络聊天程序的设置。

异步完整版的p2sp聊天程序实现的主要功能有：

1.用户注册/登陆
2.用户能互加好友，创建群组，邀请好友进群，把群里面的踢出去。目前简单处理，加好友还需要确定，拉入群也不需要好友同意。
3.用户能给单个好友发送消息，也能在群里发送消息。
4.用户能查看自己好友列表，群体列表
5.支持管理用户的概念。管理用户也和普通用户一样进行登陆，不过可以执行的权限更多。比如广播、禁用用户等。


具体的功能说明和命令如下：

客户端：

- 用户注册。reg username 输入两次密码后，提交注册。如果该用户存在，则服务端返回命令提示用户名存在，重新注册。简化逻辑，暂时不对机器人注册做处理。
- 用户登陆。login username password.客户端输入该命令后，则可向服务端请求登陆。验证用户，返回登陆状态。这里，密码保存的问题，防止密码被破解，应该对密码加密。前期使用md5加密密码和数字库密码做比较。后期，需要考虑启用ssl的问题。登陆成功后，欢迎用户，并且显示可用的命令。登陆成功后 ，给用户发一个登陆的登陆key和用户关联起来。以后每次用户请求都需要使用该key进行身份验证。如果用户在其它地方登陆，强制下线。
- 增加好友.add username。用户发起增加好友请求，如果好友不存在，则提示好友不存在。如果，已经是好友，则提示用户已经为好友，可直接发送消息。增加成功，则提示好友增加成功。
- 发送消息 .send [username] [message] 给指定好友发送消息。需要对好友进行验证。
- 创建群组。newgroup [groupname]用户可以创建群组。当前用户最多可以创建10个群组。用户自己不能创建相同名称的群体。
- 删除群组。delgroup [groupname] 用户可删除自己创建的群组。删除后 ，应该提醒其它群组成员。
- 增加用户到群组。addgroupuser [groupname] [username]。管理员可以邀请某个用户到群组。只要用户存在就能邀请成功。
- 删除群组用户 delgroupuser [groupname] [username]。管理员可以删除群用户组。
- 群发消息。sendgroup grouptag [message] 。把消息群息群发给所有群组用户。
- 查看所有好友。friends.显示当前所有好友列表，并显示好友在线状态。
- 查看所有组。这里列表显示，用户的所有加的群组。显示编号（从1开始）,群组名,创建者、在线人数/总人数(1/3)。这里用户sendgroup的时候，使用的id则为本地的编号
- 实际上以创建者和群组为主键发送。

客户端的功能就大概如此：

管理员：

管理员本质上也是用户，所以拥有所有用户的功能。前提使用相同的客户端。在登陆的时候返回是否管理员的字段，以提示更多的的命令。管理员主动发送的消息都会系统消息。

- allusers .查看所有的用户，显示哪些用户是线的。可以使用online来仅显示在线用记.
- allgroup。显示所有的服务端的群组。显示界面和用户的一样。管理员可以在所有群里发送消息。
- adminsend [username] [message] 管理员发送消息给任何一个人。
- adminsendgroup [groupid] [message] 管理员给群组发送消息。
- blockuser [username].封禁某个的用户。
- blockgroup [createduser] [groupname] ，封禁某个群组。
- unblockuser [username] 解禁某个用户。
- unblockgroup  [createduser] [groupname] 解禁某个群组。

## 实现

所有消息使用自定义二进制结构进行，但消息类型都放在payload里面，可以参考protocol.py为解少复杂度。但需要抽象ReqeustMesage,ResponseMessage封装更多的普通请求或者影应信息。比如在ReqeustMessage里面封装token等。

能支持离线消息，所以所有用户的群发或者单发，关键的系统通知，广播等，用户在线的时候当前及时分发。如果用户不在线，则存储在队列中。用户上线时，统计一切性发给用户。

后端数据采用sqlite存储，目前查询直接走数据库暂时不考虑缓存。使用sqlalchemy操作数据库。主要的几个表如下：

users 用户标识
uesrname 用户名 用户标识，不为空.
userpassword 用户密码.md5存储在数据库
userstatus 用户状态。1正常。0，禁用。
createtime 用户创建的时间。
isadmin 是否有管理员
authtoken 用户授权的token(要设置一个索引，每次用户登陆的时候更新)

user_login_log 用户登陆日志
uerid,
username,
lastlogintime 最后登陆的时间。
lastloginip 最后登陆的ip(理当要存在登陆日志中)

groups 用户群组表

groupid 群体标识
groupname 群体名
createuserid 创建者用户id 
createtime 群组创建时间
groupusercount 群组的用户数

group_users 群组的用户
id 标识自增长id
groupid 群组标识
userid 用户标识

这里创建者应该是第一默认的群组用户.


数据访问的相关的声明可以定义一个serverdb.py来封装.

对客户端，服务端消息的处理应该封装到不同的处理类。比如ServerMessagerHandler,ClientMessageHandler.
