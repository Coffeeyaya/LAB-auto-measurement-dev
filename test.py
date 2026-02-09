from pywinauto import Desktop

# get all top-level windows
windows = Desktop(backend="win32").windows()
for w in windows:
    print(w.window_text(), w.class_name())
