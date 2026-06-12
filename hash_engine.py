"""
HashEngine — 后台哈希计算线程
==============================
在独立的工作线程中分块读取文件并计算哈希值，计算期间不阻塞 UI。

为什么不直接在 UI 线程中计算？
  - 如果文件很大（几个 GB），计算可能需要数秒甚至数十秒。
  - 如果在主线程（UI 线程）中做这件事，窗口会"卡死"——无法移动、
    无法点击、Windows 会显示"未响应"。
  - 解决方案：继承 QThread，在 run() 中执行耗时计算。

线程通信机制:
  本类定义三个 Qt Signal:
    - progress(int):   每 1% 进度变化时发射，更新进度条
    - result(str):     计算完成时发射，携带十六进制哈希字符串
    - error(str):      出错时发射，携带错误描述
  Qt 自动将这些跨线程信号投递到主线程的事件循环，因此槽函数
  可以安全地更新 UI 控件（PySide6 内部做了线程安全处理）。

支持的算法:
  - SHA-256:   输出 256 位（64 个十六进制字符），最常用的安全哈希算法
  - SHA-3:     输出 512 位（128 个十六进制字符），新一代 NIST 标准

取消机制:
  通过 _cancelled 标志实现协作式取消。调用 cancel() 设置标志，
  线程在每次读取新块前检查该标志，如果为 True 则静默退出。
  这是 QThread 推荐的做法，比强制 terminate() 安全得多。
"""

import hashlib  # Python 标准库，提供 SHA-256、SHA-3 等哈希算法
import os

from PySide6.QtCore import QThread, Signal


