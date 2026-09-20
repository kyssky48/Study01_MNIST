<#
.SYNOPSIS
    손글씨 숫자 인식 앱의 바탕화면 바로가기를 만든다.

.DESCRIPTION
    - pythonw.exe로 실행해 검은 콘솔 창이 뜨지 않게 한다.
    - icon.ico를 바로가기 아이콘으로 지정한다.
    - 바로가기에 AppUserModelID를 심어, 작업 표시줄에 고정한 아이콘과
      실행 중인 창이 따로 놀지 않고 하나로 묶이게 한다.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
#>

$ErrorActionPreference = "Stop"

# ── 경로 준비 ─────────────────────────────────────────────
$프로젝트폴더 = Split-Path -Parent $MyInvocation.MyCommand.Definition
$앱스크립트   = Join-Path $프로젝트폴더 "draw_app.py"
$아이콘       = Join-Path $프로젝트폴더 "icon.ico"
$앱식별자     = "kyssk.MNIST.HandwritingRecognizer"   # draw_app.py의 앱_식별자와 같아야 한다

if (-not (Test-Path $앱스크립트)) { throw "draw_app.py를 찾을 수 없습니다: $앱스크립트" }
if (-not (Test-Path $아이콘))     { throw "icon.ico가 없습니다. 먼저 'python make_icon.py'를 실행하세요." }

# 콘솔 창 없이 파이썬을 실행하는 pythonw.exe를 찾는다
$pythonw = $null
$후보 = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if ($후보) {
    $pythonw = $후보.Source
} else {
    # pythonw.exe가 PATH에 없으면 python.exe와 같은 폴더에서 찾는다
    $파이썬 = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($파이썬) {
        $추정 = Join-Path (Split-Path -Parent $파이썬.Source) "pythonw.exe"
        if (Test-Path $추정) { $pythonw = $추정 }
    }
}
if (-not $pythonw) { throw "pythonw.exe를 찾지 못했습니다." }

$바탕화면 = [Environment]::GetFolderPath("Desktop")
$바로가기 = Join-Path $바탕화면 "손글씨 숫자 인식.lnk"

# ── 바로가기 만들기 ───────────────────────────────────────
$셸 = New-Object -ComObject WScript.Shell
$링크 = $셸.CreateShortcut($바로가기)
$링크.TargetPath       = $pythonw
$링크.Arguments        = '"' + $앱스크립트 + '"'
$링크.WorkingDirectory = $프로젝트폴더
$링크.IconLocation     = $아이콘 + ",0"
$링크.Description      = "손글씨로 쓴 숫자를 CNN으로 인식합니다"
$링크.WindowStyle      = 1        # 보통 크기 창
$링크.Save()

# ── 바로가기에 AppUserModelID 심기 ────────────────────────
# WScript.Shell로는 이 속성을 넣을 수 없어 윈도우 속성 저장소 API를 직접 쓴다.
$소스 = @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

public static class ShortcutAumid
{
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    public struct PropertyKey
    {
        public Guid fmtid;
        public uint pid;
        public PropertyKey(Guid f, uint p) { fmtid = f; pid = p; }
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PropVariant
    {
        public ushort vt;
        public ushort r1, r2, r3;
        public IntPtr p1, p2;
    }

    [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore
    {
        void GetCount(out uint c);
        void GetAt(uint i, out PropertyKey key);
        void GetValue(ref PropertyKey key, out PropVariant pv);
        void SetValue(ref PropertyKey key, ref PropVariant pv);
        void Commit();
    }

    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    public class ShellLink { }

    private const ushort VT_LPWSTR = 31;

    // 문자열을 담은 PROPVARIANT를 직접 만든다.
    // (propsys.dll의 InitPropVariantFromString은 내보내지 않는 버전이 있어 직접 구성한다)
    private static PropVariant MakeStringPropVariant(string value)
    {
        PropVariant pv = new PropVariant();
        pv.vt = VT_LPWSTR;
        pv.p1 = Marshal.StringToCoTaskMemUni(value);
        return pv;
    }

    [DllImport("ole32.dll")]
    private static extern int PropVariantClear(ref PropVariant pv);

    // System.AppUserModel.ID 속성 키
    private static PropertyKey AumidKey =
        new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);

    public static void Set(string linkPath, string aumid)
    {
        object link = new ShellLink();
        ((IPersistFile)link).Load(linkPath, 2 /* STGM_READWRITE */);
        IPropertyStore store = (IPropertyStore)link;
        PropVariant pv = MakeStringPropVariant(aumid);
        store.SetValue(ref AumidKey, ref pv);
        store.Commit();
        PropVariantClear(ref pv);
        ((IPersistFile)link).Save(linkPath, true);
        Marshal.ReleaseComObject(link);
    }

    public static string Get(string linkPath)
    {
        object link = new ShellLink();
        ((IPersistFile)link).Load(linkPath, 0 /* STGM_READ */);
        IPropertyStore store = (IPropertyStore)link;
        PropVariant pv;
        store.GetValue(ref AumidKey, out pv);
        string result = (pv.vt == 31 /* VT_LPWSTR */) ? Marshal.PtrToStringUni(pv.p1) : null;
        PropVariantClear(ref pv);
        Marshal.ReleaseComObject(link);
        return result;
    }
}
"@

if (-not ("ShortcutAumid" -as [type])) { Add-Type -TypeDefinition $소스 }
[ShortcutAumid]::Set($바로가기, $앱식별자)

# ── 결과 확인 ─────────────────────────────────────────────
$확인 = $셸.CreateShortcut($바로가기)
Write-Output "바로가기를 만들었습니다: $바로가기"
Write-Output "  실행 대상 : $($확인.TargetPath)"
Write-Output "  인자      : $($확인.Arguments)"
Write-Output "  작업 폴더 : $($확인.WorkingDirectory)"
Write-Output "  아이콘    : $($확인.IconLocation)"
Write-Output "  앱 식별자 : $([ShortcutAumid]::Get($바로가기))"
