[
    {
        "Case":  "invalid-upload-and-capacity",
        "StartedUtc":  "2026-09-09T07:12:32.5676728Z",
        "FinishedUtc":  "2026-09-09T07:12:35.5181431Z",
        "Passed":  true,
        "ExitCode":  0,
        "Cleanup":  "pytest subprocess completed; temporary test state is fixture-scoped",
        "LeaksScan":  true,
        "Output":  ".......                                                                  [100%] 7 passed in 1.79s uv.exe : Exception ignored in atexit callback: \u003cfunction cleanup_numbered_dir at 0x0000020109CE31A0\u003e At \u003cproject\u003e\\scripts\\windows\\run_operations_matrix.ps1:38 char:19 + ...   $output = \u0026 uv run --project apps/api python -m pytest $entry.Value ... +                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (Exception ignor...00020109CE31A0\u003e:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError   Traceback (most recent call last):   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  374, in cleanup_numbered_dir     cleanup_dead_symlinks(root)   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  359, in cleanup_dead_symlinks     if not left_dir.resolve().exists():            ^^^^^^^^^^^^^^^^^^^^^^^^^^^   File \"\u003cprivate-path\u003e\", line 860, in exists     self.stat(follow_symlinks=follow_symlinks)   File \"\u003cprivate-path\u003e\", line 840, in stat     return os.stat(self, follow_symlinks=follow_symlinks)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PermissionError: [WinError 5] Access is denied:  \u0027\u003cprivate-path\u003e\u0027"
    },
    {
        "Case":  "queue-and-cancellation",
        "StartedUtc":  "2026-09-09T07:12:35.5368331Z",
        "FinishedUtc":  "2026-09-09T07:12:37.1725145Z",
        "Passed":  true,
        "ExitCode":  0,
        "Cleanup":  "pytest subprocess completed; temporary test state is fixture-scoped",
        "LeaksScan":  true,
        "Output":  "...                                                                      [100%] 3 passed in 0.82s uv.exe : Exception ignored in atexit callback: \u003cfunction cleanup_numbered_dir at 0x000002949BB231A0\u003e At \u003cproject\u003e\\scripts\\windows\\run_operations_matrix.ps1:38 char:19 + ...   $output = \u0026 uv run --project apps/api python -m pytest $entry.Value ... +                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (Exception ignor...0002949BB231A0\u003e:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError   Traceback (most recent call last):   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  374, in cleanup_numbered_dir     cleanup_dead_symlinks(root)   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  359, in cleanup_dead_symlinks     if not left_dir.resolve().exists():            ^^^^^^^^^^^^^^^^^^^^^^^^^^^   File \"\u003cprivate-path\u003e\", line 860, in exists     self.stat(follow_symlinks=follow_symlinks)   File \"\u003cprivate-path\u003e\", line 840, in stat     return os.stat(self, follow_symlinks=follow_symlinks)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PermissionError: [WinError 5] Access is denied:  \u0027\u003cprivate-path\u003e\u0027"
    },
    {
        "Case":  "restart-and-dependency-recovery",
        "StartedUtc":  "2026-09-09T07:12:37.1725145Z",
        "FinishedUtc":  "2026-09-09T07:12:40.0515481Z",
        "Passed":  true,
        "ExitCode":  0,
        "Cleanup":  "pytest subprocess completed; temporary test state is fixture-scoped",
        "LeaksScan":  true,
        "Output":  ".......                                                                  [100%] 7 passed in 2.04s uv.exe : Exception ignored in atexit callback: \u003cfunction cleanup_numbered_dir at 0x000002B0399031A0\u003e At \u003cproject\u003e\\scripts\\windows\\run_operations_matrix.ps1:38 char:19 + ...   $output = \u0026 uv run --project apps/api python -m pytest $entry.Value ... +                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (Exception ignor...0002B0399031A0\u003e:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError   Traceback (most recent call last):   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  374, in cleanup_numbered_dir     cleanup_dead_symlinks(root)   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  359, in cleanup_dead_symlinks     if not left_dir.resolve().exists():            ^^^^^^^^^^^^^^^^^^^^^^^^^^^   File \"\u003cprivate-path\u003e\", line 860, in exists     self.stat(follow_symlinks=follow_symlinks)   File \"\u003cprivate-path\u003e\", line 840, in stat     return os.stat(self, follow_symlinks=follow_symlinks)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PermissionError: [WinError 5] Access is denied:  \u0027\u003cprivate-path\u003e\u0027"
    },
    {
        "Case":  "submission-bounds-and-cleanup",
        "StartedUtc":  "2026-09-09T07:12:40.0515481Z",
        "FinishedUtc":  "2026-09-09T07:12:42.4509215Z",
        "Passed":  true,
        "ExitCode":  0,
        "Cleanup":  "pytest subprocess completed; temporary test state is fixture-scoped",
        "LeaksScan":  true,
        "Output":  "....                                                                     [100%] 4 passed in 1.54s uv.exe : Exception ignored in atexit callback: \u003cfunction cleanup_numbered_dir at 0x0000013174BE31A0\u003e At \u003cproject\u003e\\scripts\\windows\\run_operations_matrix.ps1:38 char:19 + ...   $output = \u0026 uv run --project apps/api python -m pytest $entry.Value ... +                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (Exception ignor...00013174BE31A0\u003e:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError   Traceback (most recent call last):   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  374, in cleanup_numbered_dir     cleanup_dead_symlinks(root)   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  359, in cleanup_dead_symlinks     if not left_dir.resolve().exists():            ^^^^^^^^^^^^^^^^^^^^^^^^^^^   File \"\u003cprivate-path\u003e\", line 860, in exists     self.stat(follow_symlinks=follow_symlinks)   File \"\u003cprivate-path\u003e\", line 840, in stat     return os.stat(self, follow_symlinks=follow_symlinks)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PermissionError: [WinError 5] Access is denied:  \u0027\u003cprivate-path\u003e\u0027"
    },
    {
        "Case":  "nginx-upstream-timeout-upload-host",
        "StartedUtc":  "2026-09-09T07:12:42.4509215Z",
        "FinishedUtc":  "2026-09-09T07:12:45.5290353Z",
        "Passed":  true,
        "ExitCode":  0,
        "Cleanup":  "pytest subprocess completed; temporary test state is fixture-scoped",
        "LeaksScan":  true,
        "Output":  "..                                                                       [100%] 2 passed in 2.40s uv.exe : Exception ignored in atexit callback: \u003cfunction cleanup_numbered_dir at 0x000001EAC28831A0\u003e At \u003cproject\u003e\\scripts\\windows\\run_operations_matrix.ps1:38 char:19 + ...   $output = \u0026 uv run --project apps/api python -m pytest $entry.Value ... +                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (Exception ignor...0001EAC28831A0\u003e:String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError   Traceback (most recent call last):   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  374, in cleanup_numbered_dir     cleanup_dead_symlinks(root)   File \"\u003cproject\u003e\\apps\\api\\.venv\\Lib\\site-packages\\_pytest\\pathlib.py\", line  359, in cleanup_dead_symlinks     if not left_dir.resolve().exists():            ^^^^^^^^^^^^^^^^^^^^^^^^^^^   File \"\u003cprivate-path\u003e\", line 860, in exists     self.stat(follow_symlinks=follow_symlinks)   File \"\u003cprivate-path\u003e\", line 840, in stat     return os.stat(self, follow_symlinks=follow_symlinks)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PermissionError: [WinError 5] Access is denied:  \u0027\u003cprivate-path\u003e\u0027"
    }
]
