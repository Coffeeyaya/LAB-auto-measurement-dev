

---

### **What `poll()` does**

* **Syntax:**

```python
return_code = process.poll()
```

* **Purpose:**

  * Checks if the subprocess has **finished running**.
  * Does **not wait**; it returns immediately.

* **Return values:**

  1. `None` → The process is still running.
  2. An integer → The process has finished; the integer is the exit code (0 usually means success, non-zero means error).

---

### **Example**

```python
import subprocess
import time

proc = subprocess.Popen(["python", "some_script.py"])

while True:
    status = proc.poll()
    if status is None:
        print("Still running...")
        time.sleep(1)
    else:
        print("Finished with exit code:", status)
        break
```

* This loop **keeps checking** without blocking the rest of your program.

---

### **How it’s used in `kill_script`**

```python
if proc.poll() is None:  # still running
    # terminate the process
```

* Checks if the script is **still active** before trying to kill it.
* Prevents errors from trying to kill a process that has already finished.

---

So in short:

* `poll()` → non-blocking “is the subprocess done?”
* Returns `None` if still running, exit code if finished.

---
