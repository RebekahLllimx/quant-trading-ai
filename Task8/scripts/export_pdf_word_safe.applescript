on run argv
    set inputPath to item 1 of argv
    set outputPath to item 2 of argv
    with timeout of 300 seconds
        tell application "Microsoft Word"
            set display alerts to alerts none
            set docRef to open (POSIX file inputPath)
            delay 3
            save as docRef file name outputPath file format format PDF
            close docRef saving no
        end tell
    end timeout
end run
