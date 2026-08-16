from __future__ import annotations

from kis_mcp.shell_parser import output_redirection_targets


def test_output_redirection_targets_ignore_quoted_operators() -> None:
    assert output_redirection_targets(
        'Write-Output "literal > text"', shell="powershell"
    ) == ()


def test_output_redirection_targets_ignore_escaped_operators() -> None:
    assert output_redirection_targets(r"echo literal ^> text", shell="cmd") == ()
    assert output_redirection_targets(
        r"Write-Output literal `> text", shell="powershell"
    ) == ()


def test_output_redirection_targets_preserve_actual_target_text() -> None:
    assert output_redirection_targets(
        r'echo test > "C:\Windows\Temp\output file.txt"', shell="cmd"
    ) == (r"C:\Windows\Temp\output file.txt",)
    assert output_redirection_targets(
        r"Write-Output test >> .\output.txt", shell="powershell"
    ) == (r".\output.txt",)


def test_output_redirection_targets_preserve_powershell_mixed_quote_context() -> None:
    first = "''" + "$env:USERPROFILE" + r"'\out.txt'"
    second = "'prefix'" + "$env:USERPROFILE" + "'suffix'"
    assert output_redirection_targets(
        "echo data > " + first,
        shell="powershell",
    ) == (first,)
    assert output_redirection_targets(
        "echo data > " + second,
        shell="powershell",
    ) == (second,)
