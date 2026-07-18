Option Explicit

Dim shell, fso, scriptDir, projectRoot, logDir
Dim frontendCommand, backendCommand

Sub KillPort(port)
    Dim process, regex, line, fields, localAddress, pid

    Set process = shell.Exec("cmd.exe /c netstat -ano")
    Set regex = CreateObject("VBScript.RegExp")
    regex.Pattern = "\s+"
    regex.Global = True

    Do Until process.StdOut.AtEndOfStream
        line = Trim(process.StdOut.ReadLine())
        If InStr(line, "LISTENING") > 0 Then
            fields = Split(regex.Replace(line, " "), " ")
            If UBound(fields) >= 4 Then
                localAddress = fields(1)
                If Right(localAddress, Len(CStr(port)) + 1) = ":" & CStr(port) Then
                    pid = fields(UBound(fields))
                    shell.Run "taskkill /F /PID " & pid, 0, True
                End If
            End If
        End If
    Loop
End Sub

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(scriptDir)
logDir = fso.BuildPath(projectRoot, "log")

If Not fso.FolderExists(logDir) Then
    fso.CreateFolder(logDir)
End If

KillPort 5000
KillPort 2453

frontendCommand = "title Frontend - Deploy & cd /d """ & projectRoot & """ && npm run build && npx vite preview --port 5000"
backendCommand = "title Backend - Deploy & cd /d """ & fso.BuildPath(projectRoot, "backend") & """ && set PYTHONUNBUFFERED=1&& uv run -m uvicorn app.main:app --port 2453 >> """ & fso.BuildPath(logDir, "backend.log") & """ 2>&1"

shell.Run "cmd.exe /c """ & frontendCommand & """", 0, False
shell.Run "cmd.exe /c """ & backendCommand & """", 0, False
