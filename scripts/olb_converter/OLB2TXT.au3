; <AUT2EXE VERSION: 3.1.1.0>
; Language:       English
; Platform:       WinXP

; Prompt the user to run the script with a Yes/No prompt
$answer = MsgBox(4, "Make Bible", "This script will copy and paste OLB verses into a text editor 50 times per loop. Make sure OLB is running and the Bible version that you want is loaded. Also make sure you have Bibletext.txt open. Run?")

; Check the user's answer to the prompt
; If "No" was clicked (7) then exit the script
If $answer = 7 Then
    MsgBox(0, "AutoIt", "OK.  Bye!")
    Exit
EndIf

; This sets the delay for window switching. Higher = slower.
Opt("WinTitleMatchMode", 2)

; This sets the keystroke speed. Higher = slower.
Opt("SendKeyDelay", 25)

Local $i = 0
Do

WinActivate("Passage","")
WinWait("Passage","")

send("{h}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")
send("{n}")
send("{Down}")

WinActivate("bibletext","")
WinWait("bibletext","")
Send("^v")
send("{Enter}")
send("{Enter}")

; Repeat 623 times if you want to copy paste an entire public domain Bible (31102 verses)
    $i = $i + 1
Until $i = 2

; Finished!
MsgBox(0, "AutoIt Example", "Finished!")


