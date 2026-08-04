Set-StrictMode -Version Latest

if (-not ('KisMcp.NativeCredential' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

namespace KisMcp {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct NativeCredentialStruct {
        public uint Flags;
        public uint Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public uint CredentialBlobSize;
        public IntPtr CredentialBlob;
        public uint Persist;
        public uint AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    public static class NativeCredential {
        [DllImport("advapi32.dll", EntryPoint = "CredWriteW", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CredWrite(ref NativeCredentialStruct credential, uint flags);

        [DllImport("advapi32.dll", EntryPoint = "CredReadW", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CredRead(string target, uint type, uint flags, out IntPtr credentialPtr);

        [DllImport("advapi32.dll", EntryPoint = "CredFree", SetLastError = true)]
        private static extern void CredFree(IntPtr buffer);

        public static void Write(string target, string userName, string secret) {
            byte[] bytes = Encoding.Unicode.GetBytes(secret);
            IntPtr blob = Marshal.AllocCoTaskMem(bytes.Length);
            try {
                Marshal.Copy(bytes, 0, blob, bytes.Length);
                var credential = new NativeCredentialStruct {
                    Type = 1,
                    TargetName = target,
                    CredentialBlobSize = (uint)bytes.Length,
                    CredentialBlob = blob,
                    Persist = 2,
                    UserName = userName
                };
                if (!CredWrite(ref credential, 0)) {
                    throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
                }
            }
            finally {
                for (int index = 0; index < bytes.Length; index++) {
                    Marshal.WriteByte(blob, index, 0);
                }
                Marshal.FreeCoTaskMem(blob);
                Array.Clear(bytes, 0, bytes.Length);
            }
        }

        public static string Read(string target) {
            IntPtr credentialPtr;
            if (!CredRead(target, 1, 0, out credentialPtr)) {
                return null;
            }
            try {
                var credential = Marshal.PtrToStructure<NativeCredentialStruct>(credentialPtr);
                if (credential.CredentialBlob == IntPtr.Zero || credential.CredentialBlobSize == 0) {
                    return string.Empty;
                }
                return Marshal.PtrToStringUni(
                    credential.CredentialBlob,
                    (int)credential.CredentialBlobSize / 2
                );
            }
            finally {
                CredFree(credentialPtr);
            }
        }
    }
}
'@
}

function Set-KisMcpWindowsCredential {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Target,
        [Parameter(Mandatory)] [securestring]$Secret
    )

    $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
    $Plain = $null
    try {
        $Plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
        [KisMcp.NativeCredential]::Write($Target, 'kis-mcp', $Plain)
    }
    finally {
        if ($Pointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
        }
        $Plain = $null
    }
}

function Get-KisMcpWindowsCredential {
    [CmdletBinding()]
    param([Parameter(Mandatory)] [string]$Target)

    $Value = [KisMcp.NativeCredential]::Read($Target)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "KIS_MCP_TUNNEL_CREDENTIAL_MISSING: store the credential once with scripts\\set-tunnel-credential.ps1. Target: $Target"
    }
    return $Value
}
