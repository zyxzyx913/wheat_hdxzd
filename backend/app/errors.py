"""向用户提供可操作的中文错误，不泄露系统路径或堆栈。"""


class AnalysisError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
