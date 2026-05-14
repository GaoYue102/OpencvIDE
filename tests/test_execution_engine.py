"""执行引擎测试。"""
import time
import numpy as np

from core.execution_engine import ExecutionEngine


def _wait_for_signal(qapp, check_fn, timeout=3.0):
    """轮询 Qt 事件循环直到 check_fn() 返回 True 或超时。"""
    deadline = time.time() + timeout
    while not check_fn() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.05)
    return check_fn()


class TestExecutionEngine:

    def test_init_state(self, qapp):
        engine = ExecutionEngine()
        assert engine.get_all_variables() == {}

    def test_set_source(self, qapp):
        engine = ExecutionEngine()
        engine.set_source("x = 42")
        assert engine._source == "x = 42"

    def test_run_simple_script(self, qapp):
        """测试运行简单脚本，验证变量捕获。"""
        engine = ExecutionEngine()
        engine.set_source("a = 1 + 2\nb = a * 10")

        results = {"line_nos": [], "finished": False, "errors": []}

        def on_line(no):
            results["line_nos"].append(no)

        def on_finished():
            results["finished"] = True

        def on_error(msg, line):
            results["errors"].append((msg, line))

        engine.line_reached.connect(on_line)
        engine.execution_finished.connect(on_finished)
        engine.execution_error.connect(on_error)

        engine.start()
        engine.run_continuously()

        _wait_for_signal(qapp, lambda: results["finished"] or results["errors"], timeout=3.0)

        # 再给一点时间处理剩余信号
        for _ in range(10):
            qapp.processEvents()
            time.sleep(0.02)

        if engine.isRunning():
            engine.stop()
            engine.wait(1000)

        assert not results["errors"], f"Unexpected errors: {results['errors']}"
        assert len(results["line_nos"]) >= 1, f"Got line_nos: {results['line_nos']}"

    def test_image_variable_detection(self, qapp):
        """测试图像变量检测。"""
        engine = ExecutionEngine()
        engine.set_source(
            "import numpy as np\n"
            "img = np.zeros((10, 10, 3), dtype=np.uint8)\n"
            "img2 = np.ones((5, 5), dtype=np.uint8)\n"
        )

        images = []
        finished = [False]

        def on_image(name, img):
            images.append((name, img.shape))

        def on_finished():
            finished[0] = True

        engine.new_image_detected.connect(on_image)
        engine.execution_finished.connect(on_finished)

        engine.start()
        engine.run_continuously()

        _wait_for_signal(qapp, lambda: finished[0], timeout=3.0)

        for _ in range(10):
            qapp.processEvents()
            time.sleep(0.02)

        if engine.isRunning():
            engine.stop()
            engine.wait(1000)

        assert len(images) >= 1, f"Got {len(images)} images: {images}"
        names = [n for n, _ in images]
        assert "img" in names

    def test_step_mode(self, qapp):
        """测试单步模式暂停/继续。"""
        engine = ExecutionEngine()
        engine.set_source("x = 1\ny = 2\nz = 3")

        paused = [False]

        def on_paused():
            paused[0] = True

        engine.execution_paused.connect(on_paused)

        engine.start()
        engine.step()

        _wait_for_signal(qapp, lambda: paused[0], timeout=3.0)
        assert paused[0], "Should have paused after first step"

        engine.run_continuously()
        engine.wait(3000)
        if engine.isRunning():
            engine.stop()
            engine.wait(1000)

    def test_stop(self, qapp):
        """测试手动停止。"""
        engine = ExecutionEngine()
        engine.set_source("x = 1\n")

        engine.start()
        engine.run_continuously()
        engine.wait(3000)

    def test_reset(self, qapp):
        """测试重置。"""
        engine = ExecutionEngine()
        engine.set_source("x = 42")
        engine.start()
        engine.run_continuously()
        engine.wait(3000)

        engine.reset()
        engine.set_source("y = 99")

        assert engine.get_all_variables() == {}
        assert engine._source == "y = 99"

    def test_get_variable(self, qapp):
        """测试 get_variable。"""
        engine = ExecutionEngine()
        engine.set_source("x = 42\ny = 'hello'")

        finished = [False]

        def on_finished():
            finished[0] = True

        engine.execution_finished.connect(on_finished)

        engine.start()
        engine.run_continuously()

        _wait_for_signal(qapp, lambda: finished[0], timeout=3.0)

        for _ in range(10):
            qapp.processEvents()
            time.sleep(0.02)

        if engine.isRunning():
            engine.stop()
            engine.wait(1000)

        assert engine.get_variable("x") == 42
        assert engine.get_variable("y") == "hello"
