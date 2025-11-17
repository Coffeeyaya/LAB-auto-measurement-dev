
---

# **`python -m` explained**

The `-m` flag in Python lets you **run a module as a script**, instead of specifying a `.py` file directly.

---

### **Basic syntax**

```bash
python -m module_name [args...]
```

**Key points:**

1. `module_name` **must be a Python module or package**.

   * A module is usually a `.py` file.
   * A package is a folder with an `__init__.py`.

2. You **do not include `.py`** when using `-m`.

   * Wrong: `python -m server.py`
   * Correct: `python -m server` (or `python -m test.server` if inside a package)

3. The **current directory** is added to `sys.path`, so Python can find your modules/packages.

---

### **Why `-m` is useful**

1. **Run a script inside a package**
   Suppose you have:

```
project/
│
├── package/
│   ├── __init__.py
│   └── module.py
└── script.py
```

You can run `module.py` like this:

```bash
cd project
python -m package.module
```

Without `-m`, Python might not handle **relative imports** inside the package.

2. **Handles relative imports correctly**
   If `module.py` contains:

```python
from .submodule import func
```

* Running `python package/module.py` **directly** fails.
* Running `python -m package.module` works perfectly.

3. **Consistency**

   * Lets you run Python modules the same way on any system.
   * Avoids messing with `PYTHONPATH` or modifying `sys.path` in code.

---

### **Examples**

1. Run a standard library module:

```bash
python -m http.server 8000
```

2. Run your script inside a package:

```bash
python -m test.server
```

3. Pass command-line arguments to the module:

```bash
python -m test.server --port 8080
```

---

### **Common mistakes**

| Mistake                              | Why it fails                                   | Correct way             |
| ------------------------------------ | ---------------------------------------------- | ----------------------- |
| `python -m server.py`                | Python treats `.py` as part of the module name | `python -m test.server` |
| Running from the wrong directory     | `sys.path` does not include project root       | `cd measure` first      |
| No `__init__.py` in a package folder | Python doesn’t treat folder as a package       | Add `__init__.py`       |

---

