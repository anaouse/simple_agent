Option Explicit

Dim shell, fso, scriptDir, projectRoot, logDir
Dim frontendCommand, backendCommand

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(scriptDir)
logDir = fso.BuildPath(projectRoot, "log")

If Not fso.FolderExists(logDir) Then
    fso.CreateFolder(logDir)
End If

frontendCommand = "title Frontend - Deploy & cd /d """ & projectRoot & """ && npm run build && npx vite preview --port 5000"
backendCommand = "title Backend - Deploy & cd /d """ & fso.BuildPath(projectRoot, "backend") & """ && set PYTHONUNBUFFERED=1&& uv run -m uvicorn app.main:app --port 2453 >> """ & fso.BuildPath(logDir, "backend.log") & """ 2>&1"

shell.Run "cmd.exe /c """ & frontendCommand & """", 0, False
shell.Run "cmd.exe /c """ & backendCommand & """", 0, False
