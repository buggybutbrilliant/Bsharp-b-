# B# Core — shared types used by all modules

class BSharpError(Exception):
    def __init__(self, msg, line=0):
        self.bsharp_message = msg; self.line = line; super().__init__(msg)
    def friendly(self):
        return f"Error{f' (line {self.line})' if self.line else ''}: {self.bsharp_message}"

class BSharpReturn(Exception):
    def __init__(self, v): self.value = v

class ModuleObject:
    def __init__(self, name, exports):
        self.name = name; self.exports = exports