# Alas修改版，适用于云


## 相较于原版Alas


* 合并了一个奇怪的库


* 将GamePageUnknownError和RequestHumanTakeover写入重启，重启一次后再运行上次未完成的任务如果依旧报错则抛出错误并用OnePush通知(如果有设置OnePush的话)


## 注意事项

请勿开启在不小开情况下打不过的项目，防止资源浪费，特别是大世界的某些项目     
         
 <br />
 
 <br />

# 小开特供版Alas：

## 相较于原版Alas
- 加入了`特别的东西`，可能有用？
- 将`GamePageUnknownError`和`RequestHumanTakeover`写入重启，重启一次后再运行上次未完成的任务如果依旧报错则抛出错误并用OnePush通知(如果有设置OnePush的话)
- 将`优化设置`中的`放慢截图速度至 X 秒一张`和`战斗中放慢截图速度至 X 秒一张`的时间限制分别从`0.1 ~ 0.3`和`0.1 ~ 1.0`放宽至`0.1 ~ 2.0`和`0.1 ~ 5.0`
- 将`GameStuckError`中`无操作连续截图超过 1 分钟`放宽至`3 分钟`
- 修复了在云端时由于网络延迟所导致的换装备时卡住(目前还在测试)
- 修复了在云端时战术学院选择舰船时的bug(由于难以复现，目前还在观察测试)

## 注意事项
- 不建议开启`大世界`中的`深渊海域` `塞壬要塞` `月度Boss`，因为修改了部分异常处理，导致我也不知道会发生什么，要开就做好**资源可能会被浪费**的准备