class HashEngine(QThread):
    """
    后台哈希计算线程。

    使用方式:
      engine = HashEngine("/path/to/file.iso", "sha256")
      engine.progress.connect(my_progress_handler)   # 可选
      engine.result.connect(my_result_handler)       # 接收计算结果
      engine.error.connect(my_error_handler)          # 可选
      engine.start()   # QThread.start() → 内部调用 run()

    QThread 生命周期:
      start() → run() 在工作线程中执行 → 自动 emit finished 信号
    """

    # ---- Qt Signal 定义 ----
    # 在类体级别定义（不是 __init__ 中），这是 Qt 元对象系统的要求。
    # Signal 实例会被 Qt 的 moc（元对象编译器）处理，注册到信号/槽系统中。

    # 进度信号: 0-100 的整数百分比
    progress = Signal(int)

    # 结果信号: 携带十六进制哈希字符串，如 "a1b2c3d4e5f6..."
    result = Signal(str)

    # 错误信号: 携带人类可读的错误描述
    error = Signal(str)

    # ---- 支持的哈希算法 ----
    # 字典结构使得添加新算法变得简单：只需增加一行。
    # key: 内部使用的算法标识符
    # value: (用户界面上显示的名称, hashlib 的构造器函数)
    ALGORITHMS = {
        "sha256":   ("SHA-256",   hashlib.sha256),    # 256 位输出，64 个 hex 字符
        "sha3_512": ("SHA-3",     hashlib.sha3_512),   # 512 位输出，128 个 hex 字符
    }

    # 每次读取的块大小：64 KB
    # 这是一个权衡——太小会导致过多的 IO 操作和信号发射；
    # 太大则进度更新不够平滑，取消响应也不够及时。
    CHUNK_SIZE = 64 * 1024  # 64 * 1024 = 65536 字节

    def __init__(self, file_path: str, algorithm: str, parent=None):
        """
        Args:
            file_path: 要计算哈希的文件绝对路径
            algorithm: 算法 key，必须是 ALGORITHMS 字典中的键（如 'sha256'）
            parent: Qt 父子关系（用于自动内存管理，一般传 None）
        """
        super().__init__(parent)
        self._file_path = file_path
        self._algorithm = algorithm
        self._cancelled = False  # 取消标志，线程安全（Python GIL 保护 bool 赋值）

    # ------------------------------------------------------------------
    # Public API（从主线程调用）
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """
        请求取消当前计算。

        注意: 这不会立即停止线程，只是设置一个标志。
        线程在下一轮读块循环时检查到该标志，然后静默退出。
        在 Python 中 bool 赋值是原子的（受 GIL 保护），因此跨线程安全。
        """
        self._cancelled = True

    @property
    def algorithm_key(self) -> str:
        """返回当前使用的算法 key（如 'sha256'）。"""
        return self._algorithm

    @property
    def algorithm_label(self) -> str:
        """
        返回算法的用户友好名称（如 'SHA-256'）。

        如果传入的算法 key 不在 ALGORITHMS 中（理论上不会发生），
        则回退显示原始的 key 字符串。
        """
        # .get() 的第二个参数是找不到 key 时的默认值
        # 这里取了 ALGORITHMS 中 value 元组的第一个元素（算法名称）
        return self.ALGORITHMS.get(self._algorithm, (self._algorithm,))[0]

    # ------------------------------------------------------------------
    # 线程体（在工作线程中执行）
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        QThread 的工作入口，在 start() 调用后于新线程中执行。

        执行流程:
          1. 验证算法是否支持
          2. 验证文件是否存在且非空
          3. 以 64KB 为块大小循环读取文件
          4. 每一块调用 hasher.update() 增量更新哈希值
          5. 每 1% 进度变化时 emit progress 信号
          6. 读取完毕 → emit result(hex_digest)
          7. 任何异常 → emit error(message)

        块读取哈希的原理:
          不需要一次性把整个文件加载到内存。hashlib 支持增量计算:
            hasher = hashlib.sha256()
            hasher.update(block1)
            hasher.update(block2)
            ...
            result = hasher.hexdigest()   # 等价于一次性计算整个文件的哈希
          这使得我们可以处理任意大小的文件（甚至超过可用 RAM）。
        """
        # ---- 阶段 1: 验证算法 ----
        try:
            algo_name, hasher_factory = self.ALGORITHMS[self._algorithm]
        except KeyError:
            # 算法 key 不在字典中（可能是代码 bug 或未来版本不兼容）
            self.error.emit(f"不支持的算法: {self._algorithm}")
            return

        # ---- 阶段 2: 验证文件 ----
        if not os.path.isfile(self._file_path):
            self.error.emit(f"文件不存在: {self._file_path}")
            return

        # 获取文件大小（用于计算进度百分比）
        file_size = os.path.getsize(self._file_path)
        if file_size == 0:
            # 空文件没有内容可做哈希，虽然有技术上的空哈希值，但实际使用无意义
            self.error.emit("文件为空，无法计算哈希值。")
            return

        # ---- 阶段 3: 分块读取 + 增量计算 ----
        # hasher_factory() 调用返回一个新的哈希对象，例如 hashlib.sha256()
        hasher = hasher_factory()
        bytes_read = 0      # 已读取的字节数（用于进度计算）
        last_pct = -1        # 上一次发射的进度值（用于节流，避免重复发射）

        try:
            # 以二进制读模式打开文件（rb = read binary）
            # with 语句确保无论发生什么，文件都会被正确关闭
            with open(self._file_path, "rb") as fh:
                while True:
                    # ---- 取消检查 ----
                    # 在每次 IO 操作前检查取消标志，使得取消响应延迟
                    # 不超过一个 CHUNK_SIZE 的读取时间（非常短）。
                    if self._cancelled:
                        return  # 静默退出，不 emit 任何信号

                    # 读取一个块
                    chunk = fh.read(self.CHUNK_SIZE)
                    if not chunk:
                        # read() 返回空字节表示已到文件末尾
                        break

                    # 将这一块数据喂给哈希对象（增量计算的核心）
                    hasher.update(chunk)
                    bytes_read += len(chunk)

                    # ---- 进度发射（带节流） ----
                    # 进度发射被"节流"到每 1% 变化一次，避免频繁发射信号。
                    # 对于大文件，如果没有节流，64KB 的块会导致成千上万次
                    # 信号发射，浪费 UI 线程资源。
                    pct = int(bytes_read * 100 / file_size)
                    if pct != last_pct:
                        last_pct = pct
                        self.progress.emit(pct)

            # ---- 阶段 4: 最终进度 + 结果 ----
            # 确保进度条走到 100%（某些边界情况可能漏掉最后一次发射）
            if last_pct != 100:
                self.progress.emit(100)

            # hexdigest() 返回十六进制字符串，例如:
            #   SHA-256: "e3b0c44298fc1c14..." (64 个字符)
            #   SHA-3:   "a69f73cca23a..."     (128 个字符)
            digest = hasher.hexdigest()
            self.result.emit(digest)

        except PermissionError:
            # 文件存在但没有读权限（Windows 上较少见，但可能发生）
            self.error.emit("没有权限读取该文件。")
        except OSError as exc:
            # 操作系统级 IO 错误：磁盘故障、网络断开（如果是网络路径）、文件被锁定等
            self.error.emit(f"读取文件时出错: {exc}")
        except Exception as exc:
            # 兜底异常处理：捕获所有未预见的异常，确保线程不会静默崩溃
            self.error.emit(f"计算哈希时发生意外错误: {exc}")
