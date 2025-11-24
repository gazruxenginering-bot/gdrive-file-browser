Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Tunggu 3 detik agar server Flask siap
WScript.Sleep 3000

' Buka browser ke localhost
objShell.Run "http://127.0.0.1:5000", 3, False