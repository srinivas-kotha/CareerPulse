"""Prevent two server processes from scheduling the same private installation."""
import os


class InstallationLock:
    def __init__(self, root):
        self.file = (root / 'server.lock').open('a+b')
        try:
            self.file.seek(0, 2)
            if self.file.tell() == 0:
                self.file.write(b'0')
                self.file.flush()
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise RuntimeError('This candidate data root is already running in another server') from exc

    def close(self):
        self.file.close()  # OS releases the lock, including after a crash.
