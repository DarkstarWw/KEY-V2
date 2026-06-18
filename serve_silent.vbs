' 静默启动：无任何可见窗口地起 Flask 服务 + cloudflared 隧道
' 双击本文件即可。公网地址生成后写入同目录 tunnel.log
Set sh = CreateObject("WScript.Shell")
base = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' 0 = 隐藏窗口，False = 不等待
sh.Run """" & base & "_run_server.bat""", 0, False
WScript.Sleep 4000
sh.Run """" & base & "_run_tunnel.bat""", 0, False
WScript.Sleep 6000

' 弹一次提示，告知日志位置（不弹也行，可删下面两行）
MsgBox "已在后台启动。" & vbCrLf & "公网地址见：" & base & "tunnel.log", 64, "图床已启动"
