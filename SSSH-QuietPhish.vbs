```vbscript
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Determine the directory containing this launcher
projectRoot = fso.GetParentFolderName(WScript.ScriptFullName)

' Locate the application and virtual environment
appDirectory = fso.BuildPath(projectRoot, "PhishGuard")
pythonPath = fso.BuildPath(appDirectory, ".venv\Scripts\pythonw.exe")

' Verify that Python exists
If Not fso.FileExists(pythonPath) Then
    MsgBox "QuietPhish virtual environment not found. Please complete installation first.", vbExclamation, "QuietPhish"
    WScript.Quit
End If

' Set application working directory
shell.CurrentDirectory = appDirectory

' Launch QuietPhish
shell.Run """" & pythonPath & """ -m flask --app ""phishguard.web.app:create_app"" run --host 127.0.0.1 --port 8081", 0, False

' Allow the server to initialize
WScript.Sleep 3000

' Open dashboard
shell.Run "http://127.0.0.1:8081", 1, False
```
